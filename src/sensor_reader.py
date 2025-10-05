"""
Sensor reader for DHT11/DHT22 and other sensors.
Provides unified interface for reading sensor data with error handling and validation.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import random

try:
    import adafruit_dht
    import board
    HAS_DHT = True
except ImportError:
    HAS_DHT = False
    print("Warning: DHT sensor library not available. Using mock data.")

try:
    import w1thermsensor
    HAS_DS18B20 = True
except ImportError:
    HAS_DS18B20 = False

from shared.constants import SensorType, SENSOR_RANGES
from shared.logger import get_logger

@dataclass
class SensorReading:
    """Represents a sensor reading"""
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    timestamp: datetime = None
    sensor_id: str = ""
    sensor_type: str = ""
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'error': self.error
        }
    
    def is_valid(self) -> bool:
        """Check if reading has valid data"""
        return self.error is None and (
            self.temperature is not None or 
            self.humidity is not None or 
            self.pressure is not None
        )

class SensorReader:
    """Base class for sensor readers"""
    
    def __init__(self, sensor_id: str, sensor_type: str, config: Dict[str, Any]):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.config = config
        self.logger = get_logger(f"sensor_{sensor_id}")
        self._last_reading = None
        self._error_count = 0
        self._max_errors = config.get('max_errors', 5)
        self._lock = threading.Lock()
    
    def read(self) -> SensorReading:
        """Read sensor data"""
        raise NotImplementedError
    
    def validate_reading(self, reading: SensorReading) -> bool:
        """Validate sensor reading against expected ranges"""
        if not reading.is_valid():
            return False
        
        try:
            sensor_type = SensorType(self.sensor_type)
            ranges = SENSOR_RANGES.get(sensor_type, {})
            
            if reading.temperature is not None:
                temp_range = ranges.get('temperature', {})
                if 'min' in temp_range and reading.temperature < temp_range['min']:
                    return False
                if 'max' in temp_range and reading.temperature > temp_range['max']:
                    return False
            
            if reading.humidity is not None:
                hum_range = ranges.get('humidity', {})
                if 'min' in hum_range and reading.humidity < hum_range['min']:
                    return False
                if 'max' in hum_range and reading.humidity > hum_range['max']:
                    return False
            
            if reading.pressure is not None:
                press_range = ranges.get('pressure', {})
                if 'min' in press_range and reading.pressure < press_range['min']:
                    return False
                if 'max' in press_range and reading.pressure > press_range['max']:
                    return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def get_last_reading(self) -> Optional[SensorReading]:
        """Get last successful reading"""
        with self._lock:
            return self._last_reading
    
    def is_healthy(self) -> bool:
        """Check if sensor is healthy"""
        return self._error_count < self._max_errors

class DHT11Reader(SensorReader):
    """DHT11/DHT22 sensor reader"""
    
    def __init__(self, sensor_id: str, pin: int, sensor_type: str = "DHT11", config: Dict[str, Any] = None):
        super().__init__(sensor_id, sensor_type, config or {})
        self.pin = pin
        
        if HAS_DHT:
            try:
                pin_obj = getattr(board, f'D{pin}')
                if sensor_type == "DHT22":
                    self.sensor = adafruit_dht.DHT22(pin_obj)
                else:
                    self.sensor = adafruit_dht.DHT11(pin_obj)
                self.logger.info(f"Initialized {sensor_type} sensor on pin {pin}")
            except Exception as e:
                self.logger.error(f"Failed to initialize DHT sensor: {e}")
                self.sensor = None
        else:
            self.sensor = None
            self.logger.warning("DHT library not available, using mock data")
    
    def read(self) -> SensorReading:
        """Read DHT sensor data"""
        reading = SensorReading(
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type
        )
        
        try:
            if self.sensor and HAS_DHT:
                # Real sensor reading
                temperature = self.sensor.temperature
                humidity = self.sensor.humidity
                
                if temperature is not None and humidity is not None:
                    reading.temperature = round(temperature, 1)
                    reading.humidity = round(humidity, 1)
                    self._error_count = 0
                    
                    with self._lock:
                        self._last_reading = reading
                    
                    self.logger.sensor_reading(
                        self.sensor_id, reading.temperature, reading.humidity
                    )
                else:
                    reading.error = "Sensor returned None values"
                    self._error_count += 1
            else:
                # Mock data for testing
                reading.temperature = round(20 + random.uniform(-5, 10), 1)
                reading.humidity = round(50 + random.uniform(-20, 30), 1)
                self.logger.debug(f"Mock sensor reading: T={reading.temperature}°C, H={reading.humidity}%")
        
        except Exception as e:
            reading.error = str(e)
            self._error_count += 1
            self.logger.error(f"Failed to read DHT sensor: {e}")
        
        return reading

class DS18B20Reader(SensorReader):
    """DS18B20 temperature sensor reader"""
    
    def __init__(self, sensor_id: str, config: Dict[str, Any] = None):
        super().__init__(sensor_id, "DS18B20", config or {})
        
        if HAS_DS18B20:
            try:
                self.sensor = w1thermsensor.W1ThermSensor()
                self.logger.info("Initialized DS18B20 sensor")
            except Exception as e:
                self.logger.error(f"Failed to initialize DS18B20 sensor: {e}")
                self.sensor = None
        else:
            self.sensor = None
            self.logger.warning("DS18B20 library not available, using mock data")
    
    def read(self) -> SensorReading:
        """Read DS18B20 sensor data"""
        reading = SensorReading(
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type
        )
        
        try:
            if self.sensor and HAS_DS18B20:
                temperature = self.sensor.get_temperature()
                reading.temperature = round(temperature, 2)
                self._error_count = 0
                
                with self._lock:
                    self._last_reading = reading
                
                self.logger.sensor_reading(self.sensor_id, reading.temperature)
            else:
                # Mock data
                reading.temperature = round(20 + random.uniform(-10, 15), 2)
                self.logger.debug(f"Mock DS18B20 reading: T={reading.temperature}°C")
        
        except Exception as e:
            reading.error = str(e)
            self._error_count += 1
            self.logger.error(f"Failed to read DS18B20 sensor: {e}")
        
        return reading

class MockSensorReader(SensorReader):
    """Mock sensor for testing"""
    
    def __init__(self, sensor_id: str, sensor_type: str = "DHT11", config: Dict[str, Any] = None):
        super().__init__(sensor_id, sensor_type, config or {})
        self.base_temp = 22.0
        self.base_humidity = 60.0
        self.drift = 0.0
    
    def read(self) -> SensorReading:
        """Generate mock sensor data"""
        # Add some random variation and drift
        self.drift += random.uniform(-0.1, 0.1)
        self.drift = max(-2.0, min(2.0, self.drift))  # Limit drift
        
        reading = SensorReading(
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type,
            temperature=round(self.base_temp + self.drift + random.uniform(-1, 1), 1),
            humidity=round(self.base_humidity + random.uniform(-5, 5), 1)
        )
        
        # Occasionally simulate errors
        if random.random() < 0.05:  # 5% error rate
            reading.error = "Simulated sensor error"
            self._error_count += 1
        else:
            self._error_count = max(0, self._error_count - 1)
            with self._lock:
                self._last_reading = reading
        
        return reading

class SensorManager:
    """Manages multiple sensors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sensors = {}
        self.logger = get_logger("sensor_manager")
        self._setup_sensors()
    
    def _setup_sensors(self):
        """Setup sensors based on configuration"""
        sensor_configs = self.config.get('sensors', [])
        
        for sensor_config in sensor_configs:
            sensor_id = sensor_config.get('id')
            sensor_type = sensor_config.get('type', 'DHT11')
            
            try:
                if sensor_type in ['DHT11', 'DHT22']:
                    pin = sensor_config.get('pin', 4)
                    sensor = DHT11Reader(sensor_id, pin, sensor_type, sensor_config)
                elif sensor_type == 'DS18B20':
                    sensor = DS18B20Reader(sensor_id, sensor_config)
                else:
                    sensor = MockSensorReader(sensor_id, sensor_type, sensor_config)
                
                self.sensors[sensor_id] = sensor
                self.logger.info(f"Added sensor: {sensor_id} ({sensor_type})")
                
            except Exception as e:
                self.logger.error(f"Failed to setup sensor {sensor_id}: {e}")
    
    def read_all(self) -> Dict[str, SensorReading]:
        """Read all sensors"""
        readings = {}
        
        for sensor_id, sensor in self.sensors.items():
            try:
                reading = sensor.read()
                readings[sensor_id] = reading
                
                if not reading.is_valid():
                    self.logger.warning(f"Invalid reading from sensor {sensor_id}: {reading.error}")
            
            except Exception as e:
                self.logger.error(f"Failed to read sensor {sensor_id}: {e}")
                readings[sensor_id] = SensorReading(
                    sensor_id=sensor_id,
                    error=str(e)
                )
        
        return readings
    
    def get_sensor(self, sensor_id: str) -> Optional[SensorReader]:
        """Get sensor by ID"""
        return self.sensors.get(sensor_id)
    
    def get_sensor_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sensors"""
        status = {}
        
        for sensor_id, sensor in self.sensors.items():
            last_reading = sensor.get_last_reading()
            status[sensor_id] = {
                'sensor_type': sensor.sensor_type,
                'healthy': sensor.is_healthy(),
                'error_count': sensor._error_count,
                'last_reading_time': last_reading.timestamp.isoformat() if last_reading else None,
                'last_temperature': last_reading.temperature if last_reading else None,
                'last_humidity': last_reading.humidity if last_reading else None
            }
        
        return status

def create_sensor_reader(sensor_id: str, sensor_type: str, config: Dict[str, Any]) -> SensorReader:
    """Factory function to create sensor readers"""
    if sensor_type in ['DHT11', 'DHT22']:
        pin = config.get('pin', 4)
        return DHT11Reader(sensor_id, pin, sensor_type, config)
    elif sensor_type == 'DS18B20':
        return DS18B20Reader(sensor_id, config)
    else:
        return MockSensorReader(sensor_id, sensor_type, config)