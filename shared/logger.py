"""
Enhanced logging utility for IoT sensor network.
Provides structured logging with rotation, formatting, and multiple handlers.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage'):
                log_entry[key] = value
        
        return json.dumps(log_entry)

class IoTLogger:
    """Enhanced logger for IoT applications"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with handlers and formatters"""
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set logging level
        level = self.config.get('level', 'INFO')
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Create formatters
        console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter(console_format))
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        log_dir = Path(self.config.get('log_dir', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"{self.name}.log"
        max_bytes = self._parse_size(self.config.get('max_size', '10MB'))
        backup_count = self.config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(logging.Formatter(file_format))
        self.logger.addHandler(file_handler)
        
        # JSON file handler for structured logs
        if self.config.get('json_logging', False):
            json_file = log_dir / f"{self.name}.json"
            json_handler = logging.handlers.RotatingFileHandler(
                json_file, maxBytes=max_bytes, backupCount=backup_count
            )
            json_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(json_handler)
        
        # Error file handler
        error_file = log_dir / f"{self.name}_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=max_bytes, backupCount=backup_count
        )
        error_handler.setFormatter(logging.Formatter(file_format))
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)
    
    def sensor_reading(self, sensor_id: str, temperature: float, 
                      humidity: Optional[float] = None, **kwargs):
        """Log sensor reading with structured data"""
        data = {
            'sensor_id': sensor_id,
            'temperature': temperature,
            'type': 'sensor_reading'
        }
        if humidity is not None:
            data['humidity'] = humidity
        data.update(kwargs)
        
        self.info(f"Sensor reading: T={temperature}°C" + 
                 (f", H={humidity}%" if humidity else ""), **data)
    
    def mqtt_event(self, event_type: str, topic: str, **kwargs):
        """Log MQTT events"""
        data = {
            'event_type': event_type,
            'topic': topic,
            'type': 'mqtt_event'
        }
        data.update(kwargs)
        
        self.info(f"MQTT {event_type}: {topic}", **data)
    
    def system_event(self, event_type: str, component: str, **kwargs):
        """Log system events"""
        data = {
            'event_type': event_type,
            'component': component,
            'type': 'system_event'
        }
        data.update(kwargs)
        
        self.info(f"System {event_type}: {component}", **data)

def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> IoTLogger:
    """Get or create a logger instance"""
    return IoTLogger(name, config)

def setup_root_logger(config: Optional[Dict[str, Any]] = None):
    """Setup root logger configuration"""
    config = config or {}
    
    # Set root logger level
    level = config.get('level', 'INFO')
    logging.getLogger().setLevel(getattr(logging, level.upper()))
    
    # Disable urllib3 warnings
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Configure third-party loggers
    logging.getLogger('paho.mqtt').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)