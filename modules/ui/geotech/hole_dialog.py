"""
Hole Dialog - Hộp thoại quản lý hố khoan trong dự án

QUAN TRỌNG: 
- BẮT BUỘC phải cấu hình API (api_base_url và api_project_id) trong project_info.json
- BẮT BUỘC phải tải danh sách hố khoan từ API trước
- KHÔNG CHO PHÉP auto-create placeholder (tạo tự động khi chưa chọn)
- CHO PHÉP người dùng tạo hole mới thủ công

Luồng hoạt động:
1. Kiểm tra cấu hình API khi khởi tạo
2. Test kết nối đến API server
3. Tải danh sách hố khoan từ API (get_all_holes)
4. Người dùng có thể tạo hole mới hoặc chọn hole từ API
5. Local hole directories được tạo để lưu API data và session data
"""
from typing import Optional, Dict, List, Callable
import sys
import os

from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QFormLayout, QDialogButtonBox, QAbstractItemView, QDateTimeEdit, QWidget, QFrame
)

# Thêm path để import API module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from .project_manager import ProjectManager
try:
    from modules.api.holes_api import HolesAPIClient
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    HolesAPIClient = None

try:
    from modules.utils.hole_finder import find_nearest_hole, format_distance
    HOLE_FINDER_AVAILABLE = True
except ImportError:
    HOLE_FINDER_AVAILABLE = False
    find_nearest_hole = None
    format_distance = None


