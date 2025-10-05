# IoT Sensor Client (Raspberry Pi)

This repository contains the client-side code for the IoT sensor network, designed to run on Raspberry Pi devices.

## Features

- **Sensor Reading**: Support for DHT11/DHT22 temperature and humidity sensors
- **MQTT Communication**: Secure TLS connection to host server
- **Debug Console**: Interactive debugging and monitoring capabilities
- **Configuration Management**: Flexible YAML and environment variable configuration
- **Systemd Integration**: Automatic startup and service management
- **Error Handling**: Robust error recovery and logging

## Hardware Requirements

- Raspberry Pi Zero 2W or newer
- DHT11 or DHT22 temperature/humidity sensor
- MicroSD card (16GB+ recommended)
- Power supply

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/clientpi.git
   cd clientpi
   ```

2. **Run the installation script:**
   ```bash
   chmod +x install_client.sh
   sudo ./install_client.sh
   ```

3. **Configure the client:**
   ```bash
   sudo nano /etc/iot-sensor/client.yaml
   ```

## Configuration

Edit `/etc/iot-sensor/client.yaml` to configure:
- MQTT broker connection details
- Sensor pin assignments
- Update intervals
- SSL/TLS certificates

Example configuration:
```yaml
mqtt:
  broker_host: "192.168.1.112"
  broker_port: 8883
  use_tls: true
  
sensor:
  type: "DHT22"
  pin: 4
  
client:
  id: "sensor_001"
  update_interval: 30
```

## Usage

### Start the service:
```bash
sudo systemctl start iot-sensor-client
sudo systemctl enable iot-sensor-client
```

### Monitor logs:
```bash
sudo journalctl -u iot-sensor-client -f
```

### Debug console:
```bash
python3 src/main.py --debug
```

## Project Structure

```
clientpi/
├── src/                    # Source code
│   ├── main.py            # Main client application
│   ├── sensor_reader.py   # Sensor interface
│   ├── mqtt_client.py     # MQTT communication
│   └── debug_cli.py       # Debug console
├── shared/                # Shared utilities
│   ├── logger.py          # Logging system
│   ├── config_manager.py  # Configuration management
│   └── constants.py       # System constants
├── config/                # Configuration files
├── requirements.txt       # Python dependencies
├── install_client.sh      # Installation script
└── README.md             # This file
```

## Development

### Install dependencies:
```bash
pip3 install -r requirements.txt
```

### Run in development mode:
```bash
python3 src/main.py --config config/client.yaml --debug
```

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please use the GitHub issue tracker.