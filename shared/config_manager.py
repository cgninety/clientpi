"""
Configuration manager for IoT sensor network.
Handles loading, validation, and management of configuration files.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
import logging

try:
    from dotenv import load_dotenv
    has_dotenv = True
except ImportError:
    has_dotenv = False
    def load_dotenv(path: Optional[str] = None) -> bool:
        return False

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: str, env_path: Optional[str] = None):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path) if env_path else None
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file and environment variables"""
        try:
            # Load environment variables
            if has_dotenv and self.env_path and self.env_path.exists():
                load_dotenv(str(self.env_path))
            
            # Load YAML configuration
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                self._config = {}
            
            # Override with environment variables
            self._apply_env_overrides()
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        env_mappings: Dict[str, Tuple[str, ...]] = {
            'MQTT_HOST': ('mqtt', 'host'),
            'MQTT_PORT': ('mqtt', 'port'),
            'MQTT_USERNAME': ('mqtt', 'username'),
            'MQTT_PASSWORD': ('mqtt', 'password'),
            'MQTT_USE_TLS': ('mqtt', 'use_tls'),
            'SENSOR_PIN': ('sensor_pin',),
            'SENSOR_TYPE': ('sensor_type',),
            'UPDATE_INTERVAL': ('update_interval',),
            'CLIENT_ID': ('client_id',),
            'DATABASE_PATH': ('database', 'path'),
            'DASHBOARD_PORT': ('dashboard', 'port'),
            'LOG_LEVEL': ('logging', 'level')
        }
        
        for env_key, config_path in env_mappings.items():
            value = os.getenv(env_key)
            if value is not None:
                self._set_nested_value(config_path, self._convert_env_value(value))
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert string environment values to appropriate types"""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _set_nested_value(self, path: Tuple[str, ...], value: Any) -> None:
        """Set a nested configuration value"""
        current: Dict[str, Any] = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation"""
        keys = key.split('.')
        current: Any = self._config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot notation"""
        keys = key.split('.')
        current: Dict[str, Any] = self._config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section"""
        return self.get(section, {})
    
    def validate_config(self, schema: Dict[str, Any]) -> bool:
        """Validate configuration against a schema"""
        try:
            return self._validate_recursive(self._config, schema)
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _validate_recursive(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Recursively validate configuration"""
        for key, expected_type in schema.items():
            if key not in config:
                logger.error(f"Missing required configuration key: {key}")
                return False
            
            if isinstance(expected_type, dict):
                if not isinstance(config[key], dict):
                    logger.error(f"Configuration key '{key}' should be a dict")
                    return False
                if not self._validate_recursive(config[key], expected_type):
                    return False
            elif not isinstance(config[key], expected_type):
                logger.error(f"Configuration key '{key}' should be {expected_type}")
                return False
        
        return True
    
    def save_config(self, path: Optional[str] = None) -> None:
        """Save current configuration to file"""
        save_path = Path(path) if path else self.config_path
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_config()
        logger.info("Configuration reloaded")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self._config.copy()
    
    def to_json(self) -> str:
        """Return configuration as JSON string"""
        return json.dumps(self._config, indent=2)

class ClientConfigManager(ConfigManager):
    """Configuration manager for client applications"""
    
    def __init__(self, config_path: str = "config/client_config.yaml", 
                 env_path: str = "config/.env"):
        super().__init__(config_path, env_path)
        self._apply_defaults()
    
    def _apply_defaults(self) -> None:
        """Apply default values for client configuration"""
        from shared.constants import DEFAULT_CLIENT_CONFIG
        
        for key, value in DEFAULT_CLIENT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value

class HostConfigManager(ConfigManager):
    """Configuration manager for host applications"""
    
    def __init__(self, config_path: str = "config/host_config.yaml",
                 env_path: str = "config/.env"):
        super().__init__(config_path, env_path)
        self._apply_defaults()
    
    def _apply_defaults(self) -> None:
        """Apply default values for host configuration"""
        from shared.constants import DEFAULT_HOST_CONFIG
        
        for key, value in DEFAULT_HOST_CONFIG.items():
            if key not in self._config:
                self._config[key] = value