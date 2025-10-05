#!/bin/bash

# Client Pi Setup Script - Oct 4 2025
# Supports client@node1 username
# Run this script on client@192.168.1.145

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GITHUB_USER="cgninety"
REPO_NAME="clientpi"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  IoT Sensor Client Setup (Oct 4 2025)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check user - support both pi and client users
echo -e "${BLUE}Current user: $USER${NC}"
if [[ "$USER" != "pi" && "$USER" != "client" ]]; then
    echo -e "${RED}Error: Run as 'pi' or 'client' user${NC}"
    echo "Current user: $USER"
    exit 1
fi

echo -e "${GREEN}✓ User check passed${NC}"

# Set home directory
if [[ "$USER" == "client" ]]; then
    INSTALL_DIR="/home/client"
else
    INSTALL_DIR="/home/pi"
fi

echo -e "${BLUE}Installing to: $INSTALL_DIR${NC}"

# Get configuration
read -p "Host Pi IP [192.168.1.112]: " HOST_IP
HOST_IP=${HOST_IP:-192.168.1.112}

read -p "Client ID [sensor_node1]: " CLIENT_ID
CLIENT_ID=${CLIENT_ID:-sensor_node1}

echo "Sensor type:"
echo "1) DHT22 (recommended)"
echo "2) DHT11"
read -p "Choice [1]: " sensor_choice
case ${sensor_choice:-1} in
    2) SENSOR_TYPE="DHT11" ;;
    *) SENSOR_TYPE="DHT22" ;;
esac

read -p "GPIO pin [4]: " SENSOR_PIN
SENSOR_PIN=${SENSOR_PIN:-4}

read -s -p "MQTT password (from host setup): " MQTT_PASS
echo ""

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Host: $HOST_IP"
echo "  Client ID: $CLIENT_ID"
echo "  Sensor: $SENSOR_TYPE on GPIO $SENSOR_PIN"

read -p "Continue? [y]: " confirm
if [[ "${confirm:-y}" != "y" ]]; then
    exit 0
fi

# Update system
echo -e "${YELLOW}Updating system...${NC}"
sudo apt update -qq
sudo apt upgrade -y -qq

# Install git
if ! command -v git &> /dev/null; then
    sudo apt install -y git
fi

# Clone/update repository
cd "$INSTALL_DIR"
if [ -d "clientpi" ]; then
    echo -e "${YELLOW}Updating repository...${NC}"
    cd clientpi
    git pull origin main
else
    echo -e "${YELLOW}Cloning repository...${NC}"
    git clone "https://github.com/$GITHUB_USER/$REPO_NAME.git"
    cd clientpi
fi

# Run installation
echo -e "${YELLOW}Running installation...${NC}"
chmod +x install_client.sh
sudo ./install_client.sh

# Configure client
echo -e "${YELLOW}Configuring client...${NC}"
sudo tee /etc/iot-sensor/client.yaml > /dev/null <<EOF
mqtt:
  broker_host: "$HOST_IP"
  broker_port: 8883
  use_tls: true
  username: "sensor_client"
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
echo -e "${YELLOW}Testing MQTT...${NC}"
if timeout 5 mosquitto_pub -h "$HOST_IP" -p 8883 -u "sensor_client" -P "$MQTT_PASS" -t "test/$CLIENT_ID" -m "setup_test" --capath /etc/ssl/certs/ 2>/dev/null; then
    echo -e "${GREEN}✓ MQTT connection OK${NC}"
else
    echo -e "${YELLOW}⚠ MQTT test failed (may be normal)${NC}"
fi

# Start service
echo -e "${YELLOW}Starting client service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable iot-sensor-client
sudo systemctl restart iot-sensor-client

sleep 3

# Check status
if systemctl is-active --quiet iot-sensor-client; then
    echo -e "${GREEN}✓ Client Service: Running${NC}"
else
    echo -e "${RED}✗ Client Service: Failed${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Client Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Client Details:${NC}"
echo "  ID: $CLIENT_ID"
echo "  Host: $HOST_IP"
echo "  Sensor: $SENSOR_TYPE on GPIO $SENSOR_PIN"
echo ""
echo -e "${BLUE}Commands:${NC}"
echo "  Status: sudo systemctl status iot-sensor-client"
echo "  Logs: sudo journalctl -u iot-sensor-client -f"
echo "  Debug: cd $INSTALL_DIR/clientpi && python3 src/main.py --debug"
echo ""
echo -e "${GREEN}Done! 🎉${NC}"