class HoleDialog(QDialog):
    """
    Hộp thoại quản lý hố khoan trong dự án
    
    CHÍNH SÁCH:
    - YÊU CẦU cấu hình API bắt buộc
    - YÊU CẦU tải danh sách từ API trước
    - CHO PHÉP người dùng tạo hole mới thủ công
    - KHÔNG CHO PHÉP auto-create placeholder
    """
    hole_selected = pyqtSignal(dict)  # Khi người dùng chọn một hố khoan
    
    def __init__(self, project_manager: ProjectManager, parent=None, gnss_service=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_hole = None
        self.gnss_service = gnss_service  # GNSS service để lấy tọa độ hiện tại
        
        # BẮT BUỘC: Khởi tạo API client
        self.api_client = None
        
        if API_AVAILABLE:
            # Lấy API config từ project info
            api_base_url = self._get_api_base_url()
            if api_base_url:
                self.api_client = HolesAPIClient(base_url=api_base_url)
        
        self.setWindowTitle("Quản lý hố khoan")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
    
    def _get_api_base_url(self) -> Optional[str]:
        """Lấy API base URL từ project info"""
        if not self.project_manager.current_project:
            return None
        
        project_info = self.project_manager.current_project
        # Có thể lưu trong project_info.json hoặc dùng default
        api_base_url = project_info.get('api_base_url', 'http://localhost:3000/api')
        return api_base_url
    
    def _get_api_project_id(self) -> Optional[int]:
        """Lấy API project ID từ project info"""
        if not self.project_manager.current_project:
            return None
        
        project_info = self.project_manager.current_project
        api_project_id = project_info.get('api_project_id')
        if api_project_id:
            try:
                return int(api_project_id)
            except (ValueError, TypeError):
                return None
        return None
    
    def _get_current_location(self):
        """Lấy tọa độ GPS hiện tại từ GNSS service"""
        if not self.gnss_service:
            QMessageBox.warning(
                self,
                "Không có GNSS",
                "Không thể lấy vị trí hiện tại.\n\n"
                "GNSS service chưa được khởi tạo hoặc chưa kết nối."
            )
            return
        
        try:
            # Lấy dữ liệu GNSS mới nhất
            gnss_data = self.gnss_service.get_latest_data()
            
            if not gnss_data:
                QMessageBox.warning(
                    self,
                    "Không có dữ liệu",
                    "Chưa nhận được dữ liệu GNSS.\n\n"
                    "Vui lòng kiểm tra:\n"
                    "• Kết nối MQTT\n"
                    "• GNSS device có đang hoạt động không"
                )
                return
            
            # Lấy tọa độ
            lat = gnss_data.get('latitude') or gnss_data.get('lat')
            lon = gnss_data.get('longitude') or gnss_data.get('lon')
            elev = gnss_data.get('elevation') or gnss_data.get('altitude')
            
            if lat is None or lon is None:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    "Dữ liệu GNSS không có tọa độ hợp lệ."
                )
                return
            
            # Điền vào form
            self.edt_gps_lat.setText(f"{lat:.8f}")
            self.edt_gps_lon.setText(f"{lon:.8f}")
            if elev is not None:
                self.edt_gps_elev.setText(f"{elev:.2f}")
            
            # Hiển thị GPS fields
            self.gps_group.setVisible(True)
            
            QMessageBox.information(
                self,
                "Đã lấy vị trí",
                f"✅ Đã lấy tọa độ GPS hiện tại:\n\n"
                f"Vĩ độ: {lat:.8f}\n"
                f"Kinh độ: {lon:.8f}\n"
                f"Độ cao: {elev:.2f}m" if elev else f"Độ cao: N/A"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể lấy vị trí hiện tại:\n\n{str(e)}"
            )
    
    def _find_nearest_hole(self):
        """Tìm và chọn hố khoan gần nhất với vị trí hiện tại"""
        if not HOLE_FINDER_AVAILABLE:
            QMessageBox.warning(
                self,
                "Chức năng không khả dụng",
                "Module hole_finder không khả dụng."
            )
            return
        
        if not self.gnss_service:
            QMessageBox.warning(
                self,
                "Không có GNSS",
                "Cần GNSS service để lấy vị trí hiện tại."
            )
            return
        
        try:
            # Lấy vị trí hiện tại
            gnss_data = self.gnss_service.get_latest_data()
            
            if not gnss_data:
                QMessageBox.warning(
                    self,
                    "Không có dữ liệu GNSS",
                    "Chưa nhận được dữ liệu GNSS.\n\n"
                    "Vui lòng kiểm tra kết nối MQTT và GNSS device."
                )
                return
            
            current_lat = gnss_data.get('latitude') or gnss_data.get('lat')
            current_lon = gnss_data.get('longitude') or gnss_data.get('lon')
            current_elev = gnss_data.get('elevation') or gnss_data.get('altitude')
            
            if current_lat is None or current_lon is None:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    "Dữ liệu GNSS không có tọa độ hợp lệ."
                )
                return
            
            # Lấy danh sách holes có GPS
            holes_with_gps = []
            for i in range(self.hole_list.count()):
                item = self.hole_list.item(i)
                hole = item.data(Qt.ItemDataRole.UserRole)
                if hole and hole.get('gps_lat') and hole.get('gps_lon'):
                    holes_with_gps.append(hole)
            
            if not holes_with_gps:
                QMessageBox.information(
                    self,
                    "Không có dữ liệu",
                    "Không có hố khoan nào có tọa độ GPS.\n\n"
                    "Vui lòng đồng bộ từ API để lấy tọa độ GPS."
                )
                return
            
            # Tìm hole gần nhất
            nearest = find_nearest_hole(
                current_lat,
                current_lon,
                current_elev,
                holes_with_gps,
                max_distance=1000,  # 1km
                use_3d=True
            )
            
            if not nearest:
                QMessageBox.information(
                    self,
                    "Không tìm thấy",
                    "Không tìm thấy hố khoan nào trong bán kính 1km.\n\n"
                    "Vị trí hiện tại:\n"
                    f"• Vĩ độ: {current_lat:.6f}\n"
                    f"• Kinh độ: {current_lon:.6f}"
                )
                return
            
            # Chọn hole trong list
            hole_name = nearest.get('name')
            distance = nearest.get('_distance', 0)
            
            for i in range(self.hole_list.count()):
                item = self.hole_list.item(i)
                hole = item.data(Qt.ItemDataRole.UserRole)
                if hole and hole.get('name') == hole_name:
                    self.hole_list.setCurrentRow(i)
                    self.hole_list.scrollToItem(item)
                    break
            
            # Hiển thị thông báo
            QMessageBox.information(
                self,
                "Đã tìm thấy",
                f"🎯 Hố khoan gần nhất: {hole_name}\n\n"
                f"Khoảng cách: {format_distance(distance)}\n\n"
                f"Vị trí hole:\n"
                f"• Vĩ độ: {nearest.get('gps_lat'):.6f}\n"
                f"• Kinh độ: {nearest.get('gps_lon'):.6f}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể tìm hố khoan gần nhất:\n\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _on_sync_button_clicked(self):
        """Xử lý khi user bấm nút Đồng bộ từ API"""
        # Clear list và tải lại từ API
        self.hole_list.clear()
        self._load_holes_from_api(silent=False)
        # Sau đó tải local holes (những holes không có trên API)
        self._load_holes()
        # Cập nhật label
        self._update_sync_label()
    
    def _get_last_sync_info(self) -> str:
        """Lấy thông tin đồng bộ lần cuối từ project_info.json"""
        if not self.project_manager.current_project:
            return ""
        
        project_info = self.project_manager.current_project
        last_sync = project_info.get('last_api_sync')
        
        if not last_sync:
            return ""
        
        try:
            from datetime import datetime
            sync_time = datetime.fromisoformat(last_sync)
            now = datetime.now()
            delta = now - sync_time
            
            if delta.days > 0:
                return f"{delta.days} ngày trước"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} giờ trước"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes} phút trước"
            else:
                return "Vừa xong"
        except:
            return last_sync
    
    def _update_sync_label(self):
        """Cập nhật label hiển thị thời gian sync"""
        last_sync = self._get_last_sync_info()
        if last_sync:
            self.lbl_last_sync.setText(f"Đồng bộ: {last_sync}")
        else:
            self.lbl_last_sync.setText("Chưa đồng bộ")
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin dự án hiện tại
        self.lbl_project = QLabel("Dự án: " + (self.project_manager.current_project.get('name', 'Chưa chọn dự án') 
                                             if self.project_manager.current_project else 'Chưa chọn dự án'))
        layout.addWidget(self.lbl_project)
        
        # CẢNH BÁO: Bắt buộc cấu hình API
        if not API_AVAILABLE or not self.api_client:
            warning_label = QLabel("⚠️ CẢNH BÁO: Chưa cấu hình API. Vui lòng cấu hình API trong Quản lý dự án để tải danh sách hố khoan.")
            warning_label.setStyleSheet("QLabel { color: red; font-weight: bold; padding: 10px; background-color: #ffeeee; border: 2px solid red; border-radius: 5px; }")
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)
        
        # Phần tạo hố khoan mới
        new_hole_group = self._create_new_hole_group()
        layout.addWidget(new_hole_group)
        
        # Danh sách hố khoan với nút tải từ API và thông tin sync
        holes_header = QHBoxLayout()
        holes_header.addWidget(QLabel("Danh sách hố khoan:"))
        holes_header.addStretch()
        
        # Label hiển thị thời gian sync lần cuối
        self.lbl_last_sync = QLabel()
        self._update_sync_label()
        self.lbl_last_sync.setStyleSheet("QLabel { color: gray; font-size: 11px; }")
        holes_header.addWidget(self.lbl_last_sync)
        
        # Nút tải từ API
        self.btn_load_from_api = QPushButton("🔄 Đồng bộ từ API")
        self.btn_load_from_api.setEnabled(API_AVAILABLE and self.api_client is not None)
        self.btn_load_from_api.setToolTip("Tải danh sách hố khoan mới nhất từ server")
        self.btn_load_from_api.clicked.connect(self._on_sync_button_clicked)
        holes_header.addWidget(self.btn_load_from_api)
        
        layout.addLayout(holes_header)
        
        self.hole_list = QListWidget()
        self.hole_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.hole_list.itemDoubleClicked.connect(self._on_hole_selected)
        layout.addWidget(self.hole_list)
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        
        self.btn_select = button_box.addButton("Chọn", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_select.setEnabled(False)
        self.btn_settings = button_box.addButton("Cấu hình", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_settings.setEnabled(False)
        self.btn_delete = button_box.addButton("Xóa", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_delete.setEnabled(False)
        button_box.addButton("Đóng", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.btn_settings.clicked.connect(self._configure_hole)
        self.btn_delete.clicked.connect(self._delete_selected_holes)
        
        layout.addWidget(button_box)
        
        # Kết nối sự kiện chọn hố khoan
        self.hole_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # LUỒNG MỚI: Luôn tải LOCAL trước (nhanh), user bấm nút để tải từ API
        # Lý do: Không nên auto-reload mỗi lần mở → tốn bandwidth và thời gian
        
        # 1. Tải holes từ local (nhanh, luôn có)
        self._load_holes()
        
        # 2. Kiểm tra cấu hình API và hiển thị thông tin sync
        if not API_AVAILABLE or not self.api_client:
            # Không có API config
            print("WARNING: Chưa cấu hình API - chỉ làm việc offline")
        elif not self._get_api_project_id():
            # Không có Project ID
            print("WARNING: Chưa cấu hình API Project ID")
        else:
            # Có API config → Hiển thị thông tin sync lần cuối
            last_sync_info = self._get_last_sync_info()
            if last_sync_info:
                print(f"INFO: Đồng bộ lần cuối: {last_sync_info}")
            else:
                print("INFO: Chưa đồng bộ với API lần nào. Nhấn 'Tải từ API' để đồng bộ.")
    
    def _create_new_hole_group(self) -> QWidget:
        """Tạo nhóm tạo hố khoan mới (CHO PHÉP người dùng tạo thủ công)"""
        group = QWidget()
        layout = QVBoxLayout(group)
        
        # Tiêu đề
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Tạo hố khoan mới:"))
        title_layout.addStretch()
        
        # Nút lấy vị trí hiện tại
        btn_get_location = QPushButton("📍 Lấy vị trí hiện tại")
        btn_get_location.setToolTip("Lấy tọa độ GPS từ GNSS")
        btn_get_location.clicked.connect(self._get_current_location)
        btn_get_location.setEnabled(self.gnss_service is not None)
        title_layout.addWidget(btn_get_location)
        
        layout.addLayout(title_layout)
        
        # Form nhập thông tin
        form_layout = QFormLayout()
        
        self.edt_hole_name = QLineEdit()
        self.edt_hole_name.setPlaceholderText("VD: HK001, LK01, ...")
        form_layout.addRow("Tên hố khoan*:", self.edt_hole_name)
        
        self.edt_location = QLineEdit()
        self.edt_location.setPlaceholderText("VD: Khu vực A, Tầng 1, ...")
        form_layout.addRow("Vị trí:", self.edt_location)
        
        # GPS fields (ẩn ban đầu, hiện khi có tọa độ)
        gps_group = QWidget()
        gps_layout = QFormLayout(gps_group)
        
        self.edt_gps_lat = QLineEdit()
        self.edt_gps_lat.setPlaceholderText("VD: 21.0286")
        gps_layout.addRow("GPS Vĩ độ:", self.edt_gps_lat)
        
        self.edt_gps_lon = QLineEdit()
        self.edt_gps_lon.setPlaceholderText("VD: 105.8542")
        gps_layout.addRow("GPS Kinh độ:", self.edt_gps_lon)
        
        self.edt_gps_elev = QLineEdit()
        self.edt_gps_elev.setPlaceholderText("VD: 10.5")
        gps_layout.addRow("GPS Độ cao (m):", self.edt_gps_elev)
        
        gps_group.setVisible(False)  # Ẩn ban đầu
        self.gps_group = gps_group
        
        self.edt_notes = QLineEdit()
        self.edt_notes.setPlaceholderText("Ghi chú thêm (nếu có)")
        form_layout.addRow("Ghi chú:", self.edt_notes)
        
        layout.addLayout(form_layout)
        layout.addWidget(gps_group)
        
        # Nút tạo hố khoan
        btn_create = QPushButton("Tạo hố khoan mới")
        btn_create.clicked.connect(self._create_hole)
        layout.addWidget(btn_create)
        
        # Đường kẻ ngăn cách
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        return group
    
    def _load_holes(self):
        """
        Tải danh sách hố khoan từ local (bao gồm cả holes do người dùng tạo)
        
        NOTE: Chỉ thêm holes chưa có trong danh sách (để không duplicate với API holes)
        """
        if not self.project_manager.current_project:
            return
        
        # Chỉ thêm local holes chưa có trong danh sách
        existing_names = set()
        for i in range(self.hole_list.count()):
            item = self.hole_list.item(i)
            hole = item.data(Qt.ItemDataRole.UserRole)
            if hole:
                existing_names.add(hole.get('name'))
        
        holes = self.project_manager.list_holes()
        
        print(f"\nDEBUG _load_holes():")
        print(f"  - Total local holes: {len(holes)}")
        print(f"  - Already in list: {len(existing_names)}")
        print(f"  - Will add: {len([h for h in holes if h.get('name') not in existing_names])}")
        
        for hole in holes:
            hole_name = hole.get('name', '')
            if hole_name in existing_names:
                continue  # Đã có trong danh sách
            
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, hole)
            
            # Hiển thị thông tin hố khoan
            name = hole.get('name', 'Không có tên')
            location = hole.get('location', '')
            created = hole.get('created_at', '')
            data_files = hole.get('data_files', [])
            
            # Tạo text đơn giản
            text = name
            
            # Thêm thông tin bổ sung
            info_parts = []
            if location:
                info_parts.append(f"Vị trí: {location}")
            
            if data_files:
                info_parts.append(f"Đã ghi {len(data_files)} lần")
            
            if created:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    info_parts.append(f"Tạo lúc: {dt.strftime('%d/%m/%Y %H:%M')}")
                except (ValueError, AttributeError):
                    info_parts.append(f"Tạo lúc: {created}")
            
            if info_parts:
                text += f" ({', '.join(info_parts)})"
            
            item.setText(text)
            # Đánh dấu là local hole
            item.setData(Qt.ItemDataRole.UserRole + 1, 'local')
            self.hole_list.addItem(item)
    
    def _load_holes_from_api(self, silent: bool = False):
        """
        BẮT BUỘC: Tải danh sách hố khoan TỪ API
        Không cho phép placeholder hoặc tạo local
        """
        if not API_AVAILABLE or not self.api_client:
            error_msg = (
                "❌ LỖI: API không khả dụng!\n\n"
                "Hệ thống BẮT BUỘC phải cấu hình API để lấy danh sách hố khoan.\n\n"
                "Vui lòng cấu hình trong Quản lý dự án:\n"
                "- api_base_url: https://nomin.wintech.io.vn/api\n"
                "- api_project_id: [ID dự án trên server]"
            )
            if not silent:
                QMessageBox.critical(self, "Lỗi cấu hình API", error_msg)
            return
        
        api_project_id = self._get_api_project_id()
        if not api_project_id:
            if not silent:
                QMessageBox.critical(
                    self, 
                    "Thiếu API Project ID", 
                    "BẮT BUỘC: Phải cấu hình 'api_project_id' trong project_info.json\n\n"
                    "Không có API Project ID, không thể lấy danh sách hố khoan."
                )
            return
        
        try:
            # Debug: In ra thông tin cấu hình
            api_base_url = self._get_api_base_url()
            print(f"\n{'='*60}")
            print(f"DEBUG: Đang tải holes từ API")
            print(f"  - API Base URL: {api_base_url}")
            print(f"  - API Project ID: {api_project_id}")
            print(f"  - Endpoint: /projects/{api_project_id}/holes")
            print(f"  - URL đầy đủ: {api_base_url}/projects/{api_project_id}/holes")
            print(f"{'='*60}\n")
            
            # Không hiển thị message "Đang tải" nữa - chỉ in console
            # Message sẽ hiển thị khi hoàn tất
            
            # Lấy tất cả holes từ API (base_url đã có /api)
            result = self.api_client.get_all_holes(api_project_id)
            
            # Debug: In ra kết quả
            print(f"DEBUG: API Response:")
            print(f"  - Success: {result.get('success') if result else 'None'}")
            print(f"  - Holes count: {len(result.get('holes', [])) if result else 0}")
            
            if not result or not result.get('success'):
                error_msg = (
                    f"❌ Không thể lấy danh sách hố khoan từ API\n\n"
                    f"URL: {api_base_url}/projects/{api_project_id}/holes\n\n"
                    f"Kiểm tra:\n"
                    f"• API base URL có đúng?\n"
                    f"• Project ID có tồn tại trên server?\n"
                    f"• Server có đang chạy?\n"
                    f"• Kết nối mạng có ổn định?"
                )
                print(f"ERROR: {error_msg}")
                print(f"Response: {result}")
                if not silent:
                    QMessageBox.critical(self, "Lỗi kết nối API", error_msg)
                return
            
            api_holes = result.get('holes', [])
            if not api_holes:
                print("WARNING: API trả về success=True nhưng không có holes")
                if not silent:
                    QMessageBox.information(
                        self, 
                        "Không có dữ liệu", 
                        f"Không có hố khoan nào trong dự án (Project ID: {api_project_id})\n\n"
                        f"Bạn có thể tạo hố khoan mới thủ công."
                    )
                return
            
            # Lấy danh sách local holes để lưu API data
            # (Vẫn cần lưu local để sync API data với filesystem)
            local_holes = self.project_manager.list_holes()
            local_hole_names = {hole.get('name') for hole in local_holes}
            local_hole_by_name = {hole.get('name'): hole for hole in local_holes}
            
            # Lấy danh sách holes đã có trong UI để tránh duplicate
            existing_hole_names = set()
            for i in range(self.hole_list.count()):
                item = self.hole_list.item(i)
                hole = item.data(Qt.ItemDataRole.UserRole)
                if hole:
                    existing_hole_names.add(hole.get('name'))
            
            # Thêm/cập nhật holes từ API vào danh sách
            holes_added = 0
            holes_synced = 0
            
            print(f"\nDEBUG: Processing {len(api_holes)} holes from API...")
            
            for api_hole in api_holes:
                # Parse hole ID (ưu tiên field "id" string như "LK1", fallback sang "hole_id")
                hole_id_str = str(api_hole.get('id', ''))  # "LK1", "LK2", etc.
                if not hole_id_str or hole_id_str == 'None':
                     hole_id_str = api_hole.get('hole_id', '')
                     
                hole_name = hole_id_str or api_hole.get('name', f"Hole_{api_hole.get('id', 'Unknown')}")
                
                # Debug: In ra thông tin hole đầu tiên
                if holes_added == 0 and holes_synced == 0:
                    print(f"\nDEBUG: Hole đầu tiên từ API:")
                    print(f"  - ID: {api_hole.get('id')}")
                    print(f"  - Hole name: {hole_name}")
                    print(f"  - Design: {api_hole.get('design_name')}")
                    print(f"  - GPS: {api_hole.get('gps')}")
                    print(f"  - Depth: {api_hole.get('depth')}")
                    print()
                
                # Parse GPS data (có thể nằm trong object "gps" hoặc trực tiếp ở root)
                gps_data = api_hole.get('gps', {})
                gps_lat = gps_data.get('lat') if gps_data else api_hole.get('gps_lat')
                gps_lon = gps_data.get('lon') if gps_data else api_hole.get('gps_lon')
                # elevation có thể null
                gps_elevation = gps_data.get('elevation') if gps_data else api_hole.get('gps_elevation')
                
                # Bỏ qua nếu đã có trong danh sách (tránh duplicate trong UI)
                # NOTE: Vẫn cần sync data với local hole
                if hole_name in existing_hole_names:
                    # Hole đã hiển thị trong UI, nhưng vẫn cần sync data
                    if hole_name in local_hole_names:
                        local_hole = local_hole_by_name[hole_name]
                        self._sync_local_hole_with_api(local_hole, api_hole)
                        print(f"  - {hole_name}: Already in UI, synced data")
                    continue
                
                # Kiểm tra xem đã có local hole chưa
                is_local = hole_name in local_hole_names
                
                # Tạo hoặc cập nhật local hole
                if not is_local:
                    # Tạo local hole mới từ API data
                    try:
                        local_hole = self._create_local_hole_from_api(api_hole, hole_name)
                        holes_added += 1
                    except Exception as e:
                        print(f"Lỗi tạo local hole từ API: {e}")
                        continue
                else:
                    # Cập nhật local hole với thông tin từ API
                    local_hole = local_hole_by_name[hole_name]
                    self._sync_local_hole_with_api(local_hole, api_hole)
                    holes_synced += 1
                
                # Thêm vào danh sách hiển thị
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, local_hole)
                item.setData(Qt.ItemDataRole.UserRole + 1, 'api' if not is_local else 'synced')
                
                # Hiển thị thông tin
                text = hole_name
                info_parts = []
                
                # Thông tin từ API
                design_name = api_hole.get('design_name', '')
                if design_name:
                    info_parts.append(f"Design: {design_name}")
                
                if gps_lat is not None and gps_lon is not None:
                    info_parts.append(f"GPS: {gps_lat:.4f}, {gps_lon:.4f}")
                
                depth = api_hole.get('depth')
                if depth:
                    info_parts.append(f"Độ sâu: {depth}m")
                
                if not is_local:
                    info_parts.append("[Từ API]")
                elif holes_synced > 0:
                    info_parts.append("[Đã đồng bộ]")
                
                if info_parts:
                    text += f" ({', '.join(info_parts)})"
                
                item.setText(text)
                self.hole_list.addItem(item)
                existing_hole_names.add(hole_name)  # Đánh dấu đã thêm
            
            # Không cần làm mới vì đã thêm vào danh sách
            
            print(f"\nDEBUG: Load từ API hoàn tất:")
            print(f"  - Tổng holes từ API: {len(api_holes)}")
            print(f"  - Holes mới tạo: {holes_added}")
            print(f"  - Holes đã sync: {holes_synced}")
            
            # Lưu timestamp đồng bộ lần cuối
            self._save_last_sync_time()
            
            # Chỉ hiển thị message khi có holes mới/sync và không phải silent mode
            if not silent and (holes_added > 0 or holes_synced > 0):
                QMessageBox.information(
                    self, 
                    "Đã đồng bộ", 
                    f"✅ Đã đồng bộ {len(api_holes)} hố khoan từ API\n\n"
                    f"• {holes_added} hố khoan mới\n"
                    f"• {holes_synced} hố khoan đã cập nhật"
                )
            
        except Exception as e:
            error_detail = f"Lỗi không mong đợi khi tải từ API:\n\n{str(e)}"
            print(f"ERROR: {error_detail}")
            import traceback
            traceback.print_exc()
            
            if not silent:
                QMessageBox.critical(
                    self, 
                    "Lỗi", 
                    f"{error_detail}\n\n"
                    f"Bạn có thể:\n"
                    f"• Kiểm tra console log để biết chi tiết\n"
                    f"• Thử lại sau\n"
                    f"• Làm việc offline với holes local"
                )
    
    def _create_local_hole_from_api(self, api_hole: Dict, hole_name: str) -> Dict:
        """
        Tạo local hole directory và metadata từ dữ liệu API
        
        NOTE: Đây KHÔNG phải là tạo placeholder!
        Đây là tạo local directory để:
        1. Lưu metadata từ API (GPS, depth, design, etc.)
        2. Lưu session data (recordings, measurements)
        3. Sync với API data
        
        Local hole directory CHỈ được tạo KHI có hole tương ứng trong API.
        """
        # Lấy thông tin từ API
        location = api_hole.get('location', '')
        design_name = api_hole.get('design_name', '')
        notes = f"Từ API - Design: {design_name}" if design_name else "Từ API"
        
        # Tạo local hole
        local_hole = self.project_manager.create_hole(
            name=hole_name,
            location=location,
            notes=notes
        )
        
        # Sync thông tin từ API
        self._sync_local_hole_with_api(local_hole, api_hole)
        
        return local_hole
    
    def _sync_local_hole_with_api(self, local_hole: Dict, api_hole: Dict):
        """
        Đồng bộ thông tin local hole metadata với API
        
        Cập nhật các thông tin từ API vào local hole_info.json:
        - GPS coordinates (lat, lon, elevation)
        - Depth, diameter
        - Design info
        - Row, column positions
        - API hole ID
        """
        import json
        from pathlib import Path
        
        try:
            project_path = Path(self.project_manager.current_project['path'])
            hole_name = local_hole.get('name', '')
            safe_hole_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
            hole_dir = project_path / "holes" / safe_hole_name
            hole_info_file = hole_dir / "hole_info.json"
            
            if not hole_info_file.exists():
                return
            
            # Đọc file hiện tại
            with open(hole_info_file, 'r', encoding='utf-8') as f:
                hole_info = json.load(f)
            
            # Cập nhật thông tin từ API
            # Ưu tiên dùng hole_id string nếu có (thường là field "id" như "LK1")
            hole_id = str(api_hole.get('id', ''))
            if not hole_id:
                hole_id = api_hole.get('hole_id')
            
            hole_info['api_hole_id'] = hole_id
            
            # Parse GPS data
            gps_data = api_hole.get('gps', {})
            hole_info['gps_lon'] = gps_data.get('lon') if gps_data else api_hole.get('gps_lon')
            hole_info['gps_lat'] = gps_data.get('lat') if gps_data else api_hole.get('gps_lat')
            hole_info['gps_elevation'] = gps_data.get('elevation') if gps_data else api_hole.get('gps_elevation')
            
            hole_info['depth'] = api_hole.get('depth')
            hole_info['diameter'] = api_hole.get('diameter')
            hole_info['x'] = api_hole.get('x') or api_hole.get('_localX')
            hole_info['y'] = api_hole.get('y')
            hole_info['z'] = api_hole.get('z') or api_hole.get('_localZ')
            hole_info['row'] = api_hole.get('row')
            hole_info['col'] = api_hole.get('col')
            hole_info['design_id'] = api_hole.get('design_id')
            hole_info['design_name'] = api_hole.get('design_name')
            hole_info['updated_at'] = api_hole.get('updated_at')
            
            # Ghi lại file
            with open(hole_info_file, 'w', encoding='utf-8') as f:
                json.dump(hole_info, f, indent=2, ensure_ascii=False)
            
            # Cập nhật trong memory
            local_hole.update(hole_info)
            
        except Exception as e:
            print(f"Lỗi đồng bộ hole với API: {e}")
    
    # REMOVED: _refresh_hole_list() - Không cần vì chỉ dùng API
    
    def _create_hole(self):
        """Tạo hố khoan mới (CHO PHÉP người dùng tạo thủ công)"""
        name = self.edt_hole_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên hố khoan")
            return
        
        try:
            # Tạo hố khoan mới
            hole = self.project_manager.create_hole(
                name=name,
                location=self.edt_location.text().strip(),
                notes=self.edt_notes.text().strip()
            )
            
            # Làm mới danh sách
            self._load_holes()
            
            # Chọn hố vừa tạo
            for i in range(self.hole_list.count()):
                item = self.hole_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole).get('name') == hole['name']:
                    self.hole_list.setCurrentRow(i)
                    break
            
            # Xóa nội dung đã nhập
            self.edt_hole_name.clear()
            self.edt_location.clear()
            self.edt_notes.clear()
            
            QMessageBox.information(self, "Thành công", f"Đã tạo hố khoan '{name}' thành công!")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo hố khoan: {str(e)}")
    
    def _delete_selected_holes(self):
        """Xóa các hố khoan đã chọn"""
        selected_items = self.hole_list.selectedItems()
        if not selected_items:
            return
        
        count = len(selected_items)
        if count == 1:
            hole = selected_items[0].data(Qt.ItemDataRole.UserRole)
            name = hole.get('name', 'hố khoan này')
            msg = f'Bạn có chắc chắn muốn xóa hố khoan "{name}"?\n\nLưu ý: Tất cả dữ liệu của hố khoan này sẽ bị xóa vĩnh viễn!'
        else:
            msg = f'Bạn có chắc chắn muốn xóa {count} hố khoan đã chọn?\n\nLưu ý: Tất cả dữ liệu của các hố khoan này sẽ bị xóa vĩnh viễn!'
        
        reply = QMessageBox.question(
            self,
            'Xác nhận xóa',
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            errors = []
            
            for item in selected_items:
                hole = item.data(Qt.ItemDataRole.UserRole)
                hole_name = hole.get('name')
                hole_path = hole.get('path')
                if hole_name:
                    if self.project_manager.delete_hole(hole_name, hole_path):
                        deleted_count += 1
                    else:
                        errors.append(hole_name)
            
            # Refresh danh sách - tải cả local và API
            self.hole_list.clear()
            self._load_holes()
            
            # Tải lại từ API nếu có cấu hình
            if API_AVAILABLE and self.api_client and self._get_api_project_id():
                self._load_holes_from_api(silent=True)
            
            if errors:
                QMessageBox.warning(self, "Cảnh báo", f"Đã xóa {deleted_count} hố khoan.\nKhông thể xóa các hố khoan sau: {', '.join(errors)}")
            else:
                QMessageBox.information(self, "Thành công", f"Đã xóa {deleted_count} hố khoan thành công.")

    def _on_selection_changed(self):
        """Xử lý sự kiện chọn hố khoan"""
        selected_items = self.hole_list.selectedItems()
        count = len(selected_items)
        
        # Chọn và Cấu hình chỉ hoạt động với 1 item
        self.btn_select.setEnabled(count == 1)
        self.btn_settings.setEnabled(count == 1)
        
        # Xóa hoạt động với 1 hoặc nhiều item
        self.btn_delete.setEnabled(count > 0)
    
    def _configure_hole(self):
        """Mở hộp thoại cấu hình hố khoan"""
        selected = self.get_selected_hole()
        if not selected:
            return
        
        # Lấy danh sách tất cả holes (để tìm gần nhất)
        all_holes = []
        for i in range(self.hole_list.count()):
            item = self.hole_list.item(i)
            hole = item.data(Qt.ItemDataRole.UserRole)
            if hole:
                all_holes.append(hole)
        
        # Mở dialog cấu hình (pass gnss_service và all_holes)
        from .hole_settings_dialog import HoleSettingsDialog
        dialog = HoleSettingsDialog(
            self.project_manager, 
            selected, 
            self,
            gnss_service=self.gnss_service,
            all_holes=all_holes
        )
        if dialog.exec():
            # Làm mới danh sách
            self.hole_list.clear()
            self._load_holes()
            if API_AVAILABLE and self.api_client and self._get_api_project_id():
                self._load_holes_from_api(silent=True)
    
    def _on_hole_selected(self, item):
        """Xử lý sự kiện chọn nhanh hố khoan"""
        self.accept()
    
    def get_selected_hole(self) -> Optional[Dict]:
        """Lấy thông tin hố khoan đã chọn"""
        selected = self.hole_list.currentItem()
        if selected:
            return selected.data(Qt.ItemDataRole.UserRole)
        return None
    
    def accept(self):
        """Xử lý khi nhấn nút Chọn"""
        selected = self.get_selected_hole()
        if selected:
            self.selected_hole = selected
            
            # Kiểm tra xem hole có từ API không, nếu có thì sync lại
            selected_item = self.hole_list.currentItem()
            if selected_item:
                source = selected_item.data(Qt.ItemDataRole.UserRole + 1)
                if source == 'api' or source == 'synced':
                    # Đồng bộ lại từ API để đảm bảo thông tin mới nhất
                    api_project_id = self._get_api_project_id()
                    if api_project_id and self.api_client:
                        api_hole_id = selected.get('api_hole_id')
                        if api_hole_id:
                            try:
                                api_hole = self.api_client.get_hole(api_project_id, api_hole_id)
                                if api_hole and api_hole.get('success'):
                                    self._sync_local_hole_with_api(selected, api_hole.get('hole', {}))
                            except Exception as e:
                                print(f"Lỗi sync hole khi chọn: {e}")
            
            # Lấy GPS từ API nếu chưa có (fallback)
            if self.api_client and (not selected.get('gps_lat') or not selected.get('gps_lon')):
                self._load_gps_from_api(selected)
            
            self.hole_selected.emit(selected)
            super().accept()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một hố khoan")
    
    def _load_gps_from_api(self, hole: Dict):
        """Lấy GPS coordinates từ API và cập nhật vào hole info"""
        if not self.api_client:
            return
        
        api_project_id = self._get_api_project_id()
        if not api_project_id:
            return
        
        # Tìm hole trong API bằng hole_id (tên hole)
        hole_name = hole.get('name', '')
        if not hole_name:
            return
        
        try:
            # Tìm hole trong API
            api_hole = self.api_client.find_hole_by_hole_id(api_project_id, hole_name)
            
            if api_hole:
                # Lấy GPS coordinates
                gps_data = api_hole.get('gps', {})
                gps_lon = gps_data.get('lon') if gps_data else api_hole.get('gps_lon')
                gps_lat = gps_data.get('lat') if gps_data else api_hole.get('gps_lat')
                gps_elevation = gps_data.get('elevation') if gps_data else api_hole.get('gps_elevation')
                
                if gps_lon is not None and gps_lat is not None:
                    # Cập nhật vào hole info
                    hole['gps_lon'] = gps_lon
                    hole['gps_lat'] = gps_lat
                    hole['gps_elevation'] = gps_elevation
                    
                    # Parse ID
                    hole_id = str(api_hole.get('id', ''))
                    if not hole_id:
                        hole_id = api_hole.get('hole_id')
                    hole['api_hole_id'] = hole_id
                    
                    # Lưu vào file hole_info.json
                    self._save_hole_info(hole)
                    
                    # Hiển thị thông báo
                    QMessageBox.information(
                        self,
                        "Đã tải GPS",
                        f"Đã tải tọa độ GPS từ API:\n"
                        f"Kinh độ: {gps_lon:.6f}\n"
                        f"Vĩ độ: {gps_lat:.6f}\n"
                        f"Độ cao: {gps_elevation or 'N/A'}"
                    )
        except Exception as e:
            # Không hiển thị lỗi nếu API không khả dụng
            print(f"Lỗi khi lấy GPS từ API: {e}")
    
    def _save_last_sync_time(self):
        """Lưu timestamp đồng bộ lần cuối vào project_info.json"""
        if not self.project_manager.current_project:
            return
        
        try:
            import json
            from datetime import datetime
            from pathlib import Path
            
            project_path = Path(self.project_manager.current_project['path'])
            info_file = project_path / "project_info.json"
            
            if info_file.exists():
                with open(info_file, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
                
                project_info['last_api_sync'] = datetime.now().isoformat()
                
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(project_info, f, indent=2, ensure_ascii=False)
                
                # Cập nhật trong memory
                self.project_manager.current_project['last_api_sync'] = project_info['last_api_sync']
                
                print(f"INFO: Đã lưu timestamp sync: {project_info['last_api_sync']}")
        except Exception as e:
            print(f"WARNING: Không thể lưu timestamp sync: {e}")
    
    def _save_hole_info(self, hole: Dict):
        """Lưu thông tin hole vào file hole_info.json"""
        try:
            import json
            from pathlib import Path
            
            if not self.project_manager.current_project:
                return
            
            project_path = Path(self.project_manager.current_project['path'])
            hole_name = hole.get('name', '')
            if not hole_name:
                return
            
            # Tạo safe directory name
            safe_hole_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
            hole_dir = project_path / "holes" / safe_hole_name
            hole_info_file = hole_dir / "hole_info.json"
            
            if hole_info_file.exists():
                # Đọc file hiện tại
                with open(hole_info_file, 'r', encoding='utf-8') as f:
                    hole_info = json.load(f)
                
                # Cập nhật GPS data
                hole_info['gps_lon'] = hole.get('gps_lon')
                hole_info['gps_lat'] = hole.get('gps_lat')
                hole_info['gps_elevation'] = hole.get('gps_elevation')
                hole_info['api_hole_id'] = hole.get('api_hole_id')
                
                # Ghi lại file
                with open(hole_info_file, 'w', encoding='utf-8') as f:
                    json.dump(hole_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi khi lưu hole info: {e}")


if __name__ == "__main__":
    # Test dialog
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Tạo thư mục test nếu chưa có
    import os
    test_dir = "test_projects/test_project"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Khởi tạo ProjectManager với thư mục test
    project_manager = ProjectManager("test_projects")
    
    # Tạo một dự án mẫu nếu chưa có
    if not project_manager.current_project:
        project_manager.create_project("Dự án kiểm thử", "Dự án để kiểm tra hộp thoại hố khoan")
    
    # Hiển thị hộp thoại
    dialog = HoleDialog(project_manager)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Đã chọn hố khoan:", dialog.selected_hole)
    else:
        print("Đã hủy chọn hố khoan")
    
    sys.exit()
