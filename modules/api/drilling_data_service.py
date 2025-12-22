"""
Drilling Data Service - Service để gửi dữ liệu tốc độ khoan lên API
"""
import time
import threading
from typing import Optional, Dict, Any, Union
from datetime import datetime
from collections import deque

from .holes_api import HolesAPIClient


class DrillingDataService:
    """Service để gửi dữ liệu tốc độ khoan lên API"""
    
    def __init__(self, api_client: HolesAPIClient, project_id: int, hole_id: Optional[Union[int, str]] = None):
        """
        Khởi tạo service
        
        Args:
            api_client: HolesAPIClient instance
            project_id: API project ID
            hole_id: API hole ID (có thể là số hoặc string như "LK1", "HK01")
        """
        self.api_client = api_client
        self.project_id = project_id
        self.hole_id = hole_id
        
        # Queue để lưu dữ liệu chờ gửi
        self.data_queue: deque = deque(maxlen=1000)
        self.send_interval = 2.0  # Gửi mỗi 2 giây
        self.last_send_time = 0.0
        
        # Thread để gửi dữ liệu
        self.send_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Thống kê
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'last_send_time': None
        }
    
    def set_hole_id(self, hole_id: Union[int, str]):
        """Set API hole ID (có thể là số hoặc string)"""
        with self.lock:
            self.hole_id = hole_id
    
    def add_velocity_data(self, velocity_ms: float, depth_m: float, timestamp: Optional[float] = None):
        """
        Thêm dữ liệu tốc độ khoan vào queue
        
        Args:
            velocity_ms: Tốc độ khoan (m/s)
            depth_m: Chiều sâu (meters)
            timestamp: Timestamp (optional, mặc định là thời gian hiện tại)
        """
        if timestamp is None:
            timestamp = time.time()
        
        data = {
            'velocity_ms': velocity_ms,
            'depth_m': depth_m,
            'timestamp': timestamp
        }
        
        with self.lock:
            self.data_queue.append(data)
    
    def start(self):
        """Bắt đầu service gửi dữ liệu"""
        if self.running:
            return
        
        if not self.hole_id:
            print("Warning: DrillingDataService started without hole_id")
            return
        
        self.running = True
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()
        print(f"DrillingDataService started for project {self.project_id}, hole {self.hole_id}")
    
    def stop(self):
        """Dừng service và gửi dữ liệu còn lại"""
        if not self.running:
            return
        
        self.running = False
        
        # Gửi dữ liệu còn lại
        self._send_pending_data()
        
        if self.send_thread:
            self.send_thread.join(timeout=5.0)
        
        print(f"DrillingDataService stopped. Stats: {self.stats}")
    
    def _send_loop(self):
        """Loop gửi dữ liệu định kỳ"""
        while self.running:
            try:
                current_time = time.time()
                
                # Kiểm tra xem đã đến lúc gửi chưa
                if current_time - self.last_send_time >= self.send_interval:
                    self._send_pending_data()
                    self.last_send_time = current_time
                
                # Sleep một chút để tránh busy loop
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error in DrillingDataService send loop: {e}")
                time.sleep(1.0)
    
    def _send_pending_data(self):
        """Gửi dữ liệu trong queue"""
        if not self.hole_id:
            return
        
        with self.lock:
            if not self.data_queue:
                return
            
            # Lấy dữ liệu mới nhất (có thể lấy nhiều điểm để batch update)
            # Hiện tại sẽ chỉ gửi điểm mới nhất
            latest_data = self.data_queue[-1] if self.data_queue else None
            
            if not latest_data:
                return
        
        # Gửi dữ liệu lên API
        try:
            # Chuyển đổi timestamp từ float (time.time()) sang datetime
            timestamp = None
            if latest_data.get('timestamp'):
                try:
                    # timestamp là float (seconds since epoch)
                    timestamp = datetime.utcfromtimestamp(latest_data['timestamp'])
                except (ValueError, TypeError, OSError):
                    # Nếu không thể convert, dùng thời gian hiện tại
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            # Sử dụng method post_drilling_speed để gửi dữ liệu lên endpoint drilling-speed
            # Format: POST /api/projects/{projectId}/holes/{holeId}/drilling-speed
            # Body: {"speed": float, "depth": float, "timestamp": "ISO8601", "sensor_id": "optional"}
            result = self.api_client.post_drilling_speed(
                project_id=self.project_id,
                hole_id=self.hole_id,
                speed=latest_data['velocity_ms'],  # Tốc độ khoan (m/s)
                depth=latest_data['depth_m'],      # Chiều sâu (meters)
                timestamp=timestamp,                # Timestamp (UTC)
                sensor_id="LASER_SENSOR"           # ID cảm biến
            )
            
            success = result is not None and result.get('success', False)
            
            with self.lock:
                if success:
                    self.stats['total_sent'] += 1
                    self.stats['last_send_time'] = datetime.now().isoformat()
                    # Xóa dữ liệu đã gửi
                    if self.data_queue:
                        self.data_queue.clear()
                else:
                    self.stats['total_failed'] += 1
                    # Log lỗi chi tiết để debug
                    print(f"Failed to send drilling data: {result}")
        except Exception as e:
            print(f"Error sending drilling data to API: {e}")
            import traceback
            traceback.print_exc()
            with self.lock:
                self.stats['total_failed'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê"""
        with self.lock:
            return self.stats.copy()

