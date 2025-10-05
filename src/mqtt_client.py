"""
MQTT client for IoT sensor network.
Handles publishing sensor data and receiving configuration updates.
"""

import json
import ssl
import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    print("Warning: MQTT library not available.")

from shared.constants import MQTT_TOPICS, MessageType
from shared.logger import get_logger

class MQTTClient:
    """MQTT client for sensor communication"""
    
    def __init__(self, config: Dict[str, Any], client_id: Optional[str] = None):
        self.config = config
        self.client_id = client_id or f"iot_client_{uuid.uuid4().hex[:8]}"
        self.logger = get_logger(f"mqtt_{self.client_id}")
        
        # Connection state
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        
        # Threading
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._heartbeat_thread = None
        
        # Callbacks
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        
        # Initialize MQTT client
        if HAS_MQTT:
            self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
            self._setup_client()
        else:
            self.client = None
            self.logger.warning("MQTT library not available")
    
    def _setup_client(self):
        """Setup MQTT client with callbacks and configuration"""
        if not self.client:
            return
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_log = self._on_log
        
        # Configure authentication
        username = self.config.get('username')
        password = self.config.get('password')
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Configure TLS
        if self.config.get('use_tls', False):
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Load CA certificate if specified
            ca_cert = self.config.get('ca_cert')
            if ca_cert:
                context.load_verify_locations(ca_cert)
            
            # Client certificates
            cert_file = self.config.get('cert_file')
            key_file = self.config.get('key_file')
            if cert_file and key_file:
                context.load_cert_chain(cert_file, key_file)
            
            self.client.tls_set_context(context)
        
        # Set will message for ungraceful disconnections
        will_topic = MQTT_TOPICS['sensor_status'].format(client_id=self.client_id)
        will_payload = json.dumps({
            'status': 'offline',
            'timestamp': datetime.now().isoformat(),
            'reason': 'unexpected_disconnect'
        })
        self.client.will_set(will_topic, will_payload, qos=1, retain=True)
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        if not self.client:
            self.logger.error("MQTT client not available")
            return False
        
        try:
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 1883)
            keepalive = self.config.get('keepalive', 60)
            
            self.logger.info(f"Connecting to MQTT broker: {host}:{port}")
            
            result = self.client.connect(host, port, keepalive)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.client.loop_start()
                return True
            else:
                self.logger.error(f"Failed to connect to MQTT broker: {mqtt.error_string(result)}")
                return False
        
        except Exception as e:
            self.logger.error(f"MQTT connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if not self.client:
            return
        
        self._stop_event.set()
        
        # Stop heartbeat thread
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        # Publish offline status
        if self.connected:
            self.publish_status('offline', 'graceful_disconnect')
        
        self.client.loop_stop()
        self.client.disconnect()
        self.logger.info("Disconnected from MQTT broker")
    
    def publish_sensor_data(self, sensor_id: str, data: Dict[str, Any]) -> bool:
        """Publish sensor data"""
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker")
            return False
        
        topic = MQTT_TOPICS['sensor_data'].format(client_id=self.client_id)
        
        payload = {
            'sensor_id': sensor_id,
            'client_id': self.client_id,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'message_type': MessageType.SENSOR_DATA.value
        }
        
        return self._publish(topic, payload)
    
    def publish_status(self, status: str, reason: Optional[str] = None) -> bool:
        """Publish client status"""
        topic = MQTT_TOPICS['sensor_status'].format(client_id=self.client_id)
        
        payload = {
            'client_id': self.client_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'message_type': MessageType.SENSOR_STATUS.value
        }
        
        return self._publish(topic, payload, retain=True)
    
    def publish_heartbeat(self) -> bool:
        """Publish heartbeat message"""
        topic = MQTT_TOPICS['heartbeat'].format(client_id=self.client_id)
        
        payload = {
            'client_id': self.client_id,
            'timestamp': datetime.now().isoformat(),
            'message_type': MessageType.HEARTBEAT.value
        }
        
        return self._publish(topic, payload)
    
    def publish_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Publish debug message"""
        topic = MQTT_TOPICS['debug'].format(client_id=self.client_id)
        
        payload = {
            'client_id': self.client_id,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now().isoformat(),
            'message_type': MessageType.DEBUG.value
        }
        
        return self._publish(topic, payload)
    
    def _publish(self, topic: str, payload: Dict[str, Any], qos: int = 1, retain: bool = False) -> bool:
        """Internal publish method"""
        if not self.client or not self.connected:
            return False
        
        try:
            json_payload = json.dumps(payload, default=str)
            result = self.client.publish(topic, json_payload, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.mqtt_event('publish', topic, qos=qos, retain=retain)
                return True
            else:
                self.logger.error(f"Failed to publish to {topic}: {mqtt.error_string(result.rc)}")
                return False
        
        except Exception as e:
            self.logger.error(f"Publish error: {e}")
            return False
    
    def subscribe(self, topic_pattern: str, qos: int = 1) -> bool:
        """Subscribe to topic"""
        if not self.client or not self.connected:
            return False
        
        try:
            result = self.client.subscribe(topic_pattern, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.logger.mqtt_event('subscribe', topic_pattern, qos=qos)
                return True
            else:
                self.logger.error(f"Failed to subscribe to {topic_pattern}: {mqtt.error_string(result[0])}")
                return False
        
        except Exception as e:
            self.logger.error(f"Subscribe error: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for successful connection"""
        if rc == 0:
            self.connected = True
            self.reconnect_attempts = 0
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to configuration updates
            config_topic = MQTT_TOPICS['config'].format(client_id=self.client_id)
            self.subscribe(config_topic)
            
            # Publish online status
            self.publish_status('online', 'connected')
            
            # Start heartbeat thread
            self._start_heartbeat()
            
            if self.on_connect_callback:
                self.on_connect_callback()
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {mqtt.connack_string(rc)}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        self.logger.warning(f"Disconnected from MQTT broker: {mqtt.error_string(rc)}")
        
        if self.on_disconnect_callback:
            self.on_disconnect_callback()
        
        # Attempt reconnection if not intentional
        if rc != mqtt.MQTT_ERR_SUCCESS and not self._stop_event.is_set():
            self._attempt_reconnect()
    
    def _on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            self.logger.mqtt_event('message_received', topic)
            
            # Handle configuration updates
            if 'config' in topic:
                self._handle_config_update(payload)
            
            if self.on_message_callback:
                self.on_message_callback(topic, payload)
        
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for successful publish"""
        self.logger.debug(f"Message published: {mid}")
    
    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT client logs"""
        self.logger.debug(f"MQTT log: {buf}")
    
    def _handle_config_update(self, payload: Dict[str, Any]):
        """Handle configuration update messages"""
        try:
            self.logger.info("Received configuration update")
            # Implementation depends on how config updates should be handled
            # Could trigger a callback or update internal configuration
        except Exception as e:
            self.logger.error(f"Failed to handle config update: {e}")
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to MQTT broker"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = min(30, 2 ** self.reconnect_attempts)  # Exponential backoff
        
        self.logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        time.sleep(delay)
        
        try:
            self.client.reconnect()
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
    
    def _start_heartbeat(self):
        """Start heartbeat thread"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Heartbeat loop"""
        heartbeat_interval = self.config.get('heartbeat_interval', 30)
        
        while not self._stop_event.is_set():
            if self.connected:
                self.publish_heartbeat()
            
            self._stop_event.wait(heartbeat_interval)
    
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker"""
        return self.connected
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            'client_id': self.client_id,
            'connected': self.connected,
            'reconnect_attempts': self.reconnect_attempts,
            'broker_host': self.config.get('host'),
            'broker_port': self.config.get('port')
        }

class MockMQTTClient:
    """Mock MQTT client for testing"""
    
    def __init__(self, config: Dict[str, Any], client_id: Optional[str] = None):
        self.client_id = client_id or f"mock_client_{uuid.uuid4().hex[:8]}"
        self.config = config
        self.logger = get_logger(f"mock_mqtt_{self.client_id}")
        self.connected = False
        self.published_messages = []
    
    def connect(self) -> bool:
        self.connected = True
        self.logger.info("Mock MQTT client connected")
        return True
    
    def disconnect(self):
        self.connected = False
        self.logger.info("Mock MQTT client disconnected")
    
    def publish_sensor_data(self, sensor_id: str, data: Dict[str, Any]) -> bool:
        if not self.connected:
            return False
        
        message = {
            'sensor_id': sensor_id,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.published_messages.append(('sensor_data', message))
        self.logger.info(f"Mock published sensor data: {sensor_id}")
        return True
    
    def publish_status(self, status: str, reason: Optional[str] = None) -> bool:
        if not self.connected:
            return False
        
        message = {
            'status': status,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.published_messages.append(('status', message))
        self.logger.info(f"Mock published status: {status}")
        return True
    
    def publish_heartbeat(self) -> bool:
        return self.connected
    
    def publish_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        return self.connected
    
    def is_connected(self) -> bool:
        return self.connected
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'connected': self.connected,
            'published_count': len(self.published_messages)
        }

def create_mqtt_client(config: Dict[str, Any], client_id: Optional[str] = None) -> MQTTClient:
    """Factory function to create MQTT client"""
    if HAS_MQTT and not config.get('mock_mode', False):
        return MQTTClient(config, client_id)
    else:
        return MockMQTTClient(config, client_id)