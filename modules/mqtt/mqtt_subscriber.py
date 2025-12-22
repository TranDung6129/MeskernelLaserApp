"""
MQTT Subscriber - Nhận dữ liệu từ MQTT broker
"""
import paho.mqtt.client as mqtt
import json
import threading
from typing import Dict, Any, Optional, Callable


class MQTTSubscriber:
    """MQTT Subscriber để nhận dữ liệu từ broker"""
    
    def __init__(self, broker_host: str, broker_port: int = 1883, 
                 username: Optional[str] = None, password: Optional[str] = None,
                 tls_enabled: bool = False, ca_certs: Optional[str] = None):
        """
        Khởi tạo MQTT subscriber
        
        Args:
            broker_host: IP hoặc hostname của MQTT broker
            broker_port: Port của MQTT broker (mặc định: 1883)
            username: Username để authenticate (optional)
            password: Password để authenticate (optional)
            tls_enabled: Bật TLS (optional)
            ca_certs: Đường dẫn đến CA certificates (optional)
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Callback khi nhận được message
        self.message_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
        # Auth
        if username is not None:
            try:
                self.client.username_pw_set(username=username, password=password)
            except Exception:
                self.client.username_pw_set(username, password)
        
        # TLS (optional)
        if tls_enabled:
            if ca_certs:
                self.client.tls_set(ca_certs=ca_certs)
            else:
                self.client.tls_set()
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối với broker"""
        if rc == 0:
            print(f"MQTT Subscriber: Đã kết nối với broker {self.broker_host}:{self.broker_port}")
        else:
            print(f"MQTT Subscriber: Kết nối thất bại, mã lỗi {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback khi ngắt kết nối"""
        if rc == 0:
            print("MQTT Subscriber: Đã ngắt kết nối")
        else:
            print(f"MQTT Subscriber: Ngắt kết nối bất thường (rc={rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback khi nhận được message"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            
            # Thử parse JSON
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                # Nếu không phải JSON, trả về string
                payload = payload_str
            
            # Gọi callback nếu có
            if self.message_callback:
                self.message_callback(topic, payload)
        except Exception as e:
            print(f"MQTT Subscriber: Lỗi xử lý message: {e}")
    
    def set_message_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback khi nhận được message"""
        self.message_callback = callback
    
    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe vào một topic"""
        self.client.subscribe(topic, qos)
        print(f"MQTT Subscriber: Đã subscribe vào topic: {topic}")
    
    def connect(self, keepalive: int = 60) -> bool:
        """
        Kết nối với MQTT broker
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            print(f"MQTT Subscriber: Đang kết nối với broker {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, keepalive)
            self.client.loop_start()  # Bắt đầu network loop trong background thread
            return True
        except Exception as e:
            print(f"MQTT Subscriber: Không thể kết nối: {e}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối với broker"""
        print("MQTT Subscriber: Đang ngắt kết nối...")
        self.client.loop_stop()
        self.client.disconnect()
        print("MQTT Subscriber: Đã ngắt kết nối")

