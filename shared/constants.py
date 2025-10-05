# Shared constants for the IoT sensor network
"""
Common constants and enums used across client and host applications.
"""

from enum import Enum
from typing import Dict, Any

class SensorType(Enum):
    """Supported sensor types"""
    DHT11 = "DHT11"
    DHT22 = "DHT22"
    DS18B20 = "DS18B20"
    BMP280 = "BMP280"

class MessageType(Enum):
    """MQTT message types"""
    SENSOR_DATA = "sensor_data"
    SENSOR_STATUS = "sensor_status"
    HEARTBEAT = "heartbeat"
    CONFIG_UPDATE = "config_update"
    DEBUG = "debug"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# MQTT Topics
MQTT_TOPICS = {
    "sensor_data": "sensors/{client_id}/data",
    "sensor_status": "sensors/{client_id}/status",
    "heartbeat": "sensors/{client_id}/heartbeat",
    "config": "sensors/{client_id}/config",
    "debug": "sensors/{client_id}/debug",
    "discovery": "sensors/discovery"
}

# Default configurations
DEFAULT_CLIENT_CONFIG = {
    "client_id": "pi_client_001",
    "sensor_pin": 4,
    "sensor_type": "DHT11",
    "update_interval": 30,
    "mqtt": {
        "host": "192.168.1.112",
        "port": 8883,
        "username": "",
        "password": "",
        "use_tls": True,
        "ca_cert": "/etc/ssl/certs/ca-certificates.crt"
    },
    "modbus": {
        "enabled": False,
        "port": 5020,
        "slave_id": 1
    },
    "logging": {
        "level": "INFO",
        "max_size": "10MB",
        "backup_count": 5
    }
}

DEFAULT_HOST_CONFIG = {
    "mqtt": {
        "host": "0.0.0.0",
        "port": 8883,
        "websocket_port": 9001,
        "username": "admin",
        "password": "secure_password_123",
        "use_tls": True,
        "cert_file": "/etc/ssl/certs/mqtt-server.crt",
        "key_file": "/etc/ssl/private/mqtt-server.key"
    },
    "database": {
        "type": "sqlite",
        "path": "data/sensors.db",
        "retention_days": 365
    },
    "dashboard": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False,
        "secret_key": "your-secret-key-here"
    },
    "logging": {
        "level": "INFO",
        "max_size": "50MB",
        "backup_count": 10
    }
}

# Sensor data validation ranges
SENSOR_RANGES = {
    SensorType.DHT11: {
        "temperature": {"min": 0, "max": 50},
        "humidity": {"min": 20, "max": 90}
    },
    SensorType.DHT22: {
        "temperature": {"min": -40, "max": 80},
        "humidity": {"min": 0, "max": 100}
    },
    SensorType.DS18B20: {
        "temperature": {"min": -55, "max": 125}
    },
    SensorType.BMP280: {
        "temperature": {"min": -40, "max": 85},
        "pressure": {"min": 300, "max": 1100}
    }
}

# Error codes
ERROR_CODES = {
    "SENSOR_READ_FAILED": 1001,
    "MQTT_CONNECTION_FAILED": 2001,
    "MQTT_PUBLISH_FAILED": 2002,
    "CONFIG_LOAD_FAILED": 3001,
    "DATABASE_ERROR": 4001,
    "VALIDATION_ERROR": 5001
}

# Health check intervals (seconds)
HEALTH_CHECK_INTERVAL = 60
HEARTBEAT_INTERVAL = 30
SENSOR_TIMEOUT = 10

# Data retention
MAX_LOG_ENTRIES = 10000
DATABASE_CLEANUP_INTERVAL = 86400  # 24 hours