"""
Geotech Form - Form thông tin hố khoan cho Geotech Panel
Chứa form nhập thông tin hố khoan và các nút điều khiển
"""
import os
import time
import csv
from pathlib import Path
from typing import Dict, Any, Callable, Optional
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QCheckBox, QFileDialog, 
    QMessageBox, QLabel, QFrame
)

from .project_manager import ProjectManager
from .project_dialog import ProjectDialog
from .hole_dialog import HoleDialog
from .recording_dialog import RecordingDialog
from .data_selector_dialog import DataSelectorDialog


class GeotechFormWidget(QWidget):
    """Widget form thông tin hố khoan cho Geotech Panel"""
    # Tín hiệu khi bắt đầu/dừng ghi dữ liệu
    recording_started = pyqtSignal(dict)  # Chứa thông tin cấu hình ghi
    recording_stopped = pyqtSignal()      # Khi dừng ghi
    session_started = pyqtSignal()        # Khi bắt đầu session mới
    
    # Callback functions (can be set by parent)
    on_save_requested = None
    on_export_requested = None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording: bool = False
        self.project_manager = ProjectManager()
        self.recording_settings: Optional[Dict] = None
        
        self._setup_ui()
        self._update_ui_state()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Thông tin dự án và hố khoan hiện tại
        info_group = QGroupBox("Thông tin")
        info_layout = QVBoxLayout(info_group)
        
        # Dự án hiện tại
        project_layout = QHBoxLayout()
        self.lbl_project = QLabel("<b>Dự án:</b> Chưa chọn dự án")
        self.btn_project = QPushButton("Quản lý dự án")
        self.btn_project.clicked.connect(self._manage_projects)
        project_layout.addWidget(self.lbl_project, 1)
        project_layout.addWidget(self.btn_project)
        
        # Hố khoan hiện tại
        hole_layout = QHBoxLayout()
        self.lbl_hole = QLabel("<b>Hố khoan:</b> Chưa chọn hố khoan")
        self.btn_hole = QPushButton("Quản lý hố khoan")
        self.btn_hole.clicked.connect(self._manage_holes)
        self.btn_hole.setEnabled(False)  # Chỉ bật khi có dự án
        hole_layout.addWidget(self.lbl_hole, 1)
        hole_layout.addWidget(self.btn_hole)
        
        info_layout.addLayout(project_layout)
        info_layout.addLayout(hole_layout)
        
        # Đường kẻ ngăn cách
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        info_layout.addWidget(line)
        
        # Thông tin hố khoan chi tiết
        self.lbl_hole_info = QLabel("Vui lòng chọn hoặc tạo mới một hố khoan để bắt đầu ghi dữ liệu.")
        self.lbl_hole_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_hole_info)
        
        # Nút điều khiển
        buttons_layout = QHBoxLayout()
        self.btn_start = QPushButton("Bắt đầu ghi")
        self.btn_save = QPushButton("Xem dữ liệu đã lưu")
        self.btn_save.setEnabled(True)  # Luôn cho phép xem dữ liệu đã lưu
        self.btn_start.clicked.connect(self._toggle_recording)
        self.btn_save.clicked.connect(self._view_saved_data)
        
        buttons_layout.addWidget(self.btn_start, 1)
        buttons_layout.addWidget(self.btn_save, 1)
        
        # Thêm các thành phần vào layout chính
        layout.addWidget(info_group, 1)
        layout.addLayout(buttons_layout)
        
        # Kết nối sự kiện
        self._connect_signals()
    
    def _connect_signals(self):
        """Kết nối các tín hiệu"""
        pass
    
    def _update_ui_state(self, recording_state_changed: bool = False):
        """Cập nhật trạng thái UI dựa trên trạng thái hiện tại
        
        Args:
            recording_state_changed: Nếu True, chỉ cập nhật trạng thái liên quan đến ghi dữ liệu
        """
        if not recording_state_changed:
            # Chỉ cập nhật các phần không liên quan đến trạng thái ghi
            # Cập nhật thông tin dự án và hố khoan
            if self.project_manager.current_project:
                self.lbl_project.setText(f"<b>Dự án:</b> {self.project_manager.current_project.get('name', 'Không có tên')}")
                self.btn_hole.setEnabled(True)
                
                if self.project_manager.current_hole:
                    hole = self.project_manager.current_hole
                    self.lbl_hole.setText(f"<b>Hố khoan:</b> {hole.get('name', 'Không có tên')}")
                    
                    # Hiển thị thông tin chi tiết hố khoan
                    info_lines = []
                    if 'location' in hole and hole['location']:
                        info_lines.append(f"<b>Vị trí:</b> {hole['location']}")
                    if 'created_at' in hole and hole['created_at']:
                        info_lines.append(f"<b>Ngày tạo:</b> {hole['created_at']}")
                    if 'notes' in hole and hole['notes']:
                        info_lines.append(f"<b>Ghi chú:</b> {hole['notes']}")
                    
                    if info_lines:
                        self.lbl_hole_info.setText("<br>".join(info_lines))
                    else:
                        self.lbl_hole_info.setText("Không có thông tin chi tiết.")
                    
                    # Bật nút bắt đầu ghi nếu đã chọn hố khoan
                    self.btn_start.setEnabled(True)
                    self.btn_save.setEnabled(True)
                    self.lbl_hole_info.setText("<br>".join(info_lines))
                else:
                    self.lbl_hole_info.setText("Không có thông tin chi tiết.")
                    # Tắt nút bắt đầu ghi nếu chưa chọn hố khoan
                    self.btn_start.setEnabled(False)
                    self.btn_save.setEnabled(False)
            else:
                self.lbl_hole.setText("<b>Hố khoan:</b> Chưa chọn hố khoan")
                self.lbl_hole_info.setText("Vui lòng chọn hoặc tạo mới một hố khoan để bắt đầu ghi dữ liệu.")
                self.btn_start.setEnabled(False)
                self.btn_save.setEnabled(False)
        else:
            self.lbl_project.setText("<b>Dự án:</b> Chưa chọn dự án")
            self.lbl_hole.setText("<b>Hố khoan:</b> Chưa chọn hố khoan")
            self.lbl_hole_info.setText("Vui lòng tạo hoặc chọn một dự án để bắt đầu.")
            self.btn_hole.setEnabled(False)
            self.btn_start.setEnabled(False)
            self.btn_save.setEnabled(False)
        
        # Cập nhật giao diện khi đang ghi
        if self.is_recording:
            self.btn_start.setText("Dừng ghi")
            self.btn_start.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
            self.btn_save.setEnabled(False)
            self.btn_project.setEnabled(False)
            self.btn_hole.setEnabled(False)
        else:
            self.btn_start.setText("Bắt đầu ghi")
            self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_project.setEnabled(True)
            self.btn_hole.setEnabled(bool(self.project_manager.current_project))
    
    def _manage_projects(self):
        """Mở hộp thoại quản lý dự án"""
        dialog = ProjectDialog(self.project_manager, self)
        if dialog.exec():
            # Đã chọn một dự án
            project = dialog.get_selected_project()
            if project:
                self.project_manager.load_project(project['path'])
                # Reset hố khoan hiện tại khi chuyển dự án
                self.project_manager.current_hole = None
                self._update_ui_state()
    
    def _manage_holes(self):
        """Mở hộp thoại quản lý hố khoan"""
        if not self.project_manager.current_project:
            return
            
        dialog = HoleDialog(self.project_manager, self)
        if dialog.exec():
            # Đã chọn một hố khoan
            hole = dialog.get_selected_hole()
            if hole:
                self.project_manager.current_hole = hole
                self._update_ui_state()
    
    def _toggle_recording(self):
        """Bật/tắt chế độ ghi dữ liệu"""
        if not self.is_recording:
            # Bắt đầu ghi mới
            self._start_recording()
        else:
            # Dừng ghi
            self._stop_recording()
    
    def _start_recording(self):
        """Bắt đầu ghi dữ liệu mới"""
        if not self.project_manager.current_project or not self.project_manager.current_hole:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn dự án và hố khoan trước khi bắt đầu ghi.")
            return
        
        # Hiển thị hộp thoại cấu hình ghi
        dialog = RecordingDialog(self.project_manager, self)
        if dialog.exec() != RecordingDialog.DialogCode.Accepted:
            return
        
        # Lấy cài đặt ghi
        self.recording_settings = dialog.get_recording_settings()
        
        # Cập nhật trạng thái
        self.is_recording = True
        self._update_ui_state()
        
        # Phát tín hiệu bắt đầu ghi
        self.recording_started.emit(self.recording_settings)
        
        # Phát tín hiệu bắt đầu session mới
        self.session_started.emit()
    
    def _stop_recording(self):
        """Dừng ghi dữ liệu"""
        # Xác nhận trước khi dừng
        reply = QMessageBox.question(
            self, 
            "Xác nhận dừng ghi", 
            "Bạn có chắc chắn muốn dừng ghi dữ liệu?\nDữ liệu sẽ được lưu tự động vào file CSV.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Cập nhật trạng thái
            self.is_recording = False
            self._update_ui_state()
            
            # Phát tín hiệu dừng ghi
            self.recording_stopped.emit()
            
            # TỰ ĐỘNG LƯU DỮ LIỆU CSV
            success = self._auto_save_recording_data()
            
            # Thông báo kết quả
            if success:
                QMessageBox.information(
                    self, 
                    "Hoàn thành", 
                    "Đã dừng ghi dữ liệu và lưu thành công vào file CSV."
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Cảnh báo", 
                    "Đã dừng ghi dữ liệu nhưng có lỗi khi lưu CSV.\nBạn có thể lưu thủ công từ menu File."
                )
    
    def _auto_save_recording_data(self) -> bool:
        """Tự động lưu dữ liệu recording thành CSV"""
        try:
            # Validate prerequisites
            if not self.project_manager.current_project or not self.project_manager.current_hole:
                # Missing project/hole for auto-save
                return False
            
            if not self.recording_settings:
                # Missing recording settings
                return False
            
            # Get data from parent GeotechPanel
            parent_panel = None
            # Find parent GeotechPanel by walking up widget hierarchy
            widget = self.parent()
            while widget is not None:
                if hasattr(widget, 'depth_series_m'):  # GeotechPanel has this attribute
                    parent_panel = widget
                    break
                widget = widget.parent()
            
            if not parent_panel:
                # Parent GeotechPanel not found
                return False
            
            # Check if we have data to save
            if not parent_panel.depth_series_m:
                # No measurement data to save
                # Still return True as this might be intentional (empty session)
                QMessageBox.information(
                    self, 
                    "Không có dữ liệu", 
                    "Phiên ghi không có dữ liệu đo để lưu."
                )
                return True
            
            # Get filename from recording settings
            filename = self.recording_settings.get('filename', '')
            if not filename:
                # Generate default filename if not provided
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                hole_name = self.project_manager.current_hole.get('name', 'data')
                filename = f"{hole_name}_{timestamp}.csv"
            
            # Ensure .csv extension
            if not filename.lower().endswith('.csv'):
                filename += '.csv'
            
            # Create data structure for ProjectManager.save_data() format
            data_rows = []
            depth_series = parent_panel.depth_series_m
            velocity_series = parent_panel.velocity_series_ms
            time_series = parent_panel.time_series
            state_series = parent_panel.state_series
            quality_series = parent_panel.quality_series
            
            # Get hole info for metadata
            hole_info = self.get_borehole_info()
            
            # Convert to list of dictionaries (ProjectManager format)
            for i in range(len(depth_series)):
                row = {
                    'timestamp': time_series[i] if i < len(time_series) else '',
                    'depth_m': f"{depth_series[i]:.6f}",
                    'velocity_ms': f"{velocity_series[i]:.6f}" if i < len(velocity_series) else '',
                    'state': state_series[i] if i < len(state_series) else '',
                    'signal_quality': quality_series[i] if i < len(quality_series) else '',
                    'borehole_name': hole_info.get('name', ''),
                    'location': hole_info.get('location', ''),
                    'operator': hole_info.get('operator', ''),
                    'notes': hole_info.get('notes', '')
                }
                data_rows.append(row)
            
            # Save using ProjectManager
            saved_path = self.project_manager.save_data(data_rows, filename)
            # Auto-saved successfully
            
            return True
            
        except Exception:
            return False
    
    def _view_saved_data(self):
        """Xem dữ liệu đã lưu - mở hộp thoại chọn dữ liệu"""
        try:
            # Mở hộp thoại chọn dữ liệu
            dialog = DataSelectorDialog(self.project_manager, self)
            if dialog.exec():
                file_path, hole_info = dialog.get_selected_data()
                if file_path and os.path.exists(file_path):
                    # Đọc dữ liệu từ file
                    self._load_and_show_data(file_path, hole_info)
                else:
                    QMessageBox.warning(self, "Lỗi", "Không tìm thấy file dữ liệu đã chọn.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi mở hộp thoại chọn dữ liệu: {str(e)}")
    
    def _load_and_show_data(self, file_path: str, hole_info: Dict):
        """Tải và hiển thị dữ liệu từ file"""
        try:
            # Đọc dữ liệu từ file CSV
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
            
            if not data:
                QMessageBox.information(self, "Thông tin", "File dữ liệu trống.")
                return
            
            # Hiển thị hộp thoại chế độ xem
            file_name = os.path.basename(file_path)
            self._show_data_viewer(data, hole_info, file_name)
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc file dữ liệu: {str(e)}")
    
    def _show_data_viewer(self, data, hole, file_name):
        """Hiển thị hộp thoại xem dữ liệu hoặc phát lại"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
        
        class DataViewerChoiceDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Chọn chế độ xem dữ liệu")
                self.setMinimumWidth(300)
                
                layout = QVBoxLayout(self)
                
                # Nội dung hướng dẫn
                label = QLabel("Chọn cách bạn muốn xem dữ liệu:")
                layout.addWidget(label)
                
                # Nút xem dạng bảng
                btn_table = QPushButton("Xem dạng bảng")
                btn_table.clicked.connect(self.accept_table)
                
                # Nút phát lại dữ liệu
                btn_replay = QPushButton("Phát lại dữ liệu")
                btn_replay.clicked.connect(self.accept_replay)
                
                # Nút hủy
                btn_cancel = QPushButton("Hủy")
                btn_cancel.clicked.connect(self.reject)
                
                # Thêm các nút vào layout
                layout.addWidget(btn_table)
                layout.addWidget(btn_replay)
                layout.addSpacing(20)
                layout.addWidget(btn_cancel)
                
                # Biến lưu kết quả
                self.choice = None
            
            def accept_table(self):
                self.choice = "table"
                self.accept()
                
            def accept_replay(self):
                self.choice = "replay"
                self.accept()
        
        # Hiển thị hộp thoại chọn chế độ xem
        choice_dialog = DataViewerChoiceDialog(self)
        result = choice_dialog.exec()
        
        if result == QDialog.DialogCode.Accepted and choice_dialog.choice:
            if choice_dialog.choice == "table":
                # Hiển thị dữ liệu trong DataViewerDialog
                from .data_viewer_dialog import DataViewerDialog
                
                dialog = DataViewerDialog(
                    data, 
                    title=f"Dữ liệu hố khoan: {hole.get('name', '')} - {file_name}",
                    parent=self
                )
                dialog.exec()
                
            elif choice_dialog.choice == "replay":
                # Phát lại dữ liệu
                self._replay_data(data, f"{hole.get('name', '')} - {file_name}")
    
    def _replay_data(self, data, title):
        """Phát lại dữ liệu đã lưu"""
        if not data:
            QMessageBox.warning(self, "Lỗi", "Không có dữ liệu để phát lại.")
            return
        
        try:
            # Kiểm tra xem có dữ liệu hợp lệ không
            has_valid_data = False
            for row in data:
                if any(isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()) for val in row.values()):
                    has_valid_data = True
                    break
            
            if not has_valid_data:
                QMessageBox.warning(
                    self, 
                    "Dữ liệu không phù hợp", 
                    "Dữ liệu không chứa các trường số để hiển thị trên biểu đồ. "
                    "Vui lòng chọn xem dạng bảng thay thế."
                )
                return
            
            # Hiển thị hộp thoại phát lại
            from .replay_dialog import ReplayDialog
            
            dialog = ReplayDialog(
                data,
                title=f"Phát lại dữ liệu: {title}",
                parent=self
            )
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Lỗi phát lại dữ liệu", 
                f"Không thể phát lại dữ liệu: {str(e)}"
            )
    
    def get_borehole_info(self) -> Dict[str, Any]:
        """Lấy thông tin hố khoan hiện tại"""
        if self.project_manager.current_hole:
            return self.project_manager.current_hole.copy()
        return {}
    
    def _ensure_borehole_dir(self) -> str:
        """Tạo và đảm bảo thư mục hố khoan tồn tại"""
        project = self.project_manager.current_project
        hole = self.project_manager.current_hole
        
        if not project or not hole:
            raise ValueError("Chưa chọn dự án hoặc hố khoan")
        
        # Tạo đường dẫn thư mục hố khoan
        project_dir = Path(project["path"])
        hole_name = hole.get('name', 'unknown_hole')
        # Tạo tên thư mục an toàn
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
        hole_dir = project_dir / "holes" / safe_name
        
        # Tạo thư mục nếu chưa tồn tại
        hole_dir.mkdir(parents=True, exist_ok=True)
        
        return str(hole_dir)
    
    def _auto_create_project_and_hole(self):
        """Tự động tạo dự án và hố khoan mặc định nếu chưa có"""
        try:
            # Auto-create project if none exists
            if not self.project_manager.current_project:
                from datetime import datetime
                project_name = f"Project_{datetime.now().strftime('%Y%m%d')}"
            # Auto-creating project
                self.project_manager.create_project(project_name, "Auto-created project")
            
            # Auto-create hole if none exists
            if not self.project_manager.current_hole:
                from datetime import datetime
                hole_name = f"Hole_{datetime.now().strftime('%H%M%S')}"
                # Auto-creating hole
                self.project_manager.create_hole(hole_name, "Auto-created for data saving")
                
            return True
        except Exception:
            return False

    def get_save_path(self) -> str:
        """Lấy đường dẫn lưu file CSV"""
        # Try auto-create if missing
        if not self.project_manager.current_project or not self.project_manager.current_hole:
            if not self._auto_create_project_and_hole():
                QMessageBox.warning(
                    self, 
                    "Không thể tạo dự án", 
                    "Không thể tự động tạo dự án/hố khoan.\nVui lòng tạo thủ công trước khi lưu."
                )
                return ""
        
        # Validate prerequisites
        project = self.project_manager.current_project
        hole = self.project_manager.current_hole
        
        if not project:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng tạo hoặc chọn một dự án trước khi lưu.")
            return ""
            
        if not hole:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng tạo hoặc chọn một hố khoan trước khi lưu.")
            return ""
        
        try:
            bdir = self._ensure_borehole_dir()
            ts_str = time.strftime('%Y%m%d_%H%M%S')
            hole_name = hole.get('name', 'data')
            default_path = os.path.join(bdir, f"{hole_name}_{ts_str}.csv")
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Lưu dữ liệu hố khoan", default_path, "CSV Files (*.csv)"
            )
            return filename
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo đường dẫn lưu file: {e}")
            return ""
    
    def save_data_to_csv(self, data: Dict[str, Any]) -> bool:
        """Lưu dữ liệu ra file CSV"""
        # Validate data first
        if not data:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có dữ liệu để lưu.\nVui lòng đo dữ liệu trước khi lưu.")
            return False
        
        # Check if we have actual measurement data
        depth_series = data.get('depth_series', [])
        if not depth_series:
            QMessageBox.warning(self, "Không có dữ liệu đo", "Không có dữ liệu đo để lưu.\nVui lòng thực hiện đo trước khi lưu.")
            return False
        
        filename = self.get_save_path()
        if not filename:
            return False
        
        try:
            # Get borehole info for metadata
            hole_info = self.get_borehole_info()
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "depth_m", "velocity_ms", "state", "signal_quality",
                    "borehole_name", "location", "operator", "notes"
                ])
                
                meta = (
                    hole_info.get('name', ''),
                    hole_info.get('location', ''),
                    hole_info.get('operator', ''),
                    hole_info.get('notes', '')
                )
                
                # Get data from data dict
                velocity_series = data.get('velocity_series', [])
                time_series = data.get('time_series', [])
                state_series = data.get('state_series', [])
                quality_series = data.get('quality_series', [])
                
                # Ensure all series have same length for safety
                max_len = max(len(depth_series), len(velocity_series), len(time_series), 
                             len(state_series), len(quality_series))
                
                if max_len == 0:
                    QMessageBox.warning(self, "Không có dữ liệu", "Các series dữ liệu đều rỗng.")
                    return False
                
                for i in range(len(depth_series)):
                    writer.writerow([
                        time_series[i] if i < len(time_series) else '',
                        f"{depth_series[i]:.6f}",
                        f"{velocity_series[i]:.6f}" if i < len(velocity_series) else '',
                        state_series[i] if i < len(state_series) else '',
                        quality_series[i] if i < len(quality_series) else '',
                        meta[0], meta[1], meta[2], meta[3]
                    ])
            
            # Show success message with details
            data_count = len(depth_series)
            QMessageBox.information(
                self, 
                "Lưu dữ liệu thành công", 
                f"Đã lưu {data_count} dữ liệu đo thành công:\n{filename}\n\nHố khoan: {meta[0]}\nVị trí: {meta[1]}"
            )
            # Saved successfully
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu dữ liệu", f"Không thể lưu CSV:\n{str(e)}\n\nVui lòng kiểm tra quyền ghi file và thử lại.")
            # Save CSV failed
            return False
    
    def trigger_save(self):
        """Trigger save operation từ external caller"""
        try:
            if callable(self.on_save_requested):
                self.on_save_requested()
            else:
                QMessageBox.warning(self, "Chức năng chưa sẵn sàng", "Chức năng lưu chưa được thiết lập.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu dữ liệu: {e}")
            
    def trigger_export(self):
        """Trigger export operation từ external caller"""
        try:
            if callable(self.on_export_requested):
                self.on_export_requested()
            else:
                QMessageBox.warning(self, "Chức năng chưa sẵn sàng", "Chức năng xuất chưa được thiết lập.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất dữ liệu: {e}")
