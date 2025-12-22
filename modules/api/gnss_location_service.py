"""
GNSS Location Service - Service để nhận tọa độ từ GNSS RTK qua MQTT và tự động cập nhật tốc độ khoan
"""
import math
import threading
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import deque

import sys
import os
# Thêm path để import mqtt_subscriber
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.mqtt.mqtt_subscriber import MQTTSubscriber
from .holes_api import HolesAPIClient


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa hai điểm GPS bằng công thức Haversine (meters)
    
    Args:
        lat1, lon1: Tọa độ điểm 1 (degrees)
        lat2, lon2: Tọa độ điểm 2 (degrees)
        
    Returns:
        Khoảng cách tính bằng meters
    """
    # Bán kính Trái Đất (meters)
    R = 6371000
    
    # Chuyển đổi sang radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Công thức Haversine
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


class GNSSLocationService:
    """Service để nhận tọa độ từ GNSS RTK và tự động cập nhật tốc độ khoan"""
    
    def __init__(self,
                 mqtt_broker_host: str, mqtt_broker_port: int = 1883,
                 mqtt_topic: str = "device/+/upload",
                 api_client: Optional[HolesAPIClient] = None,
                 project_id: Optional[int] = None,
                 max_distance_threshold: float = 10.0,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 mqtt_tls_enabled: bool = False,
                 mqtt_ca_certs: Optional[str] = None):
        """
        Khởi tạo GNSS Location Service
        
        Args:
            mqtt_broker_host: MQTT broker host
            mqtt_broker_port: MQTT broker port
            mqtt_topic: MQTT topic để subscribe
            api_client: HolesAPIClient instance (Optional - nếu muốn update drilling data)
            project_id: API project ID (Optional - nếu muốn update drilling data)
            max_distance_threshold: Khoảng cách tối đa để coi là "gần" (meters)
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
            mqtt_tls_enabled: Bật TLS (optional)
            mqtt_ca_certs: Đường dẫn CA certificates (optional)
        """
        self.api_client = api_client
        self.project_id = project_id
        self.max_distance_threshold = max_distance_threshold
        
        # MQTT subscriber
        self.mqtt_subscriber = MQTTSubscriber(
            broker_host=mqtt_broker_host,
            broker_port=mqtt_broker_port,
            username=mqtt_username,
            password=mqtt_password,
            tls_enabled=mqtt_tls_enabled,
            ca_certs=mqtt_ca_certs
        )
        self.mqtt_subscriber.set_message_callback(self._on_mqtt_message)
        self.mqtt_topic = mqtt_topic
        
        # Cache danh sách holes
        self.holes_cache: List[Dict] = []
        self.holes_cache_timestamp: float = 0
        self.cache_ttl: float = 300.0  # Cache 5 phút
        self.cache_lock = threading.Lock()
        
        # Dữ liệu tốc độ khoan hiện tại
        self.current_velocity_ms: Optional[float] = None
        self.current_depth_m: Optional[float] = None
        
        # Thống kê
        self.stats = {
            'messages_received': 0,
            'locations_processed': 0,
            'holes_updated': 0,
            'last_update_time': None,
            'last_location': None
        }
        self.stats_lock = threading.Lock()
        
        # Running state
        self.running = False
    
    def set_drilling_data(self, velocity_ms: float, depth_m: float):
        """
        Set dữ liệu tốc độ khoan hiện tại
        
        Args:
            velocity_ms: Tốc độ khoan (m/s)
            depth_m: Chiều sâu (meters)
        """
        self.current_velocity_ms = velocity_ms
        self.current_depth_m = depth_m
    
    def _parse_nmea_gpgga(self, nmea_str: str) -> Optional[Dict[str, float]]:
        """
        Parse NMEA GGA sentence (bất kỳ constellation nào)
        Format: $xxGGA,time,lat,NS,lon,EW,quality,numSV,HDOP,alt,altUnit,sep,sepUnit,diffAge,diffStation*cs
        
        Supported:
        - GPGGA: GPS only
        - GNGGA: Multi-GNSS (GPS + GLONASS + Galileo + BeiDou)
        - GLGGA: GLONASS only
        - GAGGA: Galileo only
        - BDGGA: BeiDou only
        
        Example: $GPGGA,090110,2104.431759,N,10546.62665,E,1,28,1.1,.00,M,-13.46,M,43,*66
        Example: $GNGGA,090110,2104.431759,N,10546.62665,E,1,28,1.1,.00,M,-13.46,M,43,*66
        """
        try:
            # Chấp nhận bất kỳ sentence GGA nào (GPGGA, GNGGA, GLGGA, GAGGA, BDGGA)
            if not (nmea_str.startswith('$') and 'GGA' in nmea_str[:7]):
                return None
            
            parts = nmea_str.split(',')
            if len(parts) < 10:
                return None
            
            # Lat
            raw_lat = parts[2]
            lat_dir = parts[3]
            if not raw_lat or not lat_dir:
                return None
            
            # Convert DDMM.MMMM to DD.DDDD
            # 2104.431759 -> 21 degrees, 04.431759 minutes
            if '.' in raw_lat:
                dot_idx = raw_lat.find('.')
                deg_len = dot_idx - 2
                lat_deg = float(raw_lat[:deg_len])
                lat_min = float(raw_lat[deg_len:])
                lat = lat_deg + lat_min / 60.0
            else:
                return None
                
            if lat_dir == 'S':
                lat = -lat
            
            # Lon
            raw_lon = parts[4]
            lon_dir = parts[5]
            if not raw_lon or not lon_dir:
                return None
            
            # 10546.62665 -> 105 degrees, 46.62665 minutes
            if '.' in raw_lon:
                dot_idx = raw_lon.find('.')
                deg_len = dot_idx - 2
                lon_deg = float(raw_lon[:deg_len])
                lon_min = float(raw_lon[deg_len:])
                lon = lon_deg + lon_min / 60.0
            else:
                return None
                
            if lon_dir == 'W':
                lon = -lon
            
            # Altitude
            try:
                alt = float(parts[9])
            except ValueError:
                alt = 0.0
                
            return {'lat': lat, 'lon': lon, 'elevation': alt}
            
        except Exception as e:
            print(f"Error parsing NMEA GPGGA: {e}")
            return None

    def _on_mqtt_message(self, topic: str, payload: Dict[str, Any]):
        """Callback khi nhận được message từ MQTT"""
        with self.stats_lock:
            self.stats['messages_received'] += 1
        
        try:
            # Parse tọa độ từ payload
            lat = None
            lon = None
            elevation = None
            
            # 1. Thử parse NMEA string trước (nếu payload là string)
            if isinstance(payload, str) and payload.startswith('$'):
                nmea_data = self._parse_nmea_gpgga(payload.strip())
                if nmea_data:
                    lat = nmea_data['lat']
                    lon = nmea_data['lon']
                    elevation = nmea_data['elevation']
            
            # 2. Nếu chưa có, thử parse JSON dict/string
            if lat is None:
                if isinstance(payload, dict):
                    # Format 1: lat/lon trực tiếp
                    lat = payload.get('lat') or payload.get('latitude') or payload.get('gps_lat')
                    lon = payload.get('lon') or payload.get('longitude') or payload.get('gps_lon')
                    elevation = payload.get('elevation') or payload.get('alt') or payload.get('gps_elevation')
                    
                    # Format 2: nằm trong object 'gps' hoặc 'location'
                    if lat is None:
                         gps_obj = payload.get('gps') or payload.get('location') or payload.get('gnss')
                         if isinstance(gps_obj, dict):
                             lat = gps_obj.get('lat') or gps_obj.get('latitude')
                             lon = gps_obj.get('lon') or gps_obj.get('longitude')
                             elevation = gps_obj.get('elevation') or gps_obj.get('alt')
                             
                elif isinstance(payload, str):
                    # Thử parse JSON string
                    try:
                        import json
                        data = json.loads(payload)
                        # Format 1
                        lat = data.get('lat') or data.get('latitude') or data.get('gps_lat')
                        lon = data.get('lon') or data.get('longitude') or data.get('gps_lon')
                        elevation = data.get('elevation') or data.get('alt') or data.get('gps_elevation')
                        
                        # Format 2
                        if lat is None:
                             gps_obj = data.get('gps') or data.get('location') or data.get('gnss')
                             if isinstance(gps_obj, dict):
                                 lat = gps_obj.get('lat') or gps_obj.get('latitude')
                                 lon = gps_obj.get('lon') or gps_obj.get('longitude')
                                 elevation = gps_obj.get('elevation') or gps_obj.get('alt')
                    except:
                        pass
            
            if lat is None or lon is None:
                print(f"GNSS Location Service: Không tìm thấy tọa độ trong payload: {payload}")
                return
            
            # Xử lý tọa độ
            self._process_location(float(lat), float(lon), elevation)
            
        except Exception as e:
            print(f"GNSS Location Service: Lỗi xử lý message: {e}")
            import traceback
            traceback.print_exc()

    def _process_location(self, lat: float, lon: float, elevation: Optional[float] = None):
        """Xử lý tọa độ GPS và tìm hố khoan gần nhất"""
        with self.stats_lock:
            self.stats['locations_processed'] += 1
            self.stats['last_location'] = {'lat': lat, 'lon': lon, 'elevation': elevation}
        
        # Nếu không có API client hoặc project ID thì chỉ dừng lại ở việc nhận tọa độ
        if not self.api_client or not self.project_id:
            return

        try:
            # Lấy danh sách holes (có cache)
            holes = self._get_holes()
            
            if not holes:
                print("GNSS Location Service: Không có holes để so sánh")
                return
            
            # Tìm hố khoan gần nhất
            nearest_hole, distance = self._find_nearest_hole(holes, lat, lon)
            
            if not nearest_hole:
                print(f"GNSS Location Service: Không tìm thấy hố khoan gần (khoảng cách: {distance:.2f}m)")
                return
            
            if distance > self.max_distance_threshold:
                print(f"GNSS Location Service: Hố khoan gần nhất quá xa ({distance:.2f}m > {self.max_distance_threshold}m)")
                return
            
            # Cập nhật tốc độ khoan cho hố khoan gần nhất
            if self.current_velocity_ms is not None and self.current_depth_m is not None:
                self._update_hole_drilling_data(nearest_hole, distance)
            
        except Exception as e:
            print(f"GNSS Location Service: Lỗi xử lý location: {e}")
    
    def _get_holes(self) -> List[Dict]:
        """Lấy danh sách holes (có cache)"""
        current_time = time.time()
        
        with self.cache_lock:
            # Kiểm tra cache
            if (
                self.holes_cache
                and current_time - self.holes_cache_timestamp < self.cache_ttl
            ):
                return self.holes_cache
            
            # Lấy từ API qua base_url đã có /api
            result = self.api_client.get_all_holes(self.project_id)
            
            if result and result.get('success'):
                holes = result.get('holes', [])
                self.holes_cache = holes
                self.holes_cache_timestamp = current_time
                print(f"GNSS Location Service: Đã tải {len(holes)} holes từ API")
                return holes
            else:
                print("GNSS Location Service: Không thể lấy holes từ API")
                return []
    
    def _find_nearest_hole(self, holes: List[Dict], lat: float, lon: float) -> Tuple[Optional[Dict], float]:
        """
        Tìm hố khoan gần nhất với tọa độ cho trước
        
        Returns:
            Tuple (hole_dict, distance_meters)
        """
        nearest_hole = None
        min_distance = float('inf')
        
        for hole in holes:
            hole_lat = hole.get('gps_lat')
            hole_lon = hole.get('gps_lon')
            
            if hole_lat is None or hole_lon is None:
                continue
            
            distance = haversine_distance(lat, lon, hole_lat, hole_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_hole = hole
        
        return nearest_hole, min_distance
    
    def _update_hole_drilling_data(self, hole: Dict, distance: float):
        """Cập nhật dữ liệu tốc độ khoan cho hố khoan qua endpoint drilling-speed."""
        try:
            hole_id_str = hole.get('hole_id') or hole.get('id')
            if not hole_id_str:
                print(f"GNSS Location Service: Hole không có hole_id: {hole}")
                return

            if self.current_velocity_ms is None or self.current_depth_m is None:
                return

            # Gửi dữ liệu qua endpoint POST drilling-speed
            result = self.api_client.post_drilling_speed(
                project_id=self.project_id,
                hole_id=hole_id_str,
                speed=self.current_velocity_ms,
                depth=self.current_depth_m,
                sensor_id="GNSS_RIG",
            )

            if result and result.get("success"):
                with self.stats_lock:
                    self.stats["holes_updated"] += 1
                    self.stats["last_update_time"] = time.time()

                print(
                    f"GNSS Location Service: Đã gửi drilling-speed cho hố {hole_id_str} "
                    f"(khoảng cách: {distance:.2f}m, "
                    f"tốc độ: {self.current_velocity_ms:.4f}, "
                    f"độ sâu: {self.current_depth_m:.2f}m)"
                )
            else:
                print(f"GNSS Location Service: Không thể gửi drilling-speed cho hố {hole_id_str}")

        except Exception as e:
            print(f"GNSS Location Service: Lỗi cập nhật hole (drilling-speed): {e}")
    
    def start(self):
        """Bắt đầu service"""
        if self.running:
            return
        
        # Kết nối MQTT
        if not self.mqtt_subscriber.connect():
            print("GNSS Location Service: Không thể kết nối MQTT broker")
            return
        
        # Subscribe topic
        self.mqtt_subscriber.subscribe(self.mqtt_topic)
        
        self.running = True
        print(f"GNSS Location Service: Đã khởi động (topic: {self.mqtt_topic})")
    
    def stop(self):
        """Dừng service"""
        if not self.running:
            return
        
        self.running = False
        self.mqtt_subscriber.disconnect()
        
        print(f"GNSS Location Service: Đã dừng. Stats: {self.get_stats()}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê"""
        with self.stats_lock:
            return self.stats.copy()
    
    def clear_cache(self):
        """Xóa cache holes"""
        with self.cache_lock:
            self.holes_cache.clear()
            self.holes_cache_timestamp = 0

