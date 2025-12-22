"""
Project Settings Dialog - Hộp thoại cấu hình thông tin dự án (API, MQTT)
"""
import json
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QDialogButtonBox,
    QGroupBox, QSpinBox, QDoubleSpinBox
)

from .project_manager import ProjectManager


class ProjectSettingsDialog(QDialog):
    """Hộp thoại cấu hình thông tin dự án"""
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.project_info = None
        
        self.setWindowTitle("Cấu hình dự án")
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_project_info()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin cơ bản
        basic_group = QGroupBox("Thông tin cơ bản")
        basic_layout = QFormLayout(basic_group)
        
        self.edt_name = QLineEdit()
        self.edt_name.setReadOnly(True)  # Không cho sửa tên
        basic_layout.addRow("Tên dự án:", self.edt_name)
        
        self.edt_description = QLineEdit()
        basic_layout.addRow("Mô tả:", self.edt_description)
        
        layout.addWidget(basic_group)
        
        # Cấu hình API
        api_group = QGroupBox("Cấu hình API")
        api_layout = QFormLayout(api_group)
        
        self.edt_api_base_url = QLineEdit()
        self.edt_api_base_url.setPlaceholderText("https://nomin.wintech.io.vn/api")
        api_layout.addRow("API Base URL:", self.edt_api_base_url)
        
        self.spin_api_project_id = QSpinBox()
        self.spin_api_project_id.setMinimum(0)
        self.spin_api_project_id.setMaximum(999999)
        self.spin_api_project_id.setSpecialValueText("Chưa cấu hình")
        api_layout.addRow("API Project ID:", self.spin_api_project_id)
        
        layout.addWidget(api_group)
        
        # Note về MQTT
        note_label = QLabel(
            "<b>Lưu ý:</b> Cấu hình MQTT cho GNSS RTK được quản lý trong tab <b>MQTT</b> "
            "của ứng dụng, không cần cấu hình ở đây."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(note_label)
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        button_box.addButton("Lưu", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("Hủy", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _load_project_info(self):
        """Tải thông tin dự án hiện tại"""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn dự án")
            self.reject()
            return
        
        self.project_info = self.project_manager.current_project
        
        # Load thông tin cơ bản
        self.edt_name.setText(self.project_info.get('name', ''))
        self.edt_description.setText(self.project_info.get('description', ''))
        
        # Load API config
        api_base_url = self.project_info.get('api_base_url', 'https://nomin.wintech.io.vn/api')
        self.edt_api_base_url.setText(api_base_url)
        
        api_project_id = self.project_info.get('api_project_id')
        if api_project_id:
            try:
                self.spin_api_project_id.setValue(int(api_project_id))
            except (ValueError, TypeError):
                pass
    
    def _save_settings(self):
        """Lưu cấu hình"""
        if not self.project_info:
            return
        
        try:
            project_path = Path(self.project_info['path'])
            project_info_file = project_path / "project_info.json"
            
            if not project_info_file.exists():
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy file project_info.json")
                return
            
            # Đọc file hiện tại
            with open(project_info_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Cập nhật thông tin
            project_data['description'] = self.edt_description.text().strip()
            
            # Cập nhật API config
            api_base_url = self.edt_api_base_url.text().strip()
            if api_base_url:
                project_data['api_base_url'] = api_base_url
            
            api_project_id = self.spin_api_project_id.value()
            if api_project_id > 0:
                project_data['api_project_id'] = api_project_id
            elif 'api_project_id' in project_data:
                del project_data['api_project_id']
            
            # Ghi lại file
            with open(project_info_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            # Cập nhật trong memory
            self.project_info.update(project_data)
            self.project_manager.current_project = self.project_info
            
            QMessageBox.information(self, "Thành công", "Đã lưu cấu hình dự án")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình: {str(e)}")

