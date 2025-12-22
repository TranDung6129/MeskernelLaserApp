# Hướng dẫn tích hợp API Holes

## Tổng quan

**Hệ thống này là ứng dụng desktop (chạy trên máy tính)** được viết bằng PyQt6, giao tiếp với **Holes API trên website** (`https://nomin.wintech.io.vn/api`).

Hệ thống đã được tích hợp với Holes API để:
1. **Lấy tọa độ GPS** từ Website khi chọn hố khoan
2. **Gửi dữ liệu tốc độ khoan** lên Website trong quá trình recording

## Cấu hình

### 1. Cấu hình Project

Để sử dụng API, cần thêm thông tin API vào file `project_info.json`. 

**Cách 1: Tự động (khuyến nghị)**
- Khi tạo dự án mới, có thể nhập `api_project_id` trong hộp thoại tạo dự án
- Hệ thống sẽ tự động lưu vào `project_info.json`

**Cách 2: Thủ công**
- Mở file `project_info.json` trong thư mục dự án
- Thêm các trường sau:

```json
{
  "name": "Tên dự án",
  "description": "Mô tả dự án",
  "api_base_url": "https://nomin.wintech.io.vn/api",
  "api_project_id": 21,
  ...
}
```

**Các trường cần thiết:**
- `api_base_url`: Base URL của API (mặc định: `https://nomin.wintech.io.vn/api`)
- `api_project_id`: ID của dự án trong API (số nguyên) - **Bạn cần biết ID này từ website**

**Lưu ý:** Hiện tại API không có endpoint để tự động lấy danh sách projects, nên bạn cần biết `api_project_id` từ website và nhập thủ công.

### 2. Mapping Hole với API

Khi chọn một hố khoan, hệ thống sẽ tự động:
1. Tìm hố khoan trong API bằng `hole_id` (tên hố khoan)
2. Lấy tọa độ GPS từ API
3. Lưu `api_hole_id` vào `hole_info.json`

File `hole_info.json` sẽ có dạng:

```json
{
  "name": "HK01",
  "location": "Khu vực A",
  "gps_lon": 107.149251,
  "gps_lat": 20.995293,
  "gps_elevation": 125.5,
  "api_hole_id": 1,
  ...
}
```

## Sử dụng

### Bước 1: Tạo/Cấu hình Project với API

**Khi tạo dự án mới:**
1. Mở hộp thoại "Quản lý dự án"
2. Nhập tên dự án và mô tả
3. Trong phần "Cấu hình API":
   - **API Base URL**: Mặc định là `https://nomin.wintech.io.vn/api` 
   - **API Project ID**: Nhập ID của dự án trên website (ví dụ: 21)
4. Nhấn "Tạo dự án mới"
5. Hệ thống sẽ tự động lưu cấu hình API vào `project_info.json`

**Lưu ý:** Bạn cần biết `api_project_id` từ website. Hiện tại API không có endpoint để tự động lấy danh sách projects, nên bạn phải nhập thủ công.

**Đối với dự án đã tạo:**
- Mở file `project_info.json` trong thư mục dự án
- Thêm các trường `api_base_url` và `api_project_id`

### Bước 2: Tải danh sách hố khoan từ API

**Tự động khi mở hộp thoại:**
- Khi mở hộp thoại "Quản lý hố khoan", hệ thống sẽ tự động tải danh sách hố khoan từ API (nếu có cấu hình API Project ID)
- Tất cả hố khoan từ API sẽ được hiển thị trong danh sách

**Thủ công:**
1. Mở hộp thoại "Quản lý hố khoan"
2. Nhấn nút "Tải từ API"
3. Hệ thống sẽ:
   - Lấy tất cả hố khoan từ API
   - Tự động tạo local hole cho các hố khoan mới (chưa có trên máy)
   - Đồng bộ thông tin cho các hố khoan đã có (GPS, độ sâu, design, etc.)
   - Hiển thị trong danh sách với thông tin đầy đủ

**Thông tin hiển thị từ API:**
- Tên hố khoan (hole_id)
- Design name
- Tọa độ GPS (nếu có)
- Độ sâu (nếu có)
- Nhãn "[Từ API]" cho hố khoan mới được tạo
- Nhãn "[Đã đồng bộ]" cho hố khoan đã có và được cập nhật

**Lưu ý:**
- Hố khoan từ API sẽ tự động được tạo thành local hole trên máy tính
- Thông tin từ API (GPS, độ sâu, design, etc.) sẽ được lưu vào `hole_info.json`
- Khi chọn hố khoan, hệ thống sẽ tự động đồng bộ lại thông tin mới nhất từ API

### Gửi dữ liệu tốc độ khoan

