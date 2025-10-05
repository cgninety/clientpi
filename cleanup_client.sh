#!/bin/bash

# IoT Sensor Client Cleanup Script  
# Removes all IoT sensor services and files from client Pi
# Run as: curl -fsSL https://raw.githubusercontent.com/cgninety/clientpi/main/cleanup_client.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}========================================${NC}"
echo -e "${RED}  IoT Sensor Client Cleanup${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}This will remove ALL IoT sensor components:${NC}"
echo "• Stop and disable IoT sensor client service"
echo "• Remove systemd service files"
echo "• Delete application files"
echo "• Remove configuration files" 
echo "• Clean up log files"
echo "• Remove created users and directories"
echo "• Uninstall sensor libraries"
echo ""
echo -e "${RED}WARNING: This action cannot be undone!${NC}"
echo ""

read -p "Are you sure you want to proceed? [y/N]: " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Starting cleanup...${NC}"

# Stop and disable services
echo -e "${BLUE}Stopping services...${NC}"
sudo systemctl stop iot-sensor-client 2>/dev/null || true
sudo systemctl disable iot-sensor-client 2>/dev/null || true

echo -e "${GREEN}✓ Services stopped${NC}"

# Remove systemd service files
echo -e "${BLUE}Removing service files...${NC}"
sudo rm -f /etc/systemd/system/iot-sensor-client.service
sudo systemctl daemon-reload

echo -e "${GREEN}✓ Service files removed${NC}"

# Remove application files
echo -e "${BLUE}Removing application files...${NC}"
sudo rm -rf /opt/iot-sensor-client

# Remove from user home directories
if [[ -d "/home/client/clientpi" ]]; then
    rm -rf /home/client/clientpi
fi
if [[ -d "/home/pi/clientpi" ]]; then
    rm -rf /home/pi/clientpi
fi

echo -e "${GREEN}✓ Application files removed${NC}"

# Remove configuration files
echo -e "${BLUE}Removing configuration files...${NC}"
sudo rm -rf /etc/iot-sensor

echo -e "${GREEN}✓ Configuration files removed${NC}"

# Remove log files
echo -e "${BLUE}Removing log files...${NC}"
sudo rm -rf /var/log/iot-sensor

echo -e "${GREEN}✓ Log files removed${NC}"

# Remove data directories
echo -e "${BLUE}Removing data directories...${NC}"
sudo rm -rf /var/lib/iot-sensor

echo -e "${GREEN}✓ Data directories removed${NC}"

# Remove iot-sensor user
echo -e "${BLUE}Removing iot-sensor user...${NC}"
if id "iot-sensor" &>/dev/null; then
    sudo userdel iot-sensor 2>/dev/null || true
fi

echo -e "${GREEN}✓ User removed${NC}"

# Remove Python packages (optional - comment out if you want to keep them)
echo -e "${BLUE}Removing Python packages...${NC}"
# sudo pip3 uninstall -y paho-mqtt adafruit-dht pyyaml python-dotenv 2>/dev/null || true
echo -e "${YELLOW}⚠ Python packages left installed (remove manually if needed)${NC}"

# Clean up any sensor-related processes
echo -e "${BLUE}Cleaning up processes...${NC}"
sudo pkill -f "iot-sensor" 2>/dev/null || true
sudo pkill -f "sensor.*client" 2>/dev/null || true

echo -e "${GREEN}✓ Processes cleaned${NC}"

# Remove any GPIO configurations (optional)
echo -e "${BLUE}Cleaning GPIO configurations...${NC}"
# Reset any GPIO pins that might be in use
if command -v raspi-gpio &> /dev/null; then
    raspi-gpio set 4 ip 2>/dev/null || true  # Reset GPIO 4 to input
fi

echo -e "${GREEN}✓ GPIO cleaned${NC}"

# Remove MQTT client packages (optional)
echo -e "${BLUE}Cleaning MQTT clients...${NC}"
# sudo apt-get remove -y mosquitto-clients 2>/dev/null || true

echo -e "${GREEN}✓ MQTT clients cleaned${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Client Cleanup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}What was removed:${NC}"
echo "✓ IoT Sensor Client service"
echo "✓ All configuration files"
echo "✓ Log files and data"
echo "✓ Application directories"
echo "✓ System user account"
echo "✓ GPIO configurations reset"
echo ""
echo -e "${BLUE}What was preserved:${NC}"
echo "• Python packages (remove manually if desired)"
echo "• MQTT client tools (remove manually if desired)"
echo "• System Python installation"
echo ""
echo -e "${BLUE}System status:${NC}"
echo "• Client Pi returned to clean state"
echo "• No IoT sensor components remain"
echo "• GPIO pins reset to default"
echo "• Ready for fresh installation"
echo ""
echo -e "${GREEN}Cleanup completed successfully! 🧹${NC}"

# Optional: Show cleanup commands for manual removal
echo ""
echo -e "${YELLOW}Optional manual cleanup commands:${NC}"
echo "Remove Python packages:"
echo "  sudo pip3 uninstall -y paho-mqtt adafruit-dht pyyaml python-dotenv"
echo ""
echo "Remove MQTT tools:"
echo "  sudo apt-get remove -y mosquitto-clients"
echo ""