"""
Debug console for IoT sensor client.
Provides interactive debugging and monitoring capabilities.
"""

import cmd
import threading
import json
from typing import Dict, Any, Optional, TYPE_CHECKING
from shared.logger import get_logger

if TYPE_CHECKING:
    from main import IoTSensorClient

class DebugConsole(cmd.Cmd):
    """Interactive debug console for IoT sensor client"""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║                    IoT Sensor Debug Console                  ║
║                                                              ║
║  Type 'help' for available commands                         ║
║  Type 'status' to see current system status                 ║
║  Type 'quit' or 'exit' to close console                     ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    prompt = "IoT> "
    
    def __init__(self, client: "IoTSensorClient"):
        super().__init__()
        self.client = client
        self.logger = get_logger('debug_console')
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start the debug console"""
        self.running = True
        self._thread = threading.Thread(target=self._run_console, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the debug console"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _run_console(self) -> None:
        """Run the console in a separate thread"""
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            print("\nConsole interrupted")
        except Exception as e:
            self.logger.error(f"Console error: {e}")
    
    def do_status(self, args: str) -> None:
        """Show system status"""
        try:
            status = self.client.get_status()
            print("\n" + "="*60)
            print("SYSTEM STATUS")
            print("="*60)
            
            # Client info
            print(f"Client ID: {status.get('client_id', 'Unknown')}")
            print(f"Running: {status.get('running', False)}")
            print()
            
            # MQTT status
            mqtt_status = status.get('mqtt', {})
            print("MQTT Status:")
            print(f"  Connected: {mqtt_status.get('connected', False)}")
            print(f"  Broker: {mqtt_status.get('broker_host', 'Unknown')}:{mqtt_status.get('broker_port', 'Unknown')}")
            print(f"  Reconnect Attempts: {mqtt_status.get('reconnect_attempts', 0)}")
            print()
            
            # Sensor status
            sensors = status.get('sensors', {})
            print("Sensor Status:")
            if sensors:
                for sensor_id, sensor_info in sensors.items():
                    print(f"  {sensor_id}:")
                    print(f"    Type: {sensor_info.get('sensor_type', 'Unknown')}")
                    print(f"    Healthy: {sensor_info.get('healthy', False)}")
                    print(f"    Error Count: {sensor_info.get('error_count', 0)}")
                    print(f"    Last Reading: {sensor_info.get('last_reading_time', 'Never')}")
                    if sensor_info.get('last_temperature'):
                        print(f"    Temperature: {sensor_info.get('last_temperature')}°C")
                    if sensor_info.get('last_humidity'):
                        print(f"    Humidity: {sensor_info.get('last_humidity')}%")
            else:
                print("  No sensors configured")
            print()
            
            # Configuration
            config = status.get('config', {})
            print("Configuration:")
            print(f"  Update Interval: {config.get('update_interval', 'Unknown')}s")
            print(f"  Sensor Type: {config.get('sensor_type', 'Unknown')}")
            
        except Exception as e:
            print(f"Error getting status: {e}")
    
    def do_sensors(self, args: str) -> None:
        """Show detailed sensor information"""
        if not self.client.sensor_manager:
            print("Sensor manager not initialized")
            return
        
        try:
            readings = self.client.sensor_manager.read_all()
            print("\n" + "="*60)
            print("SENSOR READINGS")
            print("="*60)
            
            for sensor_id, reading in readings.items():
                print(f"\nSensor: {sensor_id}")
                print(f"  Type: {reading.sensor_type}")
                print(f"  Timestamp: {reading.timestamp}")
                
                if reading.is_valid():
                    if reading.temperature is not None:
                        print(f"  Temperature: {reading.temperature}°C")
                    if reading.humidity is not None:
                        print(f"  Humidity: {reading.humidity}%")
                    if reading.pressure is not None:
                        print(f"  Pressure: {reading.pressure} hPa")
                else:
                    print(f"  Error: {reading.error}")
        
        except Exception as e:
            print(f"Error reading sensors: {e}")
    
    def do_mqtt_test(self, args: str) -> None:
        """Test MQTT connection and publishing"""
        if not self.client.mqtt_client:
            print("MQTT client not initialized")
            return
        
        try:
            if not self.client.mqtt_client.is_connected():
                print("MQTT client not connected")
                return
            
            # Test publish
            test_data: Dict[str, Any] = {
                'test': True,
                'message': 'Debug console test',
                'timestamp': '2023-01-01T00:00:00'
            }
            
            success = self.client.mqtt_client.publish_debug("Debug console test", test_data)
            if success:
                print("✓ Test message published successfully")
            else:
                print("✗ Failed to publish test message")
        
        except Exception as e:
            print(f"Error testing MQTT: {e}")
    
    def do_config(self, args: str) -> None:
        """Show current configuration"""
        try:
            config = self.client.config
            print("\n" + "="*60)
            print("CONFIGURATION")
            print("="*60)
            print(json.dumps(config, indent=2, default=str))
        except Exception as e:
            print(f"Error showing config: {e}")
    
    def do_reload_config(self, args: str) -> None:
        """Reload configuration from file"""
        try:
            self.client.reload_config()
            print("✓ Configuration reloaded successfully")
        except Exception as e:
            print(f"✗ Failed to reload configuration: {e}")
    
    def do_logs(self, args: str) -> None:
        """Show recent log entries"""
        args = args.strip()
        lines = 20  # default
        
        if args:
            try:
                lines = int(args)
            except ValueError:
                print("Invalid number of lines")
                return
        
        try:
            import os
            log_file = os.path.join("logs", f"{self.client.config.get('client_id', 'iot_client')}.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_lines = f.readlines()
                    recent_lines = log_lines[-lines:]
                    
                print(f"\n=== Last {len(recent_lines)} log entries ===")
                for line in recent_lines:
                    print(line.rstrip())
            else:
                print(f"Log file not found: {log_file}")
        
        except Exception as e:
            print(f"Error reading logs: {e}")
    
    def do_simulate_error(self, args: str) -> None:
        """Simulate sensor error for testing"""
        print("Simulating sensor error...")
        # This would typically inject an error into the sensor system
        # Implementation depends on the sensor architecture
        print("Error simulation not implemented yet")
    
    def do_mqtt_status(self, args: str) -> None:
        """Show MQTT connection details"""
        if not self.client.mqtt_client:
            print("MQTT client not initialized")
            return
        
        try:
            status = self.client.mqtt_client.get_status()
            print("\n" + "="*60)
            print("MQTT STATUS")
            print("="*60)
            print(f"Client ID: {status.get('client_id')}")
            print(f"Connected: {status.get('connected')}")
            print(f"Broker Host: {status.get('broker_host')}")
            print(f"Broker Port: {status.get('broker_port')}")
            print(f"Reconnect Attempts: {status.get('reconnect_attempts')}")
        
        except Exception as e:
            print(f"Error getting MQTT status: {e}")
    
    def do_help_extended(self, args: str) -> None:
        """Show extended help with examples"""
        print("""