1. Đảm bảo dự án và hố khoan đã được cấu hình với API
2. Bắt đầu recording
3. Hệ thống sẽ tự động:
   - Khởi tạo `DrillingDataService`
   - Gửi dữ liệu tốc độ khoan và chiều sâu lên API mỗi 2 giây
4. Khi dừng recording, service sẽ tự động dừng và gửi dữ liệu còn lại

## API Endpoints được sử dụng

### 1. Lấy tất cả holes trong dự án
```
GET https://nomin.wintech.io.vn/projects/:projectId/holes
```
**Lưu ý:** Endpoint này không có `/api` prefix.

### 2. Lấy thông tin chi tiết hố khoan
```
GET https://nomin.wintech.io.vn/api/projects/:projectId/holes/:holeId
```
**Lưu ý:** `holeId` có thể là database ID (số) hoặc hole_id string (ví dụ: "LK1").

### 3. Cập nhật hố khoan với dữ liệu khoan
```
PUT https://nomin.wintech.io.vn/api/projects/:projectId/holes/:holeId
Body: {
  "depth": 14.0  // Chiều sâu (meters)
}
```

## Tính năng tự động cập nhật theo vị trí GNSS

Hệ thống hỗ trợ tự động cập nhật tốc độ khoan dựa trên vị trí GNSS RTK:

1. **Nhận tọa độ từ MQTT**: Hệ thống subscribe vào MQTT topic (ví dụ: `device/860549070085423/upload`) để nhận tọa độ từ GNSS RTK
2. **Tìm hố khoan gần nhất**: Tính khoảng cách từ vị trí hiện tại đến tất cả các hố khoan trong dự án
3. **Tự động cập nhật**: Nếu tìm thấy hố khoan gần nhất (trong phạm vi cho phép), tự động cập nhật tốc độ khoan và chiều sâu cho hố đó

### Cấu hình MQTT cho GNSS

Thêm vào `project_info.json`:

```json
{
  "api_base_url": "https://nomin.wintech.io.vn/api",
  "api_project_id": 19,
  "mqtt_broker_host": "192.168.1.100",
  "mqtt_broker_port": 1883,
  "mqtt_topic": "device/+/upload",
  "gnss_max_distance": 10.0
}
```

**Các trường:**
- `mqtt_broker_host`: IP hoặc hostname của MQTT broker
- `mqtt_broker_port`: Port của MQTT broker (mặc định: 1883)
- `mqtt_topic`: MQTT topic để subscribe (có thể dùng wildcard như `device/+/upload`)
- `gnss_max_distance`: Khoảng cách tối đa để coi là "gần" (meters, mặc định: 10.0)

**Format dữ liệu MQTT:**
Hệ thống hỗ trợ các format sau:
```json
{
  "lat": 20.995293,
  "lon": 107.149251,
  "elevation": 125.5
}
```
hoặc
```json
{
  "latitude": 20.995293,
  "longitude": 107.149251,
  "alt": 125.5
}
```
hoặc
```json
{
  "gps_lat": 20.995293,
  "gps_lon": 107.149251,
  "gps_elevation": 125.5
}
```

**Lưu ý:** API hiện tại không có field riêng cho `velocity` (tốc độ khoan). 
Hệ thống sẽ gửi `depth` (chiều sâu) lên API. 
Nếu API được mở rộng để hỗ trợ field `drilling_speed` hoặc `velocity` trong tương lai, 
có thể cập nhật method `update_hole_with_drilling_speed` trong `holes_api.py`.

## Xử lý lỗi

- Nếu API không khả dụng, hệ thống sẽ in warning nhưng không crash
- Nếu không tìm thấy hố khoan trong API, sẽ không hiển thị lỗi (fail silently)
- Nếu không có `api_project_id` hoặc `api_hole_id`, service sẽ không khởi động

## Kiểm tra kết nối

Để kiểm tra kết nối API, có thể sử dụng:

```python
from modules.api.holes_api import HolesAPIClient

client = HolesAPIClient(base_url="http://localhost:3000/api")
if client.test_connection():
    print("API connection OK")
else:
    print("API connection failed")
```

## Troubleshooting

1. **Không lấy được GPS:**
   - Kiểm tra `api_project_id` trong `project_info.json`
   - Kiểm tra tên hố khoan có khớp với `hole_id` trong API không
   - Kiểm tra API server có đang chạy không

2. **Không gửi được dữ liệu:**
   - Kiểm tra `api_hole_id` trong `hole_info.json`
   - Kiểm tra API server có đang chạy không
   - Xem console log để biết lỗi chi tiết

3. **Import error:**
   - Đảm bảo đã cài đặt `requests`: `pip install requests`
   - Kiểm tra module path trong `sys.path`

