#!/bin/bash

# Quick Setup Script for IoT Sensor Client Pi
# Run this script on each Raspberry Pi sensor device

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
GITHUB_USER="cgninety"
REPO_NAME="clientpi"
INSTALL_DIR="/home/pi"
HOST_IP=""
CLIENT_ID=""
SENSOR_TYPE=""
SENSOR_PIN=""
MQTT_USER="sensor_client"
MQTT_PASS=""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  IoT Sensor Client Pi Quick Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as pi user
if [[ "$USER" != "pi" ]]; then
    echo -e "${RED}This script should be run as the 'pi' user${NC}"
    echo "Switch to pi user: su - pi"
    exit 1
fi

# Get configuration from user
echo -e "${YELLOW}Configuration Setup${NC}"
echo ""

# Host IP
read -p "Enter Host Pi IP address [192.168.1.112]: " HOST_IP
HOST_IP=${HOST_IP:-192.168.1.112}
while [[ ! $HOST_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; do
    echo -e "${RED}Invalid IP address format${NC}"
    read -p "Enter Host Pi IP address: " HOST_IP
done

# Client ID  
read -p "Enter unique Client ID [sensor_node1]: " CLIENT_ID
CLIENT_ID=${CLIENT_ID:-sensor_node1}
while [[ -z "$CLIENT_ID" ]]; do
    echo -e "${RED}Client ID cannot be empty${NC}"
    read -p "Enter unique Client ID: " CLIENT_ID
done

# Sensor type
echo ""
echo "Select sensor type:"
echo "1) DHT22 (recommended)"
echo "2) DHT11"
read -p "Choice (1-2) [1]: " sensor_choice
sensor_choice=${sensor_choice:-1}

case $sensor_choice in
    1) SENSOR_TYPE="DHT22" ;;
    2) SENSOR_TYPE="DHT11" ;;
    *) SENSOR_TYPE="DHT22" ;;
esac

# Sensor pin
read -p "Enter GPIO pin number for sensor [4]: " SENSOR_PIN
SENSOR_PIN=${SENSOR_PIN:-4}

# MQTT password
read -s -p "Enter MQTT password (from host setup): " MQTT_PASS
echo ""

# Validate inputs
echo ""
echo -e "${YELLOW}Configuration Summary:${NC}"
echo "  Host IP: $HOST_IP"
echo "  Client ID: $CLIENT_ID"
echo "  Sensor: $SENSOR_TYPE on GPIO pin $SENSOR_PIN"
echo "  MQTT User: $MQTT_USER"
echo ""
read -p "Continue with this configuration? (y/n) [y]: " confirm
confirm=${confirm:-y}

if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo -e "${RED}Setup cancelled${NC}"
    exit 0
fi

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update -qq
sudo apt upgrade -y -qq

# Install git if needed
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Installing git...${NC}"
    sudo apt install -y git
fi

# Navigate to install directory
cd "$INSTALL_DIR"

# Check if directory exists
if [ -d "clientpi" ]; then
    echo -e "${YELLOW}clientpi directory exists. Updating...${NC}"
    cd clientpi
    git pull origin main
else
    echo -e "${YELLOW}Cloning clientpi repository...${NC}"
    git clone "https://github.com/$GITHUB_USER/$REPO_NAME.git"
    cd clientpi
fi

# Make install script executable
chmod +x install_client.sh

# Run installation
echo -e "${YELLOW}Running installation script...${NC}"
sudo ./install_client.sh

# Configure client settings
echo -e "${YELLOW}Configuring client settings...${NC}"

# Update configuration file
sudo tee /etc/iot-sensor/client.yaml > /dev/null <<EOF
# IoT Sensor Client Configuration
mqtt:
  broker_host: "$HOST_IP"
  broker_port: 8883
  use_tls: true
  username: "$MQTT_USER"
  password: "$MQTT_PASS"
  keepalive: 60
  
client:
  id: "$CLIENT_ID"
  update_interval: 30
  
sensor:
  type: "$SENSOR_TYPE"
  pin: $SENSOR_PIN
  
logging:
  level: "INFO"
  file: "/var/log/iot-sensor/client.log"
EOF

# Test MQTT connection
echo -e "${YELLOW}Testing MQTT connection...${NC}"
if timeout 5 mosquitto_pub -h "$HOST_IP" -p 8883 -u "$MQTT_USER" -P "$MQTT_PASS" -t "test/$CLIENT_ID" -m "setup_test" --capath /etc/ssl/certs/ 2>/dev/null; then
    echo -e "${GREEN}✓ MQTT connection successful${NC}"
else
    echo -e "${RED}✗ MQTT connection failed${NC}"
    echo -e "${YELLOW}This may be normal if certificates aren't set up yet${NC}"
fi

# Start and enable service
echo -e "${YELLOW}Starting client service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable iot-sensor-client
sudo systemctl restart iot-sensor-client

# Wait for service to start
sleep 3

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
if systemctl is-active --quiet iot-sensor-client; then
    echo -e "${GREEN}✓ IoT Sensor Client: Running${NC}"
else
    echo -e "${RED}✗ IoT Sensor Client: Failed${NC}"
    echo -e "${YELLOW}Check logs: sudo journalctl -u iot-sensor-client -f${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Client Pi Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Client Information:${NC}"
echo "  Client ID: $CLIENT_ID"
echo "  Host IP: $HOST_IP"
echo "  Sensor: $SENSOR_TYPE on GPIO $SENSOR_PIN"
echo ""
echo -e "${BLUE}Configuration File:${NC}"
echo "  /etc/iot-sensor/client.yaml"
echo ""
echo -e "${BLUE}Service Commands:${NC}"
echo "  Status: sudo systemctl status iot-sensor-client"
echo "  Logs: sudo journalctl -u iot-sensor-client -f"
echo "  Restart: sudo systemctl restart iot-sensor-client"
echo ""
echo -e "${BLUE}Debug Console:${NC}"
echo "  cd /home/pi/clientpi"
echo "  python3 src/main.py --debug"
echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
echo ""
echo -e "${YELLOW}The sensor should now be sending data to the host at $HOST_IP${NC}"