Extended Help:

Commands:
  status                    - Show complete system status
  sensors                   - Read and display current sensor values
  mqtt_test                 - Test MQTT connection and publishing
  mqtt_status              - Show detailed MQTT connection info
  config                   - Display current configuration
  reload_config            - Reload configuration from file
  logs [lines]             - Show recent log entries (default: 20)
  simulate_error           - Simulate sensor error for testing
  quit/exit                - Exit the debug console

Examples:
  IoT> status              # Show system overview
  IoT> sensors             # Read all sensors now
  IoT> logs 50             # Show last 50 log entries
  IoT> mqtt_test           # Test MQTT publishing
""")
    
    def do_quit(self, args: str) -> bool:
        """Exit the debug console"""
        print("Goodbye!")
        return True
    
    def do_exit(self, args: str) -> bool:
        """Exit the debug console"""
        return self.do_quit(args)
    
    def do_EOF(self, args: str) -> bool:
        """Handle Ctrl+D"""
        print("\nGoodbye!")
        return True
    
    def emptyline(self) -> bool:
        """Do nothing on empty line"""
        return False
    
    def default(self, line: str) -> None:
        """Handle unknown commands"""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands")

class WebDebugConsole:
    """Web-based debug console (future implementation)"""
    
    def __init__(self, client: "IoTSensorClient", port: int = 8081):
        self.client = client
        self.port = port
        self.logger = get_logger('web_console')
    
    def start(self) -> None:
        """Start web console server"""
        # Implementation would use Flask/FastAPI to create a web interface
        self.logger.info(f"Web debug console would start on port {self.port}")
        pass
    
    def stop(self) -> None:
        """Stop web console server"""
        pass