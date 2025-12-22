"""
Holes API Client - Client để giao tiếp với Holes API
"""
import requests
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone


class HolesAPIClient:
    """Client để giao tiếp với Holes API"""
    
    def __init__(self, base_url: str = "https://nomin.wintech.io.vn/api", timeout: int = 10):
        """
        Khởi tạo API client
        
        Args:
            base_url: Base URL của API (mặc định: https://nomin.wintech.io.vn/api)
            timeout: Timeout cho requests (giây)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Thực hiện HTTP request
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (relative path)
            **kwargs: Additional arguments cho requests
            
        Returns:
            Response data dictionary hoặc None nếu có lỗi
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"API timeout: {url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"API connection error: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None
        except Exception as e:
            print(f"API unexpected error: {e}")
            return None
    
    def get_all_holes(self, project_id: int) -> Optional[Dict]:
        """
        Lấy tất cả lỗ khoan của một dự án.
        
        Args:
            project_id: ID của dự án
            
        Returns:
            Dictionary chứa danh sách holes hoặc None nếu có lỗi.
        
        Ghi chú:
        - `base_url` đã bao gồm `/api`, ví dụ: `https://nomin.wintech.io.vn/api`
        - Endpoint chuẩn: `/projects/{project_id}/holes`
          → URL đầy đủ: `https://nomin.wintech.io.vn/api/projects/{project_id}/holes`
        """
        endpoint = f"/projects/{project_id}/holes"
        return self._make_request("GET", endpoint)
    
    def get_design_holes(self, project_id: int, design_id: int) -> Optional[Dict]:
        """
        Lấy tất cả lỗ khoan của một thiết kế
        
        Args:
            project_id: ID của dự án
            design_id: ID của thiết kế
            
        Returns:
            Dictionary chứa danh sách holes hoặc None nếu có lỗi
        """
        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/designs/{design_id}/holes"
        return self._make_request('GET', endpoint)
    
    def get_hole(self, project_id: int, hole_id: Union[int, str]) -> Optional[Dict]:
        """
        Lấy thông tin chi tiết của một lỗ khoan
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            
        Returns:
            Dictionary chứa thông tin hole hoặc None nếu có lỗi
        """
        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/holes/{hole_id}"
        return self._make_request('GET', endpoint)
    
    def find_hole_by_hole_id(self, project_id: int, hole_id_str: str) -> Optional[Dict]:
        """
        Tìm lỗ khoan theo hole_id (string như "H1", "HK01", etc.)
        
        Args:
            project_id: ID của dự án
            hole_id_str: hole_id string (ví dụ: "H1", "HK01")
            
        Returns:
            Dictionary chứa thông tin hole hoặc None nếu không tìm thấy
        """
        all_holes = self.get_all_holes(project_id)
        if not all_holes or not all_holes.get('success'):
            return None
        
        holes = all_holes.get('holes', [])
        for hole in holes:
            if hole.get('hole_id') == hole_id_str:
                return hole
        
        return None
    
    def update_hole(self, project_id: int, hole_id: Union[int, str], data: Dict[str, Any]) -> Optional[Dict]:
        """
        Cập nhật thông tin của một lỗ khoan
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            data: Dictionary chứa các field cần cập nhật
            
        Returns:
            Dictionary chứa thông tin hole đã cập nhật hoặc None nếu có lỗi
        """
        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/holes/{hole_id}"
        return self._make_request('PUT', endpoint, json=data)
    
    def update_hole_gps(self, project_id: int, hole_id: Union[int, str], lon: float, lat: float, elevation: Optional[float] = None) -> Optional[Dict]:
        """
        Cập nhật tọa độ GPS của một lỗ khoan
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            lon: Kinh độ GPS (degrees)
            lat: Vĩ độ GPS (degrees)
            elevation: Độ cao GPS (meters, optional)
            
        Returns:
            Dictionary chứa thông tin hole đã cập nhật hoặc None nếu có lỗi
        """
        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/holes/{hole_id}/gps"
        data = {
            "lon": lon,
            "lat": lat
        }
        if elevation is not None:
            data["elevation"] = elevation
        
        return self._make_request('PATCH', endpoint, json=data)
    
    def update_hole_depth(self, project_id: int, hole_id: Union[int, str], depth: float) -> Optional[Dict]:
        """
        Cập nhật chiều sâu lỗ khoan
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            depth: Chiều sâu (meters)
            
        Returns:
            Dictionary chứa thông tin hole đã cập nhật hoặc None nếu có lỗi
        """
        return self.update_hole(project_id, hole_id, {"depth": depth})
    
    def update_hole_drilling_speed(self, project_id: int, hole_id: Union[int, str], velocity_ms: float, depth: Optional[float] = None) -> Optional[Dict]:
        """
        Cập nhật tốc độ khoan (drilling speed) của một lỗ khoan.
        
        Ghi chú: method này giữ lại để tương thích với code cũ, hiện tại
        chỉ cập nhật trường depth bằng phương thức PUT /projects/{id}/holes/{id}.
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
        """
        data: Dict[str, Any] = {}
        if depth is not None:
            data["depth"] = depth
        return self.update_hole(project_id, hole_id, data)
    
    def batch_update_holes(self, project_id: int, holes: List[Dict[str, Any]]) -> Optional[Dict]:
        """
        Cập nhật nhiều lỗ khoan cùng lúc
        
        Args:
            project_id: ID của dự án
            holes: List các dictionary chứa id và các field cần cập nhật
            
        Returns:
            Dictionary chứa kết quả cập nhật hoặc None nếu có lỗi
        """
        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/holes/batch-update"
        return self._make_request('PATCH', endpoint, json={"holes": holes})
    
    def send_drilling_data(self, project_id: int, hole_id: Union[int, str], velocity_ms: float, depth_m: float, timestamp: Optional[datetime] = None) -> bool:
        """
        Gửi dữ liệu tốc độ khoan (legacy) bằng cách cập nhật depth qua PUT.
        Khuyến nghị sử dụng post_drilling_speed cho endpoint drilling-speed mới.
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
        """
        result = self.update_hole_drilling_speed(
            project_id=project_id,
            hole_id=hole_id,
            velocity_ms=velocity_ms,
            depth=depth_m
        )
        return result is not None and result.get('success', False)

    def post_drilling_speed(
        self,
        project_id: int,
        hole_id: Union[int, str],
        speed: float,
        depth: float,
        timestamp: Optional[datetime] = None,
        sensor_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gửi dữ liệu khoan lên endpoint:
        POST /api/projects/{projectId}/holes/{holeId}/drilling-speed
        
        Ghi chú:
        - `base_url` đã bao gồm `/api`, vì vậy endpoint phải bắt đầu bằng `/`
        - Ví dụ: base_url = http://localhost:3000/api
          → URL đầy đủ: http://localhost:3000/api/projects/{projectId}/holes/{holeId}/drilling-speed
        
        Args:
            project_id: ID của dự án
            hole_id: Hole identifier trong URL (thường là hole_id string như "HK_01")
            speed: Tốc độ khoan (đơn vị do server quy ước, ở đây dùng giá trị float hiện tại)
            depth: Chiều sâu hiện tại (meters)
            timestamp: Thời gian đo (UTC). Nếu None sẽ dùng thời gian hiện tại.
            sensor_id: ID cảm biến (optional)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Format timestamp thành ISO8601 với Z suffix (UTC)
        # Đảm bảo luôn có format: "2025-12-03T10:30:00Z"
        if timestamp.tzinfo is None:
            # Nếu không có timezone, coi như UTC và format trực tiếp
            ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        else:
            # Nếu có timezone, convert sang UTC và format
            utc_timestamp = timestamp.astimezone(timezone.utc)
            ts_str = utc_timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        # base_url đã bao gồm `/api`, endpoint luôn phải bắt đầu bằng `/`
        endpoint = f"/projects/{project_id}/holes/{hole_id}/drilling-speed"
        payload: Dict[str, Any] = {
            "speed": float(speed),
            "depth": float(depth),
            "timestamp": ts_str,
        }
        if sensor_id:
            payload["sensor_id"] = sensor_id

        return self._make_request("POST", endpoint, json=payload)
    
    def get_hole_gps(self, project_id: int, hole_id: Union[int, str]) -> Optional[Dict[str, float]]:
        """
        Lấy tọa độ GPS của một lỗ khoan
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            
        Returns:
            Dictionary chứa GPS coordinates: {"lon": float, "lat": float, "elevation": float}
            hoặc None nếu có lỗi hoặc không có GPS data
        """
        hole_data = self.get_hole(project_id, hole_id)
        if not hole_data or not hole_data.get('success'):
            return None
        
        hole = hole_data.get('hole', {})
        gps_data = {
            'lon': hole.get('gps_lon'),
            'lat': hole.get('gps_lat'),
            'elevation': hole.get('gps_elevation')
        }
        
        # Kiểm tra xem có GPS data không
        if gps_data['lon'] is None or gps_data['lat'] is None:
            return None
        
        return gps_data
    
    def test_connection(self) -> bool:
        """
        Kiểm tra kết nối với API server
        
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        try:
            # Thử GET request đến base URL (có thể trả về 404 nhưng OK, nghĩa là server đang chạy)
            print(f"\nDEBUG test_connection():")
            print(f"  Testing URL: {self.base_url}")
            
            response = self.session.get(
                f"{self.base_url}",
                timeout=5,
                verify=True  # Verify SSL certificate
            )
            
            print(f"  Response status: {response.status_code}")
            
            # 200, 404, 403 đều OK - nghĩa là server đang chạy
            # 404 = endpoint không có nhưng server sống
            # 403 = forbidden nhưng server sống
            is_ok = response.status_code in [200, 404, 403]
            print(f"  Connection OK: {is_ok}")
            return is_ok
            
        except requests.exceptions.SSLError as e:
            print(f"  SSL Error: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"  Connection Error: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"  Timeout Error: {e}")
            return False
        except Exception as e:
            print(f"  Unexpected Error: {e}")
            # Trả về False thay vì True để an toàn
            return False
    
    def update_hole_with_drilling_speed(self, project_id: int, hole_id: Union[int, str], velocity_ms: float, depth_m: float) -> Optional[Dict]:
        """
        Cập nhật lỗ khoan với dữ liệu tốc độ khoan và chiều sâu
        
        Args:
            project_id: ID của dự án
            hole_id: ID của lỗ khoan (database ID hoặc hole_id string như "LK1")
            velocity_ms: Tốc độ khoan (m/s)
            depth_m: Chiều sâu (meters)
            
        Returns:
            Dictionary chứa thông tin hole đã cập nhật hoặc None nếu có lỗi
        """
        # Cập nhật depth (API hỗ trợ field này)
        # Note: API hiện tại không có field riêng cho velocity, có thể mở rộng trong tương lai
        return self.update_hole(project_id, hole_id, {"depth": depth_m})

