"""
Hole Dialog - Hộp thoại quản lý hố khoan trong dự án
"""
from typing import Optional, Dict, List, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QFormLayout, QDialogButtonBox, QAbstractItemView, QDateTimeEdit, QWidget, QFrame
)

from .project_manager import ProjectManager


class HoleDialog(QDialog):
    """Hộp thoại quản lý hố khoan trong dự án"""
    hole_selected = pyqtSignal(dict)  # Khi người dùng chọn một hố khoan
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_hole = None
        
        self.setWindowTitle("Quản lý hố khoan")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin dự án hiện tại
        self.lbl_project = QLabel("Dự án: " + (self.project_manager.current_project.get('name', 'Chưa chọn dự án') 
                                             if self.project_manager.current_project else 'Chưa chọn dự án'))
        layout.addWidget(self.lbl_project)
        
        # Phần tạo hố khoan mới
        new_hole_group = self._create_new_hole_group()
        layout.addWidget(new_hole_group)
        
        # Danh sách hố khoan
        layout.addWidget(QLabel("Danh sách hố khoan:"))
        
        self.hole_list = QListWidget()
        self.hole_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.hole_list.itemDoubleClicked.connect(self._on_hole_selected)
        layout.addWidget(self.hole_list)
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        
        self.btn_select = button_box.addButton("Chọn", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_select.setEnabled(False)
        self.btn_delete = button_box.addButton("Xóa", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_delete.setEnabled(False)
        button_box.addButton("Đóng", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.btn_delete.clicked.connect(self._delete_selected_hole)
        
        layout.addWidget(button_box)
        
        # Kết nối sự kiện chọn hố khoan
        self.hole_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Tải danh sách hố khoan
        self._load_holes()
    
    def _create_new_hole_group(self) -> QWidget:
        """Tạo nhóm tạo hố khoan mới"""
        group = QWidget()
        layout = QVBoxLayout(group)
        
        # Tiêu đề
        layout.addWidget(QLabel("Tạo hố khoan mới:"))
        
        # Form nhập thông tin
        form_layout = QFormLayout()
        
        self.edt_hole_name = QLineEdit()
        self.edt_hole_name.setPlaceholderText("VD: HK001, LK01, ...")
        form_layout.addRow("Tên hố khoan*:", self.edt_hole_name)
        
        self.edt_location = QLineEdit()
        self.edt_location.setPlaceholderText("VD: Khu vực A, Tầng 1, ...")
        form_layout.addRow("Vị trí:", self.edt_location)
        
        self.edt_notes = QLineEdit()
        self.edt_notes.setPlaceholderText("Ghi chú thêm (nếu có)")
        form_layout.addRow("Ghi chú:", self.edt_notes)
        
        layout.addLayout(form_layout)
        
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
        """Tải danh sách hố khoan"""
        self.hole_list.clear()
        
        if not self.project_manager.current_project:
            return
        
        holes = self.project_manager.list_holes()
        
        for hole in holes:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, hole)
            
            # Hiển thị thông tin hố khoan
            name = hole.get('name', 'Không có tên')
            location = hole.get('location', '')
            created = hole.get('created_at', '')
            data_files = hole.get('data_files', [])
            
            # Tạo text đơn giản, không dùng HTML
            text = name
            
            # Thêm thông tin bổ sung
            info_parts = []
            if location:
                info_parts.append(f"Vị trí: {location}")
            
            if data_files:
                info_parts.append(f"Đã ghi {len(data_files)} lần")
            
            if created:
                try:
                    # Chuyển đổi định dạng ngày tháng cho dễ đọc
                    from datetime import datetime
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    info_parts.append(f"Tạo lúc: {dt.strftime('%d/%m/%Y %H:%M')}")
                except (ValueError, AttributeError):
                    info_parts.append(f"Tạo lúc: {created}")
            
            if info_parts:
                text += f" ({', '.join(info_parts)})"
            
            item.setText(text)
            self.hole_list.addItem(item)
    
    def _create_hole(self):
        """Tạo hố khoan mới"""
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
    
    def _delete_selected_hole(self):
        """Xóa hố khoan đã chọn"""
        selected = self.hole_list.currentItem()
        if not selected:
            return
        
        hole = selected.data(Qt.ItemDataRole.UserRole)
        name = hole.get('name', 'hố khoan này')
        
        reply = QMessageBox.question(
            self,
            'Xác nhận xóa',
            f'Bạn có chắc chắn muốn xóa hố khoan "{name}"?\n\n' +
            'Lưu ý: Tất cả dữ liệu của hố khoan này sẽ bị xóa vĩnh viễn!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # TODO: Thực hiện xóa thư mục hố khoan
                import shutil
                import os
                
                project_path = self.project_manager.current_project.get('path')
                hole_name = hole.get('name')
                
                if project_path and hole_name:
                    hole_dir = os.path.join(project_path, 'holes', hole_name)
                    if os.path.exists(hole_dir):
                        shutil.rmtree(hole_dir)
                        self._load_holes()
                        QMessageBox.information(self, "Thành công", f"Đã xóa hố khoan '{name}'")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa hố khoan: {str(e)}")
    
    def _on_selection_changed(self):
        """Xử lý sự kiện chọn hố khoan"""
        has_selection = bool(self.hole_list.selectedItems())
        self.btn_select.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
    
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
            self.hole_selected.emit(selected)
            super().accept()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một hố khoan")


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
