#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# IoT Sensor Network - Client Installation Script
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # Exit on any error

echo "🚀 IoT Sensor Network - Client Installation"
echo "==========================================="

# ─── Configuration ──────────────────────────────────────────────────────────────
PROJECT_NAME="iot-sensor-network"
CLIENT_DIR="/opt/${PROJECT_NAME}-client"
SERVICE_NAME="iot-sensor-client"
USER_NAME="iot"
GROUP_NAME="iot"
PYTHON_VERSION="3.11"

# ─── Check if running as root ───────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# ─── Detect system information ──────────────────────────────────────────────────
echo "📋 System Information:"
echo "   OS: $(lsb_release -d | cut -f2)"
echo "   Architecture: $(uname -m)"
echo "   Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo ""

# ─── Install system dependencies ────────────────────────────────────────────────
echo "📦 Installing system dependencies..."
apt update
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    libgpiod2 \
    libgpiod-dev \
    i2c-tools \
    libi2c-dev \
    mosquitto-clients \
    openssl \
    ca-certificates

# ─── Create system user ─────────────────────────────────────────────────────────
echo "👤 Creating system user: $USER_NAME"
if ! id "$USER_NAME" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash \
            --groups gpio,i2c,spi \
            --comment "IoT Sensor Client User" \
            "$USER_NAME"
    echo "   ✓ User $USER_NAME created"
else
    echo "   ✓ User $USER_NAME already exists"
fi

# Add user to additional groups for hardware access
usermod -a -G gpio,i2c,spi,dialout "$USER_NAME" 2>/dev/null || true

# ─── Create project directories ─────────────────────────────────────────────────
echo "📁 Creating project directories..."
mkdir -p "$CLIENT_DIR"/{src,config,logs,data}
chown -R "$USER_NAME:$GROUP_NAME" "$CLIENT_DIR"
chmod 755 "$CLIENT_DIR"

