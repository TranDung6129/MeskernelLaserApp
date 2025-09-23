"""
Data Selector Dialog - Hộp thoại chọn dữ liệu để phát lại
"""
import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QMessageBox, QGroupBox, 
    QFormLayout, QSplitter
)
from PyQt6.QtGui import QFont

from .project_manager import ProjectManager


class DataSelectorDialog(QDialog):
    """Hộp thoại chọn dữ liệu để phát lại"""
    
    def __init__(self, project_manager: ProjectManager = None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager or ProjectManager()
        self.selected_data_file = None
        self.selected_hole_info = None
        
        self.setWindowTitle("Chọn dữ liệu để phát lại")
        self.setMinimumSize(700, 500)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Thiết lập giao diện"""
        layout = QVBoxLayout(self)
        
        # Splitter chính: trái là tree, phải là thông tin
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Khu vực cây dữ liệu
        tree_widget = self._create_tree_widget()
        splitter.addWidget(tree_widget)
        
        # Khu vực thông tin chi tiết
        info_widget = self._create_info_widget()
        info_widget.setMaximumWidth(300)
        splitter.addWidget(info_widget)
        
        splitter.setSizes([400, 300])
        
        # Nút điều khiển
        buttons_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("Làm mới")
        btn_refresh.clicked.connect(self._load_data)
        
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_replay = QPushButton("Phát lại")
        self.btn_replay.setEnabled(False)
        self.btn_replay.setToolTip("Chọn một file dữ liệu cụ thể để bật tùy chọn này")
        self.btn_replay.clicked.connect(self.accept)
        
        buttons_layout.addWidget(btn_refresh)
        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_cancel)
        buttons_layout.addWidget(self.btn_replay)
        
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons_layout)
    
    def _create_tree_widget(self) -> QTreeWidget:
        """Tạo cây hiển thị dữ liệu"""
        widget = QTreeWidget()
        widget.setHeaderLabels(["Tên", "Kích thước", "Thời gian sửa đổi"])
        widget.setAlternatingRowColors(True)
        widget.itemSelectionChanged.connect(self._on_selection_changed)
        widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Font cho tree
        font = QFont("Arial", 11)
        widget.setFont(font)
        
        self.tree_widget = widget
        return widget
    
    def _create_info_widget(self) -> QGroupBox:
        """Tạo widget hiển thị thông tin chi tiết"""
        group = QGroupBox("Thông tin chi tiết")
        layout = QVBoxLayout(group)
        
        # Thông tin dự án
        project_info = QGroupBox("Thông tin dự án")
        project_info.setStyleSheet("QGroupBox { font-size: 12px; font-weight: bold; }")
        project_layout = QFormLayout(project_info)
        
        self.lbl_project_name = QLabel("Chưa chọn")
        self.lbl_project_name.setStyleSheet("font-size: 11px;")
        self.lbl_project_desc = QLabel("Chưa chọn")
        self.lbl_project_desc.setStyleSheet("font-size: 11px;")
        
        # Tạo labels với style đồng bộ
        lbl_project_name_title = QLabel("Tên dự án:")
        lbl_project_name_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_project_desc_title = QLabel("Mô tả:")
        lbl_project_desc_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        project_layout.addRow(lbl_project_name_title, self.lbl_project_name)
        project_layout.addRow(lbl_project_desc_title, self.lbl_project_desc)
        
        # Thông tin hố khoan
        hole_info = QGroupBox("Thông tin hố khoan")
        hole_info.setStyleSheet("QGroupBox { font-size: 12px; font-weight: bold; }")
        hole_layout = QFormLayout(hole_info)
        
        self.lbl_hole_name = QLabel("Chưa chọn")
        self.lbl_hole_name.setStyleSheet("font-size: 11px;")
        self.lbl_hole_location = QLabel("Chưa chọn")
        self.lbl_hole_location.setStyleSheet("font-size: 11px;")
        self.lbl_hole_operator = QLabel("Chưa chọn")
        self.lbl_hole_operator.setStyleSheet("font-size: 11px;")
        self.lbl_hole_notes = QLabel("Chưa chọn")
        self.lbl_hole_notes.setStyleSheet("font-size: 11px;")
        
        # Tạo labels với style đồng bộ
        lbl_hole_name_title = QLabel("Tên hố khoan:")
        lbl_hole_name_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_hole_location_title = QLabel("Vị trí:")
        lbl_hole_location_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_hole_operator_title = QLabel("Người vận hành:")
        lbl_hole_operator_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_hole_notes_title = QLabel("Ghi chú:")
        lbl_hole_notes_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        hole_layout.addRow(lbl_hole_name_title, self.lbl_hole_name)
        hole_layout.addRow(lbl_hole_location_title, self.lbl_hole_location)
        hole_layout.addRow(lbl_hole_operator_title, self.lbl_hole_operator)
        hole_layout.addRow(lbl_hole_notes_title, self.lbl_hole_notes)
        
        # Thông tin file dữ liệu
        file_info = QGroupBox("Thông tin file")
        file_info.setStyleSheet("QGroupBox { font-size: 12px; font-weight: bold; }")
        file_layout = QFormLayout(file_info)
        
        self.lbl_file_name = QLabel("Chưa chọn")
        self.lbl_file_name.setStyleSheet("font-size: 11px;")
        self.lbl_file_size = QLabel("Chưa chọn")
        self.lbl_file_size.setStyleSheet("font-size: 11px;")
        self.lbl_file_modified = QLabel("Chưa chọn")
        self.lbl_file_modified.setStyleSheet("font-size: 11px;")
        self.lbl_file_rows = QLabel("Chưa chọn")
        self.lbl_file_rows.setStyleSheet("font-size: 11px;")
        self.lbl_file_path = QLabel("Chưa chọn")
        self.lbl_file_path.setStyleSheet("font-size: 11px;")
        
        # Tạo labels với style đồng bộ
        lbl_file_name_title = QLabel("Tên file:")
        lbl_file_name_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_file_size_title = QLabel("Kích thước:")
        lbl_file_size_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_file_modified_title = QLabel("Thời gian sửa đổi:")
        lbl_file_modified_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_file_rows_title = QLabel("Số dòng dữ liệu:")
        lbl_file_rows_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        lbl_file_path_title = QLabel("Đường dẫn:")
        lbl_file_path_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        file_layout.addRow(lbl_file_name_title, self.lbl_file_name)
        file_layout.addRow(lbl_file_size_title, self.lbl_file_size)
        file_layout.addRow(lbl_file_modified_title, self.lbl_file_modified)
        file_layout.addRow(lbl_file_rows_title, self.lbl_file_rows)
        file_layout.addRow(lbl_file_path_title, self.lbl_file_path)
        
        layout.addWidget(project_info)
        layout.addWidget(hole_info)
        layout.addWidget(file_info)
        layout.addStretch()
        
        return group
    
    def _load_data(self):
        """Tải dữ liệu vào cây"""
        self.tree_widget.clear()
        
        try:
            # Lấy đường dẫn thư mục projects
            projects_dir = os.path.abspath("projects")  # Đường dẫn tuyệt đối
            if not os.path.exists(projects_dir):
                QMessageBox.warning(self, "Cảnh báo", 
                    f"Không tìm thấy thư mục dự án:\n{projects_dir}\n\n"
                    f"Dữ liệu được lưu trong thư mục: projects/")
                return
            
            # Duyệt qua các dự án
            for project_name in os.listdir(projects_dir):
                project_path = os.path.join(projects_dir, project_name)
                if not os.path.isdir(project_path):
                    continue
                
                # Đọc thông tin dự án
                project_config = os.path.join(project_path, "project.json")
                project_info = {"name": project_name}
                if os.path.exists(project_config):
                    try:
                        with open(project_config, 'r', encoding='utf-8') as f:
                            project_info = json.load(f)
                    except Exception:
                        pass
                
                # Tạo node dự án
                project_item = QTreeWidgetItem(self.tree_widget)
                project_item.setText(0, f"Dự án: {project_info.get('name', project_name)}")
                project_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'project',
                    'path': project_path,
                    'info': project_info
                })
                
                # Tìm thư mục holes
                holes_dir = os.path.join(project_path, "holes")
                if not os.path.exists(holes_dir):
                    continue
                
                # Duyệt qua các hố khoan
                for hole_name in os.listdir(holes_dir):
                    hole_path = os.path.join(holes_dir, hole_name)
                    if not os.path.isdir(hole_path):
                        continue
                    
                    # Đọc thông tin hố khoan
                    hole_info_file = os.path.join(hole_path, "info.json")
                    hole_info = {"name": hole_name}
                    if os.path.exists(hole_info_file):
                        try:
                            with open(hole_info_file, 'r', encoding='utf-8') as f:
                                hole_info = json.load(f)
                        except Exception:
                            pass
                    
                    # Tạo node hố khoan
                    hole_item = QTreeWidgetItem(project_item)
                    hole_item.setText(0, f"Hố khoan: {hole_info.get('name', hole_name)}")
                    hole_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'hole',
                        'path': hole_path,
                        'info': hole_info,
                        'project_info': project_info
                    })
                    
                    # Tìm các file CSV
                    csv_files = []
                    for filename in os.listdir(hole_path):
                        if filename.endswith('.csv'):
                            file_path = os.path.join(hole_path, filename)
                            if os.path.isfile(file_path):
                                # Lấy thông tin file
                                stat = os.stat(file_path)
                                size = stat.st_size
                                mtime = datetime.fromtimestamp(stat.st_mtime)
                                
                                csv_files.append({
                                    'name': filename,
                                    'path': file_path,
                                    'size': size,
                                    'modified': mtime
                                })
                    
                    # Sắp xếp theo thời gian sửa đổi (mới nhất trước)
                    csv_files.sort(key=lambda x: x['modified'], reverse=True)
                    
                    # Tạo node cho các file CSV
                    for file_info in csv_files:
                        file_item = QTreeWidgetItem(hole_item)
                        file_item.setText(0, f"File: {file_info['name']}")
                        file_item.setText(1, f"{file_info['size']:,} bytes")
                        file_item.setText(2, file_info['modified'].strftime('%d/%m/%Y %H:%M'))
                        file_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'file',
                            'path': file_info['path'],
                            'info': file_info,
                            'hole_info': hole_info,
                            'project_info': project_info
                        })
                
                # Mở rộng node dự án
                project_item.setExpanded(True)
            
            # Điều chỉnh độ rộng cột
            for i in range(3):
                self.tree_widget.resizeColumnToContents(i)
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tải dữ liệu: {str(e)}")
    
    def _on_selection_changed(self):
        """Xử lý khi thay đổi lựa chọn"""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            self.btn_replay.setEnabled(False)
            self.btn_replay.setToolTip("Chọn một file dữ liệu cụ thể để bật tùy chọn này")
            self._clear_info_display()
            return
        
        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data and data.get('type') == 'file':
            # Chọn file - bật nút phát lại
            self.btn_replay.setEnabled(True)
            self.btn_replay.setToolTip("Nhấn để phát lại dữ liệu đã chọn")
            self.selected_data_file = data['path']
            self.selected_hole_info = data.get('hole_info', {})
            
            # Hiển thị thông tin
            self._display_file_info(data)
            
        else:
            # Chọn dự án hoặc hố khoan - tắt nút phát lại
            self.btn_replay.setEnabled(False)
            self.btn_replay.setToolTip("Chọn một file dữ liệu cụ thể để bật tùy chọn này")
            self.selected_data_file = None
            self.selected_hole_info = None
            
            if data and data.get('type') == 'project':
                self._display_project_info(data)
            elif data and data.get('type') == 'hole':
                self._display_hole_info(data)
            else:
                # Trường hợp khác - clear tất cả thông tin
                self._clear_info_display()
    
    def _on_item_double_clicked(self, item, column):
        """Xử lý khi double-click item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get('type') == 'file':
            self.accept()
    
    def _display_project_info(self, data: Dict):
        """Hiển thị thông tin dự án"""
        project_info = data.get('info', {})
        
        self.lbl_project_name.setText(project_info.get('name', 'Không có tên'))
        self.lbl_project_desc.setText(project_info.get('description', 'Không có mô tả'))
        
        # Xóa thông tin hố khoan và file
        self.lbl_hole_name.setText("Chưa chọn")
        self.lbl_hole_location.setText("Chưa chọn")
        self.lbl_hole_operator.setText("Chưa chọn")
        self.lbl_hole_notes.setText("Chưa chọn")
        
        self.lbl_file_name.setText("Chưa chọn")
        self.lbl_file_size.setText("Chưa chọn")
        self.lbl_file_modified.setText("Chưa chọn")
        self.lbl_file_rows.setText("Chưa chọn")
        self.lbl_file_path.setText("Chưa chọn")
    
    def _display_hole_info(self, data: Dict):
        """Hiển thị thông tin hố khoan"""
        project_info = data.get('project_info', {})
        hole_info = data.get('info', {})
        
        self.lbl_project_name.setText(project_info.get('name', 'Không có tên'))
        self.lbl_project_desc.setText(project_info.get('description', 'Không có mô tả'))
        
        self.lbl_hole_name.setText(hole_info.get('name', 'Không có tên'))
        self.lbl_hole_location.setText(hole_info.get('location', 'Không có thông tin'))
        self.lbl_hole_operator.setText(hole_info.get('operator', 'Không có thông tin'))
        self.lbl_hole_notes.setText(hole_info.get('notes', 'Không có ghi chú'))
        
        # Xóa thông tin file
        self.lbl_file_name.setText("Chưa chọn")
        self.lbl_file_size.setText("Chưa chọn")
        self.lbl_file_modified.setText("Chưa chọn")
        self.lbl_file_rows.setText("Chưa chọn")
        self.lbl_file_path.setText("Chưa chọn")
    
    def _display_file_info(self, data: Dict):
        """Hiển thị thông tin file"""
        project_info = data.get('project_info', {})
        hole_info = data.get('hole_info', {})
        file_info = data.get('info', {})
        
        self.lbl_project_name.setText(project_info.get('name', 'Không có tên'))
        self.lbl_project_desc.setText(project_info.get('description', 'Không có mô tả'))
        
        self.lbl_hole_name.setText(hole_info.get('name', 'Không có tên'))
        self.lbl_hole_location.setText(hole_info.get('location', 'Không có thông tin'))
        self.lbl_hole_operator.setText(hole_info.get('operator', 'Không có thông tin'))
        self.lbl_hole_notes.setText(hole_info.get('notes', 'Không có ghi chú'))
        
        self.lbl_file_name.setText(file_info.get('name', 'Không có tên'))
        self.lbl_file_size.setText(f"{file_info.get('size', 0):,} bytes")
        modified_time = file_info.get('modified')
        if modified_time:
            if isinstance(modified_time, datetime):
                self.lbl_file_modified.setText(modified_time.strftime('%d/%m/%Y %H:%M'))
            else:
                self.lbl_file_modified.setText(str(modified_time))
        else:
            self.lbl_file_modified.setText('Không có thông tin')
        
        # Hiển thị đường dẫn đầy đủ
        self.lbl_file_path.setText(data['path'])
        self.lbl_file_path.setWordWrap(True)
        self.lbl_file_path.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        
        # Đếm số dòng trong file
        try:
            with open(data['path'], 'r', encoding='utf-8') as f:
                row_count = sum(1 for line in f) - 1  # Trừ header
                self.lbl_file_rows.setText(f"{row_count:,} dòng")
        except Exception:
            self.lbl_file_rows.setText('Không thể đếm')
    
    def _clear_info_display(self):
        """Xóa thông tin hiển thị"""
        labels = [
            self.lbl_project_name, self.lbl_project_desc,
            self.lbl_hole_name, self.lbl_hole_location, 
            self.lbl_hole_operator, self.lbl_hole_notes,
            self.lbl_file_name, self.lbl_file_size,
            self.lbl_file_modified, self.lbl_file_rows, self.lbl_file_path
        ]
        
        for label in labels:
            label.setText("Chưa chọn")
    
    def get_selected_data(self) -> Tuple[str, Dict]:
        """Lấy dữ liệu đã chọn"""
        return self.selected_data_file, self.selected_hole_info


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = DataSelectorDialog()
    if dialog.exec():
        file_path, hole_info = dialog.get_selected_data()
        print(f"Selected file: {file_path}")
        print(f"Hole info: {hole_info}")
    else:
        print("Cancelled")
    
    sys.exit()
