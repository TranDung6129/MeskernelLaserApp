"""
Project Dialog - Hộp thoại quản lý dự án
"""
from typing import Optional, Dict, List, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QFormLayout, QDialogButtonBox, QAbstractItemView, QWidget, QFrame
)

from .project_manager import ProjectManager


class ProjectDialog(QDialog):
    """Hộp thoại quản lý dự án"""
    project_selected = pyqtSignal(dict)  # Khi người dùng chọn một dự án
    
    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_project = None
        
        self.setWindowTitle("Quản lý dự án")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._load_projects()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Phần tạo dự án mới
        new_project_group = self._create_new_project_group()
        layout.addWidget(new_project_group)
        
        # Danh sách dự án
        layout.addWidget(QLabel("Danh sách dự án:"))
        
        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.itemDoubleClicked.connect(self._on_project_selected)
        layout.addWidget(self.project_list)
        
        # Nút điều khiển
        button_box = QDialogButtonBox()
        
        self.btn_select = button_box.addButton("Chọn", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_select.setEnabled(False)
        self.btn_delete = button_box.addButton("Xóa", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_delete.setEnabled(False)
        button_box.addButton("Đóng", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.btn_delete.clicked.connect(self._delete_selected_project)
        
        layout.addWidget(button_box)
        
        # Kết nối sự kiện chọn dự án
        self.project_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _create_new_project_group(self) -> QWidget:
        """Tạo nhóm tạo dự án mới"""
        group = QWidget()
        layout = QVBoxLayout(group)
        
        # Tiêu đề
        layout.addWidget(QLabel("Tạo dự án mới:"))
        
        # Form nhập thông tin
        form_layout = QFormLayout()
        
        self.edt_project_name = QLineEdit()
        self.edt_project_name.setPlaceholderText("Nhập tên dự án")
        form_layout.addRow("Tên dự án:", self.edt_project_name)
        
        self.edt_description = QLineEdit()
        self.edt_description.setPlaceholderText("Mô tả ngắn (tùy chọn)")
        form_layout.addRow("Mô tả:", self.edt_description)
        
        layout.addLayout(form_layout)
        
        # Nút tạo dự án
        btn_create = QPushButton("Tạo dự án mới")
        btn_create.clicked.connect(self._create_project)
        layout.addWidget(btn_create)
        
        # Đường kẻ ngăn cách
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        return group
    
    def _load_projects(self):
        """Tải danh sách dự án"""
        self.project_list.clear()
        projects = self.project_manager.list_projects()
        
        for project in projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, project)
            
            # Hiển thị thông tin dự án
            name = project.get('name', 'Không có tên')
            desc = project.get('description', '')
            updated = project.get('updated_at', '')
            
            # Tạo text đơn giản, không dùng HTML
            text = name
            if desc:
                text += f" - {desc}"
            if updated:
                text += f" (cập nhật: {updated})"
            
            item.setText(text)
            self.project_list.addItem(item)
    
    def _create_project(self):
        """Tạo dự án mới"""
        name = self.edt_project_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên dự án")
            return
        
        try:
            # Tạo dự án mới
            project = self.project_manager.create_project(
                name=name,
                description=self.edt_description.text().strip()
            )
            
            # Làm mới danh sách
            self._load_projects()
            
            # Chọn dự án vừa tạo
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole).get('path') == project['path']:
                    self.project_list.setCurrentRow(i)
                    break
            
            # Xóa nội dung đã nhập
            self.edt_project_name.clear()
            self.edt_description.clear()
            
            QMessageBox.information(self, "Thành công", f"Đã tạo dự án '{name}' thành công!")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo dự án: {str(e)}")
    
    def _delete_selected_project(self):
        """Xóa dự án đã chọn"""
        selected = self.project_list.currentItem()
        if not selected:
            return
        
        project = selected.data(Qt.ItemDataRole.UserRole)
        name = project.get('name', 'dự án này')
        
        reply = QMessageBox.question(
            self,
            'Xác nhận xóa',
            f'Bạn có chắc chắn muốn xóa dự án "{name}"?\n\n' +
            'Lưu ý: Tất cả dữ liệu trong dự án sẽ bị xóa vĩnh viễn!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # TODO: Thực hiện xóa thư mục dự án
                import shutil
                import os
                
                project_path = project.get('path')
                if project_path and os.path.exists(project_path):
                    shutil.rmtree(project_path)
                    self._load_projects()
                    QMessageBox.information(self, "Thành công", f"Đã xóa dự án '{name}'")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa dự án: {str(e)}")
    
    def _on_selection_changed(self):
        """Xử lý sự kiện chọn dự án"""
        has_selection = bool(self.project_list.selectedItems())
        self.btn_select.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
    
    def _on_project_selected(self, item):
        """Xử lý sự kiện chọn nhanh dự án"""
        self.accept()
    
    def get_selected_project(self) -> Optional[Dict]:
        """Lấy thông tin dự án đã chọn"""
        selected = self.project_list.currentItem()
        if selected:
            return selected.data(Qt.ItemDataRole.UserRole)
        return None
    
    def accept(self):
        """Xử lý khi nhấn nút Chọn"""
        selected = self.get_selected_project()
        if selected:
            self.selected_project = selected
            self.project_selected.emit(selected)
            super().accept()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một dự án")


if __name__ == "__main__":
    # Test dialog
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Tạo thư mục test nếu chưa có
    import os
    test_dir = "test_projects"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Khởi tạo ProjectManager với thư mục test
    project_manager = ProjectManager(test_dir)
    
    # Tạo một số dự án mẫu nếu chưa có
    if not project_manager.list_projects():
        project_manager.create_project("Dự án mẫu 1", "Đây là dự án mẫu đầu tiên")
        project_manager.create_project("Dự án thử nghiệm", "Dự án để kiểm tra các tính năng")
    
    # Hiển thị hộp thoại
    dialog = ProjectDialog(project_manager)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Đã chọn dự án:", dialog.selected_project)
    else:
        print("Đã hủy chọn dự án")
    
    sys.exit()
