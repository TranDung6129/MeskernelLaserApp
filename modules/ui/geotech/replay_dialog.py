"""
Replay Dialog - Hộp thoại phát lại dữ liệu đã lưu
"""
import os
import csv
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QGroupBox, QFormLayout, QMessageBox, QSizePolicy
)
from PyQt6.QtGui import QColor

# Import các thành phần từ geotech_panel
from .geotech_charts import GeotechChartsWidget
from .geotech_utils import GeotechUtils


class ReplayDialog(QDialog):
    """Hộp thoại phát lại dữ liệu đã lưu"""
    
    def __init__(self, data: List[Dict], title: str = "Phát lại dữ liệu", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)  # Kích thước mặc định lớn hơn
        # Cho phép resize + có nút Min/Max như một cửa sổ chuẩn
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        try:
            self.setSizeGripEnabled(True)
        except Exception:
            pass
        self.data = data
        self.current_index = 0
        self.is_playing = False
        self.playback_speed = 1.0  # Tốc độ phát lại (1.0 = bình thường)
        
        # Bộ đếm thời gian cho hiệu ứng phát lại
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_timeout)
        self.points_per_second = 10  # Số điểm dữ liệu phát mỗi giây
        
        self._setup_ui()
        self._prepare_data()
    
    def _setup_ui(self):
        """Thiết lập giao diện người dùng"""
        layout = QVBoxLayout(self)
        
        # Biểu đồ hiển thị dữ liệu
        self.chart_widget = GeotechChartsWidget()
        self.chart_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chart_widget, 1)  # Cho phép biểu đồ co giãn
        
        # Thanh điều khiển phát lại
        control_group = QGroupBox("Điều khiển phát lại")
        control_layout = QHBoxLayout(control_group)
        
        # Nút điều khiển
        self.btn_play = QPushButton("▶ Phát")
        self.btn_play.setFixedWidth(100)
        self.btn_play.clicked.connect(self._toggle_playback)
        
        # Thanh trượt tiến độ
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.data) - 1 if self.data else 0)
        self.slider.valueChanged.connect(self._on_slider_moved)
        
        # Nhãn tiến trình (số điểm dữ liệu)
        self.lbl_progress = QLabel("0 / 0")
        self.lbl_progress.setFixedWidth(120)
        
        # Tốc độ phát lại
        self.btn_speed = QPushButton(f"Tốc độ: {self.playback_speed}x")
        self.btn_speed.setFixedWidth(120)
        self.btn_speed.clicked.connect(self._change_playback_speed)
        
        # Thêm các thành phần vào layout
        control_layout.addWidget(self.btn_play)
        control_layout.addWidget(self.slider, 1)  # Cho phép thanh trượt co giãn
        control_layout.addWidget(self.lbl_progress)
        control_layout.addWidget(self.btn_speed)
        
        # Thông tin dữ liệu
        info_group = QGroupBox("Thông tin dữ liệu")
        info_layout = QFormLayout(info_group)
        
        self.lbl_data_info = QLabel("Đang tải dữ liệu...")
        self.lbl_current_point = QLabel("Điểm hiện tại: 0/0")
        
        info_layout.addRow("Thông tin:", self.lbl_data_info)
        info_layout.addRow("Tiến trình:", self.lbl_current_point)
        
        # Thêm các nhóm vào layout chính
        layout.addWidget(control_group)
        layout.addWidget(info_group)
        
        # Nút đóng
        btn_box = QHBoxLayout()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        
        layout.addLayout(btn_box)
    
    def _prepare_data(self):
        """Chuẩn bị dữ liệu để phát lại"""
        if not self.data:
            self.lbl_data_info.setText("Không có dữ liệu để phát lại.")
            return
        
        # Lấy danh sách các trường dữ liệu
        fields = list(self.data[0].keys()) if self.data else []
        
        # Tìm các trường dữ liệu số để hiển thị trên biểu đồ
        numeric_fields = []
        self.time_field = None
        self.depth_field = None
        self.velocity_field = None
        
        for field in fields:
            field_lower = field.lower()
            if field_lower in ['thời gian', 'time', 'timestamp']:
                self.time_field = field
            elif any(keyword in field_lower for keyword in ['độ sâu', 'depth']):
                self.depth_field = field
                numeric_fields.append(field)
            elif any(keyword in field_lower for keyword in ['vận tốc', 'velocity', 'speed']):
                self.velocity_field = field
                numeric_fields.append(field)
            elif any(keyword in field_lower for keyword in ['lực', 'force', 'load']):
                numeric_fields.append(field)
            elif any(keyword in field_lower for keyword in ['nhiệt độ', 'temp']):
                numeric_fields.append(field)
        
        # Field detection done
        
        # Kiểm tra chất lượng dữ liệu
        data_warning = ""
        if self.data:
            # Kiểm tra biến thiên độ sâu
            depths = []
            velocities = []
            for point in self.data:
                try:
                    if self.depth_field and self.depth_field in point:
                        depth_val = float(point[self.depth_field])
                        depths.append(depth_val)
                    if self.velocity_field and self.velocity_field in point:
                        vel_val = float(point[self.velocity_field])
                        velocities.append(vel_val)
                except (ValueError, TypeError):
                    continue
            
            if depths and velocities:
                depth_range = max(depths) - min(depths)
                velocity_range = max(velocities) - min(velocities)
                
                if depth_range < 0.001:
                    data_warning += " [CẢNH BÁO: Độ sâu không thay đổi]"
                if velocity_range < 0.001:
                    data_warning += " [CẢNH BÁO: Vận tốc = 0 (thiết bị dừng)]"
        
        # Cập nhật thông tin dữ liệu
        self.lbl_data_info.setText(
            f"Tổng số điểm: {len(self.data)} | "
            f"Trường dữ liệu: {', '.join(numeric_fields[:3])}"
            f"{'...' if len(numeric_fields) > 3 else ''}"
            f"{data_warning}"
        )
        
        # Cập nhật thanh trượt
        self.slider.setMaximum(len(self.data) - 1)
        
        # Vẽ biểu đồ ban đầu
        self._update_chart()
    
    def _update_chart(self):
        """Cập nhật biểu đồ với dữ liệu hiện tại"""
        if not self.data or self.current_index >= len(self.data):
            return
        
        # Lấy dữ liệu từ đầu đến điểm hiện tại để hiển thị đường cong
        current_data = self.data[:self.current_index + 1]
        
        # Tạo dữ liệu cho biểu đồ
        depth = []
        velocity = []
        states = []
        
        for i, point in enumerate(current_data):
            try:
                depth_val = None
                vel_val = None
                state_val = "Dừng"  # default
                
                # Extract depth
                if self.depth_field and self.depth_field in point:
                    depth_raw = point.get(self.depth_field, 0)
                    if isinstance(depth_raw, str):
                        depth_val = float(depth_raw) if depth_raw.strip() else 0.0
                    else:
                        depth_val = float(depth_raw)
                
                # Extract velocity
                if self.velocity_field and self.velocity_field in point:
                    vel_raw = point.get(self.velocity_field, 0)
                    if isinstance(vel_raw, str):
                        vel_val = float(vel_raw) if vel_raw.strip() else 0.0
                    else:
                        vel_val = float(vel_raw)
                
                # Last point processed
                
                # Extract state if available, otherwise derive from velocity
                if 'state' in point:
                    state_val = point.get('state', 'Dừng')
                elif vel_val is not None:
                    if abs(vel_val) < 0.01:  # Very low velocity
                        state_val = "Dừng"
                    elif vel_val < 0:
                        state_val = "Rút cần"
                    else:
                        state_val = "Khoan"
                
                # Only add if we have valid depth and velocity
                if depth_val is not None and vel_val is not None:
                    depth.append(depth_val)
                    velocity.append(vel_val)
                    states.append(state_val)
                    
            except (ValueError, TypeError):
                continue
        
        # Cập nhật biểu đồ
        if depth and velocity:
            
            # Kiểm tra xem dữ liệu có đủ biến thiên không
            depth_range = max(depth) - min(depth)
            velocity_range = max(velocity) - min(velocity)
            
            # Keep silent on minor ranges in UI dialog
            
            self.chart_widget.update_main_plot(depth, velocity, states)
            
            # Tạo time series cho các biểu đồ thời gian
            time_series = list(range(len(depth)))  # Thời gian giả định (giây)
            
            # Cập nhật các biểu đồ thời gian
            self.chart_widget.update_time_plots(time_series, depth, velocity, states)
            
            # Cập nhật histogram
            self.chart_widget.update_histogram(velocity)
        else:
            # No valid data for chart update
            pass
        
        # Cập nhật thông tin điểm hiện tại
        self.lbl_current_point.setText(
            f"Điểm hiện tại: {self.current_index + 1}/{len(self.data)} | "
            f"Độ sâu: {depth[-1] if depth else 'N/A'} m | "
            f"Vận tốc: {velocity[-1] if velocity else 'N/A'} m/s"
        )
        
        # Cập nhật thanh trượt (không phát sinh signal để tránh dừng playback)
        self.slider.blockSignals(True)
        self.slider.setValue(self.current_index)
        self.slider.blockSignals(False)
        
        # Cập nhật tiến trình
        self._update_progress_display()
    
    def _update_progress_display(self):
        """Cập nhật hiển thị tiến trình (số điểm dữ liệu)"""
        if not self.data:
            return
        
        # Hiển thị số điểm dữ liệu hiện tại / tổng số điểm
        self.lbl_progress.setText(f"{self.current_index + 1} / {len(self.data)}")
    
    def _toggle_playback(self):
        """Bật/tắt chế độ phát lại"""
        if not self.data:
            return
        
        if self.is_playing:
            # Dừng phát lại
            self.timer.stop()
            self.btn_play.setText("▶ Tiếp tục")
            self.is_playing = False
        else:
            # Bắt đầu phát lại
            # Tính interval dựa trên tốc độ phát lại
            interval = int(1000 / (self.points_per_second * self.playback_speed))
            self.timer.setInterval(interval)
            self.timer.start()
            self.btn_play.setText("⏸ Tạm dừng")
            self.is_playing = True
            
            # Nếu đã đến cuối, quay lại đầu
            if self.current_index >= len(self.data) - 1:
                self.current_index = 0
                self._update_chart()
    
    def _on_timer_timeout(self):
        """Xử lý sự kiện hẹn giờ cho phát lại"""
        if not self.data or self.current_index >= len(self.data) - 1:
            self.timer.stop()
            self.is_playing = False
            self.btn_play.setText("▶ Bắt đầu lại")
            return
        
        # Tăng chỉ số điểm dữ liệu
        self.current_index += 1
        self._update_chart()
    
    def _on_slider_moved(self, value):
        """Xử lý khi người dùng di chuyển thanh trượt"""
        if not self.data:
            return
        
        # Cập nhật chỉ số hiện tại
        self.current_index = min(max(0, value), len(self.data) - 1)
        
        # Nếu đang phát, tạm dừng
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.btn_play.setText("▶ Tiếp tục")
        
        # Cập nhật biểu đồ
        self._update_chart()
    
    def _change_playback_speed(self):
        """Thay đổi tốc độ phát lại"""
        # Danh sách các tốc độ có sẵn
        speeds = [0.5, 1.0, 2.0, 5.0, 10.0]
        current_idx = speeds.index(self.playback_speed) if self.playback_speed in speeds else 1
        next_idx = (current_idx + 1) % len(speeds)
        
        self.playback_speed = speeds[next_idx]
        self.btn_speed.setText(f"Tốc độ: {self.playback_speed}x")
        
        # Cập nhật tốc độ nếu đang phát
        if self.is_playing:
            interval = int(1000 / (self.points_per_second * self.playback_speed))
            self.timer.setInterval(interval)
    
    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ"""
        # Dừng timer khi đóng cửa sổ
        self.timer.stop()
        super().closeEvent(event)
 
