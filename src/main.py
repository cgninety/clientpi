"""
Main client application for IoT sensor network.
Reads sensor data and publishes to MQTT broker.
"""

import asyncio
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.config_manager import ClientConfigManager
from shared.logger import get_logger, setup_root_logger
from sensor_reader import SensorManager, create_sensor_reader
from mqtt_client import create_mqtt_client
from debug_cli import DebugConsole

class IoTSensorClient:
    """Main IoT sensor client application"""
    
    def __init__(self, config_path: str = "config/client_config.yaml"):
        # Load configuration
        self.config_manager = ClientConfigManager(config_path)
        self.config = self.config_manager.to_dict()
        
        # Setup logging
        setup_root_logger(self.config.get('logging', {}))
        self.logger = get_logger('iot_client')
        
        # Initialize components
        self.sensor_manager = None
        self.mqtt_client = None
        self.debug_console = None
        
        # Control flags
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Threads
        self.main_loop_thread = None
        self.console_thread = None
        
        self.logger.info(f"IoT Sensor Client initialized with ID: {self.config.get('client_id')}")
    
    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Initialize sensor manager
            sensor_config = {
                'sensors': [{
                    'id': self.config.get('client_id', 'sensor_001'),
                    'type': self.config.get('sensor', {}).get('type', 'DHT11'),
                    'pin': self.config.get('sensor', {}).get('pin', 4)
                }]
            }
            self.sensor_manager = SensorManager(sensor_config)
            
            # Initialize MQTT client
            mqtt_config = self.config.get('mqtt', {})
            client_id = self.config.get('client_id')
            self.mqtt_client = create_mqtt_client(mqtt_config, client_id)
            
            # Setup MQTT callbacks
            self.mqtt_client.on_connect_callback = self._on_mqtt_connect
            self.mqtt_client.on_disconnect_callback = self._on_mqtt_disconnect
            self.mqtt_client.on_message_callback = self._on_mqtt_message
            
            # Initialize debug console if enabled
            if self.config.get('debug', {}).get('console_enabled', True):
                self.debug_console = DebugConsole(self)
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def start(self) -> bool:
        """Start the client application"""
        if not self.initialize():
            return False
        
        try:
            # Connect to MQTT broker
            if not self.mqtt_client.connect():
                self.logger.error("Failed to connect to MQTT broker")
                return False
            
            # Start main loop in separate thread
            self.running = True
            self.main_loop_thread = threading.Thread(target=self._main_loop, daemon=False)
            self.main_loop_thread.start()
            
            # Start debug console if enabled
            if self.debug_console:
                self.console_thread = threading.Thread(target=self.debug_console.start, daemon=True)
                self.console_thread.start()
            
            self.logger.info("IoT Sensor Client started successfully")
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start client: {e}")
            return False
    
    def stop(self):
        """Stop the client application"""
        self.logger.info("Stopping IoT Sensor Client...")
        
        self.running = False
        self.shutdown_event.set()
        
        # Disconnect MQTT client
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        # Wait for main loop to finish
        if self.main_loop_thread and self.main_loop_thread.is_alive():
            self.main_loop_thread.join(timeout=10)
        
        # Stop debug console
        if self.debug_console:
            self.debug_console.stop()
        
        self.logger.info("IoT Sensor Client stopped")
    
    def _main_loop(self):
        """Main application loop"""
        update_interval = self.config.get('sensor', {}).get('update_interval', 30)
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Read all sensors
                readings = self.sensor_manager.read_all()
                
                # Publish sensor data
                for sensor_id, reading in readings.items():
                    if reading.is_valid():
                        self._publish_sensor_reading(sensor_id, reading)
                    else:
                        self.logger.warning(f"Invalid reading from sensor {sensor_id}: {reading.error}")
                
                # Wait for next reading
                self.shutdown_event.wait(update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.shutdown_event.wait(5)  # Wait before retrying
    
    def _publish_sensor_reading(self, sensor_id: str, reading):
        """Publish sensor reading to MQTT"""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            self.logger.warning("MQTT client not connected, skipping publish")
            return
        
        data = reading.to_dict()
        
        success = self.mqtt_client.publish_sensor_data(sensor_id, data)
        if success:
            self.logger.debug(f"Published sensor data for {sensor_id}")
        else:
            self.logger.error(f"Failed to publish sensor data for {sensor_id}")
    
    def _on_mqtt_connect(self):
        """Callback for MQTT connection"""
        self.logger.info("Connected to MQTT broker")
    
    def _on_mqtt_disconnect(self):
        """Callback for MQTT disconnection"""
        self.logger.warning("Disconnected from MQTT broker")
    
    def _on_mqtt_message(self, topic: str, payload: Dict[str, Any]):
        """Callback for MQTT messages"""
        self.logger.info(f"Received MQTT message on {topic}")
        # Handle configuration updates, commands, etc.
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        sensor_status = self.sensor_manager.get_sensor_status() if self.sensor_manager else {}
        mqtt_status = self.mqtt_client.get_status() if self.mqtt_client else {}
        
        return {
            'client_id': self.config.get('client_id'),
            'running': self.running,
            'sensors': sensor_status,
            'mqtt': mqtt_status,
            'config': {
                'update_interval': self.config.get('sensor', {}).get('update_interval'),
                'sensor_type': self.config.get('sensor', {}).get('type')
            }
        }
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.config_manager.reload()
            self.config = self.config_manager.to_dict()
            self.logger.info("Configuration reloaded")
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="IoT Sensor Client")
    parser.add_argument('--config', '-c', default='config/client_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='Run as daemon')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # Create client instance
    client = IoTSensorClient(args.config)
    
    # Override log level if verbose
    if args.verbose:
        client.config['logging']['level'] = 'DEBUG'
        setup_root_logger(client.config.get('logging', {}))
    
    try:
        # Start the client
        if client.start():
            if args.daemon:
                # Run as daemon
                while client.running:
                    time.sleep(1)
            else:
                # Keep main thread alive
                client.main_loop_thread.join()
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        client.logger.info("Interrupted by user")
    except Exception as e:
        client.logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        client.stop()

if __name__ == "__main__":
    main()