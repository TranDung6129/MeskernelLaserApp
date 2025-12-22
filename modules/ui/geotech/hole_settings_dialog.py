"""
Hole Settings Dialog - Hộp thoại cấu hình thông tin hố khoan (GPS, API)
"""
import json
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QDialogButtonBox,
    QGroupBox, QDoubleSpinBox
)

from .project_manager import ProjectManager

try:
    from modules.utils.hole_finder import find_nearest_hole, format_distance
    HOLE_FINDER_AVAILABLE = True
except ImportError:
    HOLE_FINDER_AVAILABLE = False
    find_nearest_hole = None
    format_distance = None


class HoleSettingsDialog(QDialog):
    """Hộp thoại cấu hình thông tin hố khoan"""
    
    def __init__(self, project_manager: ProjectManager, hole: Dict, parent=None, gnss_service=None, all_holes=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.hole = hole
        self.hole_info = None
        self.gnss_service = gnss_service
        self.all_holes = all_holes or []
        
        self.setWindowTitle(f"Cấu hình hố khoan: {hole.get('name', 'Unknown')}")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._load_hole_info()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin cơ bản
        basic_group = QGroupBox("Thông tin cơ bản")
        basic_layout = QFormLayout(basic_group)
        
        self.edt_name = QLineEdit()
        self.edt_name.setReadOnly(True)  # Không cho sửa tên
        basic_layout.addRow("Tên hố khoan:", self.edt_name)
        
        self.edt_location = QLineEdit()
        basic_layout.addRow("Vị trí:", self.edt_location)
        
        self.edt_notes = QLineEdit()
        basic_layout.addRow("Ghi chú:", self.edt_notes)
        
        layout.addWidget(basic_group)
        
        # Tọa độ GPS
        gps_group = QGroupBox("Tọa độ GPS")
        gps_layout = QVBoxLayout(gps_group)
        
        # Nút lấy GPS
        gps_buttons = QHBoxLayout()
        
        btn_get_gnss = QPushButton("📍 Lấy vị trí hiện tại")
        btn_get_gnss.setToolTip("Lấy tọa độ GPS từ GNSS")
        btn_get_gnss.setEnabled(self.gnss_service is not None)
        btn_get_gnss.clicked.connect(self._get_current_location)
        gps_buttons.addWidget(btn_get_gnss)
        
        btn_find_nearest = QPushButton("🎯 Lấy từ hole gần nhất")
        btn_find_nearest.setToolTip("Lấy GPS từ hố khoan gần nhất")
        btn_find_nearest.setEnabled(
            HOLE_FINDER_AVAILABLE and 
            self.gnss_service is not None and 
            len(self.all_holes) > 1
        )
        btn_find_nearest.clicked.connect(self._get_from_nearest_hole)
        gps_buttons.addWidget(btn_find_nearest)
        
        gps_layout.addLayout(gps_buttons)
        
        # GPS fields
        gps_form = QFormLayout()
        
        self.spin_gps_lon = QDoubleSpinBox()
        self.spin_gps_lon.setMinimum(-180.0)
        self.spin_gps_lon.setMaximum(180.0)
        self.spin_gps_lon.setDecimals(8)
        self.spin_gps_lon.setSpecialValueText("Chưa cấu hình")
        gps_form.addRow("Kinh độ (lon):", self.spin_gps_lon)
        
        self.spin_gps_lat = QDoubleSpinBox()
        self.spin_gps_lat.setMinimum(-90.0)
        self.spin_gps_lat.setMaximum(90.0)
        self.spin_gps_lat.setDecimals(8)
        self.spin_gps_lat.setSpecialValueText("Chưa cấu hình")
        gps_form.addRow("Vĩ độ (lat):", self.spin_gps_lat)
        
        self.spin_gps_elevation = QDoubleSpinBox()
        self.spin_gps_elevation.setMinimum(-1000.0)
        self.spin_gps_elevation.setMaximum(10000.0)
        self.spin_gps_elevation.setDecimals(2)
        self.spin_gps_elevation.setSuffix(" m")
        self.spin_gps_elevation.setSpecialValueText("Chưa cấu hình")
        gps_form.addRow("Độ cao (elevation):", self.spin_gps_elevation)
        
        gps_layout.addLayout(gps_form)
        
        layout.addWidget(gps_group)
        
        # API Info
        api_group = QGroupBox("Thông tin API")
        api_layout = QFormLayout(api_group)
        
        self.edt_api_hole_id = QLineEdit()
        self.edt_api_hole_id.setPlaceholderText("VD: LK1, HK01, 3, ... (có thể là string hoặc số)")
        api_layout.addRow("API Hole ID:", self.edt_api_hole_id)
        
        layout.addWidget(api_group)
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        button_box.addButton("Lưu", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("Hủy", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _load_hole_info(self):
        """Tải thông tin hố khoan"""
        try:
            project_path = Path(self.project_manager.current_project['path'])
            hole_name = self.hole.get('name', '')
            safe_hole_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
            hole_dir = project_path / "holes" / safe_hole_name
            hole_info_file = hole_dir / "hole_info.json"
            
            if not hole_info_file.exists():
                QMessageBox.warning(self, "Cảnh báo", "Không tìm thấy file hole_info.json")
                return
            
            with open(hole_info_file, 'r', encoding='utf-8') as f:
                self.hole_info = json.load(f)
            
            # Load thông tin cơ bản
            self.edt_name.setText(self.hole_info.get('name', ''))
            self.edt_location.setText(self.hole_info.get('location', ''))
            self.edt_notes.setText(self.hole_info.get('notes', ''))
            
            # Load GPS
            gps_lon = self.hole_info.get('gps_lon')
            if gps_lon is not None:
                self.spin_gps_lon.setValue(float(gps_lon))
            
            gps_lat = self.hole_info.get('gps_lat')
            if gps_lat is not None:
                self.spin_gps_lat.setValue(float(gps_lat))
            
            gps_elevation = self.hole_info.get('gps_elevation')
            if gps_elevation is not None:
                self.spin_gps_elevation.setValue(float(gps_elevation))
            
            # Load API hole ID (có thể là string hoặc số)
            api_hole_id = self.hole_info.get('api_hole_id')
            if api_hole_id is not None:
                # Chuyển đổi thành string để hiển thị
                self.edt_api_hole_id.setText(str(api_hole_id))
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin hố khoan: {str(e)}")
    
    def _get_current_location(self):
        """Lấy tọa độ GPS hiện tại từ GNSS"""
        if not self.gnss_service:
            QMessageBox.warning(
                self,
                "Không có GNSS",
                "GNSS service chưa được khởi tạo."
            )
            return
        
        try:
            gnss_data = self.gnss_service.get_latest_data()
            
            if not gnss_data:
                QMessageBox.warning(
                    self,
                    "Không có dữ liệu",
                    "Chưa nhận được dữ liệu GNSS.\n\n"
                    "Kiểm tra kết nối MQTT và GNSS device."
                )
                return
            
            lat = gnss_data.get('latitude') or gnss_data.get('lat')
            lon = gnss_data.get('longitude') or gnss_data.get('lon')
            elev = gnss_data.get('elevation') or gnss_data.get('altitude')
            
            if lat is None or lon is None:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    "Dữ liệu GNSS không có tọa độ."
                )
                return
            
            # Điền vào form
            self.spin_gps_lat.setValue(lat)
            self.spin_gps_lon.setValue(lon)
            if elev is not None:
                self.spin_gps_elevation.setValue(elev)
            
            QMessageBox.information(
                self,
                "Đã lấy vị trí",
                f"✅ Đã lấy GPS từ GNSS:\n\n"
                f"Vĩ độ: {lat:.8f}\n"
                f"Kinh độ: {lon:.8f}\n"
                f"Độ cao: {elev:.2f}m" if elev else f"Độ cao: N/A"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể lấy vị trí:\n\n{str(e)}"
            )
    
    def _get_from_nearest_hole(self):
        """Lấy GPS từ hole gần nhất với vị trí hiện tại"""
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
                "Cần GNSS service để xác định vị trí hiện tại."
            )
            return
        
        try:
            # Lấy vị trí hiện tại
            gnss_data = self.gnss_service.get_latest_data()
            
            if not gnss_data:
                QMessageBox.warning(
                    self,
                    "Không có dữ liệu GNSS",
                    "Chưa nhận được dữ liệu GNSS."
                )
                return
            
            current_lat = gnss_data.get('latitude') or gnss_data.get('lat')
            current_lon = gnss_data.get('longitude') or gnss_data.get('lon')
            current_elev = gnss_data.get('elevation') or gnss_data.get('altitude')
            
            if current_lat is None or current_lon is None:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    "Dữ liệu GNSS không có tọa độ."
                )
                return
            
            # Lọc holes có GPS (loại bỏ hole hiện tại)
            current_hole_name = self.hole.get('name')
            holes_with_gps = [
                h for h in self.all_holes 
                if h.get('gps_lat') and h.get('gps_lon') and h.get('name') != current_hole_name
            ]
            
            if not holes_with_gps:
                QMessageBox.information(
                    self,
                    "Không có dữ liệu",
                    "Không có hố khoan nào khác có tọa độ GPS."
                )
                return
            
            # Tìm hole gần nhất
            nearest = find_nearest_hole(
                current_lat,
                current_lon,
                current_elev,
                holes_with_gps,
                max_distance=10000,  # 10km
                use_3d=True
            )
            
            if not nearest:
                QMessageBox.information(
                    self,
                    "Không tìm thấy",
                    "Không tìm thấy hố khoan nào có GPS trong bán kính 10km."
                )
                return
            
            # Lấy GPS từ hole gần nhất
            hole_lat = nearest.get('gps_lat')
            hole_lon = nearest.get('gps_lon')
            hole_elev = nearest.get('gps_elevation')
            distance = nearest.get('_distance', 0)
            
            # Hỏi xác nhận
            reply = QMessageBox.question(
                self,
                "Xác nhận",
                f"🎯 Hố khoan gần nhất: {nearest.get('name')}\n"
                f"Khoảng cách: {format_distance(distance)}\n\n"
                f"GPS của hole đó:\n"
                f"• Vĩ độ: {hole_lat:.8f}\n"
                f"• Kinh độ: {hole_lon:.8f}\n"
                f"• Độ cao: {hole_elev:.2f}m\n\n"
                f"Lấy GPS này cho hole hiện tại?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Điền vào form
                self.spin_gps_lat.setValue(hole_lat)
                self.spin_gps_lon.setValue(hole_lon)
                if hole_elev is not None:
                    self.spin_gps_elevation.setValue(hole_elev)
                
                QMessageBox.information(
                    self,
                    "Đã cập nhật",
                    f"✅ Đã lấy GPS từ hole {nearest.get('name')}"
                )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể lấy GPS từ hole gần nhất:\n\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _save_settings(self):
        """Lưu cấu hình"""
        if not self.hole_info:
            return
        
        try:
            project_path = Path(self.project_manager.current_project['path'])
            hole_name = self.hole.get('name', '')
            safe_hole_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
            hole_dir = project_path / "holes" / safe_hole_name
            hole_info_file = hole_dir / "hole_info.json"
            
            if not hole_info_file.exists():
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy file hole_info.json")
                return
            
            # Cập nhật thông tin
            self.hole_info['location'] = self.edt_location.text().strip()
            self.hole_info['notes'] = self.edt_notes.text().strip()
            
            # Cập nhật GPS
            gps_lon = self.spin_gps_lon.value()
            if gps_lon != 0.0 or self.spin_gps_lon.specialValueText() not in str(gps_lon):
                self.hole_info['gps_lon'] = gps_lon
            elif 'gps_lon' in self.hole_info:
                del self.hole_info['gps_lon']
            
            gps_lat = self.spin_gps_lat.value()
            if gps_lat != 0.0 or self.spin_gps_lat.specialValueText() not in str(gps_lat):
                self.hole_info['gps_lat'] = gps_lat
            elif 'gps_lat' in self.hole_info:
                del self.hole_info['gps_lat']
            
            gps_elevation = self.spin_gps_elevation.value()
            if gps_elevation != 0.0 or self.spin_gps_elevation.specialValueText() not in str(gps_elevation):
                self.hole_info['gps_elevation'] = gps_elevation
            elif 'gps_elevation' in self.hole_info:
                del self.hole_info['gps_elevation']
            
            # Cập nhật API hole ID (có thể là string hoặc số)
            api_hole_id_text = self.edt_api_hole_id.text().strip()
            if api_hole_id_text:
                # Thử chuyển đổi thành số nếu có thể (để tương thích ngược)
                try:
                    # Nếu là số, lưu dưới dạng int
                    api_hole_id_int = int(api_hole_id_text)
                    self.hole_info['api_hole_id'] = api_hole_id_int
                except ValueError:
                    # Nếu không phải số, lưu dưới dạng string
                    self.hole_info['api_hole_id'] = api_hole_id_text
            elif 'api_hole_id' in self.hole_info:
                del self.hole_info['api_hole_id']
            
            # Ghi lại file
            with open(hole_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.hole_info, f, indent=2, ensure_ascii=False)
            
            # Cập nhật trong memory
            self.hole.update(self.hole_info)
            if self.project_manager.current_hole and self.project_manager.current_hole.get('name') == hole_name:
                self.project_manager.current_hole = self.hole_info
            
            QMessageBox.information(self, "Thành công", "Đã lưu cấu hình hố khoan")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình: {str(e)}")

