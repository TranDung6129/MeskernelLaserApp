"""
Recording Dialog - Hộp thoại cấu hình ghi dữ liệu
"""
import os
import json
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QFormLayout, QDialogButtonBox, QCheckBox, QGroupBox,
    QFileDialog
)

from .project_manager import ProjectManager


class RecordingDialog(QDialog):
    """Hộp thoại cấu hình trước khi bắt đầu ghi dữ liệu"""
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.fields = []
        self.selected_fields = set()
        
        self.setWindowTitle("Cấu hình ghi dữ liệu")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._load_fields()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin hố khoan hiện tại
        hole_info = self._create_hole_info_group()
        layout.addWidget(hole_info)
        
        # Chọn tên file
        file_group = self._create_file_group()
        layout.addWidget(file_group)
        
        # Chọn các trường dữ liệu
        fields_group = self._create_fields_group()
        layout.addWidget(fields_group, 1)  # Cho phép co giãn
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        button_box.addButton("Bắt đầu ghi", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("Hủy", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _create_hole_info_group(self) -> QGroupBox:
        """Tạo nhóm hiển thị thông tin hố khoan"""
        group = QGroupBox("Thông tin hố khoan")
        layout = QVBoxLayout(group)
        
        if self.project_manager.current_project and self.project_manager.current_hole:
            project = self.project_manager.current_project
            hole = self.project_manager.current_hole
            
            layout.addWidget(QLabel(f"<b>Dự án:</b> {project.get('name', 'Không có tên')}"))
            layout.addWidget(QLabel(f"<b>Hố khoan:</b> {hole.get('name', 'Không có tên')}"))
            
            location = hole.get('location')
            if location:
                layout.addWidget(QLabel(f"<b>Vị trí:</b> {location}"))
            
            notes = hole.get('notes')
            if notes:
                layout.addWidget(QLabel(f"<b>Ghi chú:</b> {notes}"))
        else:
            layout.addWidget(QLabel("<b>Lỗi:</b> Chưa chọn dự án hoặc hố khoan"))
        
        return group
    
    def _create_file_group(self) -> QGroupBox:
        """Tạo nhóm chọn tên file"""
        group = QGroupBox("Tùy chọn file")
        layout = QFormLayout(group)
        
        self.edt_filename = QLineEdit()
        self.edt_filename.setPlaceholderText("Tự động tạo tên file nếu để trống")
        
        self.chk_auto_name = QCheckBox("Tự động đặt tên file")
        self.chk_auto_name.setChecked(True)
        self.chk_auto_name.toggled.connect(self._on_auto_name_toggled)
        
        layout.addRow("Tên file:", self.edt_filename)
        layout.addRow("", self.chk_auto_name)
        
        # Tạo tên file mặc định
        self._generate_default_filename()
        
        return group
    
    def _create_fields_group(self) -> QGroupBox:
        """Tạo nhóm chọn trường dữ liệu"""
        group = QGroupBox("Chọn trường dữ liệu")
        layout = QVBoxLayout(group)
        
        # Danh sách các trường có thể chọn
        self.fields_list = QListWidget()
        self.fields_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.fields_list.itemChanged.connect(self._on_field_selection_changed)
        
        # Nút chọn tất cả/bỏ chọn tất cả
        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("Chọn tất cả")
        btn_select_none = QPushButton("Bỏ chọn tất cả")
        
        btn_select_all.clicked.connect(lambda: self._toggle_all_fields(True))
        btn_select_none.clicked.connect(lambda: self._toggle_all_fields(False))
        
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_select_none)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.fields_list)
        
        return group
    
    def _load_fields(self):
        """Tải danh sách các trường dữ liệu từ cấu hình dự án"""
        self.fields_list.clear()
        
        if not self.project_manager.current_project:
            return
        
        # Lấy danh sách các trường từ cấu hình dự án
        project_dir = self.project_manager.current_project.get('path')
        if not project_dir:
            return
        config_file = os.path.join(project_dir, "fields_config.json")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.fields = config.get('fields', [])
                
                # Thêm các trường vào danh sách
                for field in self.fields:
                    name = field.get('name', '')
                    unit = field.get('unit', '')
                    required = field.get('required', False)
                    
                    # Chỉ enable các trường mặc định cần thiết
                    default_fields = ['Thời gian', 'Độ sâu', 'Vận tốc']
                    enabled = required or (name in default_fields)
                    
                    item = QListWidgetItem()
                    item.setText(f"{name} ({unit})" if unit else name)
                    item.setData(Qt.ItemDataRole.UserRole, field)
                    item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    
                    if required:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                        item.setCheckState(Qt.CheckState.Checked)
                    
                    self.fields_list.addItem(item)
                    
                    if enabled:
                        self.selected_fields.add(name)
                        
        except (FileNotFoundError, json.JSONDecodeError):
            QMessageBox.warning(self, "Cảnh báo", "Không tìm thấy cấu hình trường dữ liệu. Sử dụng cấu hình mặc định.")
            
            # Sử dụng các trường mặc định nếu không tìm thấy file cấu hình
            default_fields = [
                {"name": "Thời gian", "unit": "datetime", "required": True, "enabled": True},
                {"name": "Độ sâu", "unit": "m", "required": True, "enabled": True},
                {"name": "Vận tốc", "unit": "m/s", "required": True, "enabled": True},
                {"name": "Lực đập", "unit": "N", "required": False, "enabled": False},
                {"name": "Nhiệt độ", "unit": "°C", "required": False, "enabled": False},
                {"name": "Ghi chú", "unit": "text", "required": False, "enabled": False}
            ]
            
            self.fields = default_fields
            
            for field in default_fields:
                name = field['name']
                unit = field['unit']
                required = field['required']
                enabled = field['enabled']
                
                item = QListWidgetItem()
                item.setText(f"{name} ({unit})" if unit else name)
                item.setData(Qt.ItemDataRole.UserRole, field)
                item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                if required:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Checked)
                
                self.fields_list.addItem(item)
                
                if enabled:
                    self.selected_fields.add(name)
    
    def _on_auto_name_toggled(self, checked: bool):
        """Xử lý sự kiện bật/tắt tự động đặt tên file"""
        self.edt_filename.setEnabled(not checked)
        if checked:
            self._generate_default_filename()
    
    def _generate_default_filename(self):
        """Tạo tên file mặc định dựa trên thời gian hiện tại"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.project_manager.current_hole:
            hole_name = self.project_manager.current_hole.get('name', 'data')
            safe_hole_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in hole_name).strip()
            default_name = f"{safe_hole_name}_{timestamp}.csv"
        else:
            default_name = f"data_{timestamp}.csv"
        
        self.edt_filename.setText(default_name)
        self.edt_filename.setPlaceholderText(default_name)
    
    def _on_field_selection_changed(self, item: QListWidgetItem):
        """Xử lý sự kiện thay đổi lựa chọn trường dữ liệu"""
        field = item.data(Qt.ItemDataRole.UserRole)
        if not field:
            return
        
        field_name = field.get('name')
        if not field_name:
            return
        
        # Cập nhật danh sách trường đã chọn
        if item.checkState() == Qt.CheckState.Checked:
            self.selected_fields.add(field_name)
        else:
            self.selected_fields.discard(field_name)
    
    def _toggle_all_fields(self, selected: bool):
        """Chọn hoặc bỏ chọn tất cả các trường"""
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            field = item.data(Qt.ItemDataRole.UserRole)
            
            # Bỏ qua các trường bắt buộc
            if field.get('required', False):
                continue
                
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
            
            # Cập nhật danh sách trường đã chọn
            field_name = field.get('name')
            if field_name:
                if selected:
                    self.selected_fields.add(field_name)
                else:
                    self.selected_fields.discard(field_name)
    
    def get_selected_fields(self) -> List[Dict]:
        """Lấy danh sách các trường đã chọn"""
        selected = []
        for field in self.fields:
            if field['name'] in self.selected_fields:
                selected.append(field)
        return selected
    
    def get_filename(self) -> str:
        """Lấy tên file đã chọn hoặc tạo tự động"""
        if self.chk_auto_name.isChecked() or not self.edt_filename.text().strip():
            return self.edt_filename.placeholderText()
        return self.edt_filename.text().strip()
    
    def get_recording_settings(self) -> Dict:
        """Lấy tất cả các cài đặt ghi dữ liệu"""
        return {
            "filename": self.get_filename(),
            "fields": self.get_selected_fields(),
            "auto_name": self.chk_auto_name.isChecked()
        }


if __name__ == "__main__":
    # Self-test block removed for production
    pass
