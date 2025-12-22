"""
Hole Finder - Thuật toán tìm hố khoan gần nhất dựa trên tọa độ GPS

Module này cung cấp các hàm để:
- Tính khoảng cách giữa 2 điểm GPS (Haversine formula)
- Tìm hố khoan gần nhất từ vị trí hiện tại
- Sắp xếp danh sách holes theo khoảng cách
"""
import math
from typing import List, Dict, Optional, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa 2 điểm GPS sử dụng công thức Haversine
    
    Args:
        lat1, lon1: Tọa độ điểm 1 (độ)
        lat2, lon2: Tọa độ điểm 2 (độ)
    
    Returns:
        Khoảng cách tính bằng mét
    
    Formula:
        a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
        c = 2 ⋅ atan2(√a, √(1−a))
        d = R ⋅ c
        
    Trong đó:
        φ = latitude (rad)
        λ = longitude (rad)
        R = bán kính trái đất (6371 km)
    """
    # Bán kính trái đất (km)
    R = 6371.0
    
    # Chuyển đổi từ độ sang radian
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Tính delta
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Công thức Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Khoảng cách (km)
    distance_km = R * c
    
    # Chuyển sang mét
    distance_m = distance_km * 1000
    
    return distance_m


def calculate_distance_with_elevation(
    lat1: float, lon1: float, elev1: Optional[float],
    lat2: float, lon2: Optional[float], elev2: Optional[float]
) -> float:
    """
    Tính khoảng cách 3D (có tính cả độ cao) giữa 2 điểm
    
    Args:
        lat1, lon1, elev1: Tọa độ và độ cao điểm 1
        lat2, lon2, elev2: Tọa độ và độ cao điểm 2
    
    Returns:
        Khoảng cách 3D tính bằng mét
    """
    # Khoảng cách ngang (horizontal)
    horizontal_distance = haversine_distance(lat1, lon1, lat2, lon2)
    
    # Nếu không có thông tin độ cao, chỉ trả về khoảng cách ngang
    if elev1 is None or elev2 is None:
        return horizontal_distance
    
    # Khoảng cách dọc (vertical)
    vertical_distance = abs(elev1 - elev2)
    
    # Khoảng cách 3D (Pythagorean theorem)
    distance_3d = math.sqrt(horizontal_distance**2 + vertical_distance**2)
    
    return distance_3d


def find_nearest_hole(
    current_lat: float,
    current_lon: float,
    current_elev: Optional[float],
    holes: List[Dict],
    max_distance: Optional[float] = None,
    use_3d: bool = True
) -> Optional[Dict]:
    """
    Tìm hố khoan gần nhất từ vị trí hiện tại
    
    Args:
        current_lat: Vĩ độ hiện tại
        current_lon: Kinh độ hiện tại
        current_elev: Độ cao hiện tại (optional)
        holes: Danh sách hố khoan (mỗi hole có 'gps_lat', 'gps_lon', 'gps_elevation')
        max_distance: Khoảng cách tối đa (mét). Nếu None, không giới hạn
        use_3d: Có tính khoảng cách 3D không (bao gồm độ cao)
    
    Returns:
        Dictionary của hole gần nhất, hoặc None nếu không tìm thấy
        Dictionary có thêm key '_distance' (khoảng cách tính bằng mét)
    """
    if not holes:
        return None
    
    nearest_hole = None
    min_distance = float('inf')
    
    for hole in holes:
        # Lấy tọa độ GPS của hole
        hole_lat = hole.get('gps_lat')
        hole_lon = hole.get('gps_lon')
        hole_elev = hole.get('gps_elevation')
        
        # Bỏ qua holes không có tọa độ GPS
        if hole_lat is None or hole_lon is None:
            continue
        
        # Tính khoảng cách
        if use_3d and current_elev is not None and hole_elev is not None:
            distance = calculate_distance_with_elevation(
                current_lat, current_lon, current_elev,
                hole_lat, hole_lon, hole_elev
            )
        else:
            distance = haversine_distance(current_lat, current_lon, hole_lat, hole_lon)
        
        # Kiểm tra max_distance
        if max_distance is not None and distance > max_distance:
            continue
        
        # Cập nhật nearest hole
        if distance < min_distance:
            min_distance = distance
            nearest_hole = hole.copy()
            nearest_hole['_distance'] = distance
    
    return nearest_hole


def get_holes_sorted_by_distance(
    current_lat: float,
    current_lon: float,
    current_elev: Optional[float],
    holes: List[Dict],
    max_distance: Optional[float] = None,
    use_3d: bool = True,
    limit: Optional[int] = None
) -> List[Dict]:
    """
    Lấy danh sách hố khoan được sắp xếp theo khoảng cách (gần nhất trước)
    
    Args:
        current_lat: Vĩ độ hiện tại
        current_lon: Kinh độ hiện tại
        current_elev: Độ cao hiện tại (optional)
        holes: Danh sách hố khoan
        max_distance: Khoảng cách tối đa (mét). Nếu None, không giới hạn
        use_3d: Có tính khoảng cách 3D không
        limit: Giới hạn số lượng kết quả. Nếu None, trả về tất cả
    
    Returns:
        List các hole được sắp xếp theo khoảng cách
        Mỗi hole có thêm key '_distance' (mét)
    """
    holes_with_distance = []
    
    for hole in holes:
        hole_lat = hole.get('gps_lat')
        hole_lon = hole.get('gps_lon')
        hole_elev = hole.get('gps_elevation')
        
        # Bỏ qua holes không có tọa độ GPS
        if hole_lat is None or hole_lon is None:
            continue
        
        # Tính khoảng cách
        if use_3d and current_elev is not None and hole_elev is not None:
            distance = calculate_distance_with_elevation(
                current_lat, current_lon, current_elev,
                hole_lat, hole_lon, hole_elev
            )
        else:
            distance = haversine_distance(current_lat, current_lon, hole_lat, hole_lon)
        
        # Kiểm tra max_distance
        if max_distance is not None and distance > max_distance:
            continue
        
        # Thêm vào list
        hole_copy = hole.copy()
        hole_copy['_distance'] = distance
        holes_with_distance.append(hole_copy)
    
    # Sắp xếp theo khoảng cách
    holes_with_distance.sort(key=lambda h: h['_distance'])
    
    # Giới hạn số lượng nếu có
    if limit is not None:
        holes_with_distance = holes_with_distance[:limit]
    
    return holes_with_distance


def format_distance(distance_m: float) -> str:
    """
    Format khoảng cách thành string dễ đọc
    
    Args:
        distance_m: Khoảng cách tính bằng mét
    
    Returns:
        String format (VD: "15.3m", "1.2km")
    """
    if distance_m < 1000:
        return f"{distance_m:.1f}m"
    else:
        distance_km = distance_m / 1000
        return f"{distance_km:.2f}km"


# Test functions
if __name__ == "__main__":
    # Test haversine distance
    # Hanoi Opera House: 21.0285, 105.8542
    # Hoan Kiem Lake: 21.0288, 105.8525
    dist = haversine_distance(21.0285, 105.8542, 21.0288, 105.8525)
    print(f"Distance between Hanoi Opera House and Hoan Kiem Lake: {format_distance(dist)}")
    
    # Test find nearest hole
    current_pos = {
        'lat': 21.0286,
        'lon': 105.8540,
        'elev': 10.0
    }
    
    test_holes = [
        {'name': 'HK1', 'gps_lat': 21.0285, 'gps_lon': 105.8542, 'gps_elevation': 12.0},
        {'name': 'HK2', 'gps_lat': 21.0288, 'gps_lon': 105.8525, 'gps_elevation': 8.0},
        {'name': 'HK3', 'gps_lat': 21.0290, 'gps_lon': 105.8530, 'gps_elevation': 15.0},
    ]
    
    nearest = find_nearest_hole(
        current_pos['lat'],
        current_pos['lon'],
        current_pos['elev'],
        test_holes
    )
    
    if nearest:
        print(f"\nNearest hole: {nearest['name']}")
        print(f"Distance: {format_distance(nearest['_distance'])}")
    
    # Test sorted list
    sorted_holes = get_holes_sorted_by_distance(
        current_pos['lat'],
        current_pos['lon'],
        current_pos['elev'],
        test_holes
    )
    
    print("\nAll holes sorted by distance:")
    for hole in sorted_holes:
        print(f"  {hole['name']}: {format_distance(hole['_distance'])}")

