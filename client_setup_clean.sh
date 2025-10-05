#!/bin/bash

# Client Pi Setup - Working Version
# For client@node1 (192.168.1.145)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}IoT Sensor Client Setup${NC}"
echo ""

# Check user
if [[ "$USER" != "pi" && "$USER" != "client" ]]; then
    echo -e "${RED}Run as 'pi' or 'client' user${NC}"
    exit 1
fi

echo -e "${GREEN}✓ User: $USER${NC}"

# Set directories
if [[ "$USER" == "client" ]]; then
    INSTALL_DIR="/home/client"
else
    INSTALL_DIR="/home/pi"
fi

echo -e "${BLUE}Installing to: $INSTALL_DIR${NC}"

# Get config
read -p "Host IP [192.168.1.112]: " HOST_IP
HOST_IP=${HOST_IP:-"192.168.1.112"}

read -p "Client ID [sensor_node1]: " CLIENT_ID  
CLIENT_ID=${CLIENT_ID:-"sensor_node1"}

echo "Sensor type:"
echo "1) DHT22"
echo "2) DHT11"
read -p "Choice [1]: " choice

if [[ "$choice" == "2" ]]; then
    SENSOR_TYPE="DHT11"
else
    SENSOR_TYPE="DHT22"
fi

read -p "GPIO pin [4]: " SENSOR_PIN
SENSOR_PIN=${SENSOR_PIN:-"4"}

read -s -p "MQTT password: " MQTT_PASS
echo ""

echo ""
echo "Config Summary:"
echo "  Host: $HOST_IP"
echo "  Client ID: $CLIENT_ID"  
echo "  Sensor: $SENSOR_TYPE on GPIO $SENSOR_PIN"
echo ""

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

# Clone repo
cd "$INSTALL_DIR"
if [[ -d "clientpi" ]]; then
    echo -e "${YELLOW}Updating repo...${NC}"
    cd clientpi
    git pull origin main
else
    echo -e "${YELLOW}Cloning repo...${NC}"
    git clone "https://github.com/cgninety/clientpi.git"
    cd clientpi
fi

# Install
echo -e "${YELLOW}Installing...${NC}"
chmod +x install_client.sh
sudo ./install_client.sh

# Configure
echo -e "${YELLOW}Configuring...${NC}"
sudo tee /etc/iot-sensor/client.yaml > /dev/null << EOF
mqtt:
  broker_host: "$HOST_IP"
  broker_port: 8883
  use_tls: true
  username: "sensor_client"
  password: "$MQTT_PASS"
  
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

# Test MQTT
echo -e "${YELLOW}Testing MQTT...${NC}"
if timeout 5 mosquitto_pub -h "$HOST_IP" -p 8883 -u "sensor_client" -P "$MQTT_PASS" -t "test/$CLIENT_ID" -m "test" 2>/dev/null; then
    echo -e "${GREEN}✓ MQTT OK${NC}"
else
    echo -e "${YELLOW}MQTT test inconclusive${NC}"
fi

# Start service
echo -e "${YELLOW}Starting service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable iot-sensor-client
sudo systemctl restart iot-sensor-client

sleep 2

if systemctl is-active --quiet iot-sensor-client; then
    echo -e "${GREEN}✓ Service running${NC}"
else
    echo -e "${RED}✗ Service failed${NC}"
fi

echo ""
echo -e "${GREEN}Setup Complete!${NC}"
echo ""
echo "Client: $CLIENT_ID"
echo "Host: $HOST_IP" 
echo "Sensor: $SENSOR_TYPE on GPIO $SENSOR_PIN"
echo ""
echo "Commands:"
echo "  Status: sudo systemctl status iot-sensor-client"
echo "  Logs: sudo journalctl -u iot-sensor-client -f"
echo ""
echo -e "${GREEN}Done! 🎉${NC}"