# ─── Copy project files ──────────────────────────────────────────────────────────
echo "📋 Copying project files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy client source files
if [[ -d "$PROJECT_ROOT/client/src" ]]; then
    cp -r "$PROJECT_ROOT/client/src"/* "$CLIENT_DIR/src/"
    echo "   ✓ Source files copied"
else
    echo "   ⚠️  Source directory not found: $PROJECT_ROOT/client/src"
fi

# Copy shared modules
if [[ -d "$PROJECT_ROOT/shared" ]]; then
    mkdir -p "$CLIENT_DIR/shared"
    cp -r "$PROJECT_ROOT/shared"/* "$CLIENT_DIR/shared/"
    echo "   ✓ Shared modules copied"
else
    echo "   ⚠️  Shared directory not found: $PROJECT_ROOT/shared"
fi

# Copy configuration files
if [[ -f "$PROJECT_ROOT/client/config/client_config.yaml" ]]; then
    cp "$PROJECT_ROOT/client/config/client_config.yaml" "$CLIENT_DIR/config/"
    echo "   ✓ Configuration file copied"
fi

if [[ -f "$PROJECT_ROOT/client/config/.env.example" ]]; then
    cp "$PROJECT_ROOT/client/config/.env.example" "$CLIENT_DIR/config/"
    echo "   ✓ Environment template copied"
fi

# Copy requirements
if [[ -f "$PROJECT_ROOT/client/requirements.txt" ]]; then
    cp "$PROJECT_ROOT/client/requirements.txt" "$CLIENT_DIR/"
    echo "   ✓ Requirements file copied"
fi

# Set ownership
chown -R "$USER_NAME:$GROUP_NAME" "$CLIENT_DIR"

# ─── Create Python virtual environment ──────────────────────────────────────────
echo "🐍 Setting up Python virtual environment..."
sudo -u "$USER_NAME" python3 -m venv "$CLIENT_DIR/venv"
echo "   ✓ Virtual environment created"

# Activate virtual environment and install packages
echo "📦 Installing Python packages..."
sudo -u "$USER_NAME" bash -c "
    source '$CLIENT_DIR/venv/bin/activate'
    pip install --upgrade pip setuptools wheel
    
    # Install requirements if file exists
    if [[ -f '$CLIENT_DIR/requirements.txt' ]]; then
        pip install -r '$CLIENT_DIR/requirements.txt'
    else
        # Install essential packages manually
        pip install paho-mqtt PyYAML python-dotenv requests psutil
        
        # Try to install Raspberry Pi specific packages
        pip install adafruit-circuitpython-dht || echo 'Warning: Could not install DHT library'
        pip install w1thermsensor || echo 'Warning: Could not install DS18B20 library'
        pip install pymodbus || echo 'Warning: Could not install Modbus library'
    fi
"
echo "   ✓ Python packages installed"

# ─── Configure hardware interfaces ──────────────────────────────────────────────
echo "⚙️  Configuring hardware interfaces..."

# Enable I2C, SPI, GPIO interfaces
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0     # Enable I2C
    raspi-config nonint do_spi 0     # Enable SPI
    raspi-config nonint do_ssh 0     # Ensure SSH is enabled
    echo "   ✓ Hardware interfaces enabled"
else
    echo "   ⚠️  raspi-config not found, skipping hardware configuration"
fi

# ─── Generate client configuration ──────────────────────────────────────────────
echo "🔧 Generating client configuration..."

# Detect client role based on IP address
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [[ "$LOCAL_IP" == "192.168.1.112" ]]; then
    CLIENT_ID="host_sensors"
    MQTT_HOST="127.0.0.1"  # Local MQTT broker
elif [[ "$LOCAL_IP" == "192.168.1.145" ]]; then
    CLIENT_ID="client_sensors"
    MQTT_HOST="192.168.1.112"  # Host Pi MQTT broker
else
    CLIENT_ID="pi_client_$(hostname)"
    MQTT_HOST="192.168.1.112"  # Default to host Pi
fi

# Create environment file
cat > "$CLIENT_DIR/config/.env" << EOF
# IoT Sensor Client Environment Configuration
# Generated on $(date)

# Client identification
CLIENT_ID=$CLIENT_ID

# MQTT broker settings
MQTT_HOST=$MQTT_HOST
MQTT_PORT=8883
MQTT_USE_TLS=true

# Sensor settings
SENSOR_PIN=4
SENSOR_TYPE=DHT11
UPDATE_INTERVAL=30

# Logging
LOG_LEVEL=INFO
EOF

chown "$USER_NAME:$GROUP_NAME" "$CLIENT_DIR/config/.env"
echo "   ✓ Environment configuration created"

# ─── Create systemd service ─────────────────────────────────────────────────────
echo "🔧 Creating systemd service..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=IoT Sensor Network Client
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$USER_NAME
Group=$GROUP_NAME
WorkingDirectory=$CLIENT_DIR
Environment=PYTHONPATH=$CLIENT_DIR
ExecStart=$CLIENT_DIR/venv/bin/python src/main.py --config config/client_config.yaml
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$CLIENT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "   ✓ Systemd service created and enabled"

# ─── Create log rotation configuration ──────────────────────────────────────────
echo "📝 Setting up log rotation..."

cat > "/etc/logrotate.d/${SERVICE_NAME}" << EOF
$CLIENT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 $USER_NAME $GROUP_NAME
    postrotate
        systemctl reload $SERVICE_NAME >/dev/null 2>&1 || true
    endscript
}
EOF

echo "   ✓ Log rotation configured"

# ─── Create management scripts ───────────────────────────────────────────────────
echo "🛠️  Creating management scripts..."

# Create start script
cat > "$CLIENT_DIR/start.sh" << EOF
#!/bin/bash
echo "Starting IoT Sensor Client..."
sudo systemctl start $SERVICE_NAME
sudo systemctl status --no-pager $SERVICE_NAME
EOF

# Create stop script
cat > "$CLIENT_DIR/stop.sh" << EOF
#!/bin/bash
echo "Stopping IoT Sensor Client..."
sudo systemctl stop $SERVICE_NAME
EOF

# Create status script
cat > "$CLIENT_DIR/status.sh" << EOF
#!/bin/bash
echo "IoT Sensor Client Status:"
sudo systemctl status --no-pager $SERVICE_NAME
echo ""
echo "Recent logs:"
sudo journalctl -u $SERVICE_NAME --no-pager -n 20
EOF

# Create debug script
cat > "$CLIENT_DIR/debug.sh" << EOF
#!/bin/bash
echo "Starting IoT Sensor Client in debug mode..."
cd $CLIENT_DIR
source venv/bin/activate
python src/main.py --config config/client_config.yaml --verbose
EOF

# Make scripts executable
chmod +x "$CLIENT_DIR"/*.sh
chown "$USER_NAME:$GROUP_NAME" "$CLIENT_DIR"/*.sh

echo "   ✓ Management scripts created"

# ─── Configure firewall (if ufw is installed) ───────────────────────────────────
if command -v ufw >/dev/null 2>&1; then
    echo "🔥 Configuring firewall..."
    ufw allow 5020/tcp comment "Modbus TCP"
    ufw allow 8081/tcp comment "Debug Console"
    echo "   ✓ Firewall rules added"
fi

# ─── Installation summary ───────────────────────────────────────────────────────
echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📋 Installation Summary:"
echo "   • Project directory: $CLIENT_DIR"
echo "   • System user: $USER_NAME"
echo "   • Service name: $SERVICE_NAME"
echo "   • Client ID: $CLIENT_ID"
echo "   • MQTT broker: $MQTT_HOST"
echo ""
echo "📚 Quick Start:"
echo "   • Start service:    sudo systemctl start $SERVICE_NAME"
echo "   • Check status:     sudo systemctl status $SERVICE_NAME"
echo "   • View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "   • Stop service:     sudo systemctl stop $SERVICE_NAME"
echo ""
echo "🛠️  Management Scripts:"
echo "   • $CLIENT_DIR/start.sh   - Start the service"
echo "   • $CLIENT_DIR/stop.sh    - Stop the service"
echo "   • $CLIENT_DIR/status.sh  - Check status and logs"
echo "   • $CLIENT_DIR/debug.sh   - Run in debug mode"
echo ""
echo "⚙️  Configuration:"
echo "   • Main config: $CLIENT_DIR/config/client_config.yaml"
echo "   • Environment: $CLIENT_DIR/config/.env"
echo "   • Logs:        $CLIENT_DIR/logs/"
echo ""
echo "🔍 Next Steps:"
echo "   1. Review configuration files"
echo "   2. Start the service: sudo systemctl start $SERVICE_NAME"
echo "   3. Check logs for any issues"
echo "   4. Configure your MQTT broker on the host Pi"
echo ""

# ─── Final system check ──────────────────────────────────────────────────────────
echo "🔍 System Check:"
echo "   • Python version: $(sudo -u $USER_NAME $CLIENT_DIR/venv/bin/python --version)"
echo "   • Service status: $(systemctl is-enabled $SERVICE_NAME)"
echo "   • GPIO access:    $(groups $USER_NAME | grep -q gpio && echo 'OK' || echo 'MISSING')"
echo "   • I2C access:     $(groups $USER_NAME | grep -q i2c && echo 'OK' || echo 'MISSING')"
echo ""
echo "🎉 Client installation complete!"

# Ask if user wants to start the service now
read -p "Would you like to start the service now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting IoT Sensor Client..."
    systemctl start "$SERVICE_NAME"
    sleep 2
    systemctl status "$SERVICE_NAME" --no-pager
    echo ""
    echo "✅ Service started! Check logs with: sudo journalctl -u $SERVICE_NAME -f"
fi