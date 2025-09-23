"""
Geotech Charts - Các widget đồ thị cho Geotech Panel
Chứa main plot, subplots và histogram
"""
from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, 
    QLabel, QSplitter, QComboBox, QSizePolicy
)

import pyqtgraph as pg
import numpy as np

from .geotech_utils import GeotechUtils


class GeotechChartsWidget(QWidget):
    """Widget chứa tất cả các đồ thị cho Geotech Panel"""
    
    def __init__(self):
        super().__init__()
        self.depth_unit = "m"
        self.velocity_unit = "m/s"
        self._velocity_threshold: float = 0.005
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Khu vực đồ thị chính
        chart_container = QWidget()
        chart_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)

        # Main plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Độ sâu', units='m', angle=0)
        self.plot_widget.setLabel('bottom', 'Vận tốc', units='m/s')
        self.plot_widget.setTitle('Vận tốc theo độ sâu (Khoan địa chất)', color='k', size='12pt')
        
        # Bật zoom và pan
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange()
        
        self.plot_widget.setMinimumHeight(300)
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        try:
            # Quay ngược đồ thị: để độ sâu tăng dần theo trục Y hướng xuống dưới
            self.plot_widget.getViewBox().invertY(True)
            axis_left = self.plot_widget.getAxis('left')
            axis_bottom = self.plot_widget.getAxis('bottom')
            small_font = QFont('Arial', 9)
            axis_left.setStyle(tickFont=small_font, autoExpandTextSpace=True, tickTextOffset=12)
            axis_bottom.setStyle(tickFont=small_font, autoExpandTextSpace=True, tickTextOffset=12)
            axis_left.setWidth(120)
            axis_bottom.setHeight(48)
        except Exception:
            pass

        # Đường cong theo trạng thái
        self.line_drill = self.plot_widget.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2), name='Khoan')
        self.line_stop = self.plot_widget.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2), name='Dừng')
        self.line_retract = self.plot_widget.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2), name='Rút cần')
        
        # Legend cho trạng thái
        try:
            legend = self.plot_widget.addLegend()
            legend.addItem(self.line_drill, 'Khoan')
            legend.addItem(self.line_stop, 'Dừng')
            legend.addItem(self.line_retract, 'Rút cần')
        except Exception:
            pass

        # Thanh công cụ
        toolbar = QHBoxLayout()
        
        self.cb_autoscale = QCheckBox("Auto scale")
        self.cb_autoscale.setChecked(True)
        self.cb_autoscale.toggled.connect(self._on_autoscale_toggled)
        
        self.btn_clear_data = QPushButton("Xóa dữ liệu")
        self.btn_clear_data.clicked.connect(self._clear_data)
        
        
        # Đơn vị đo
        self.lbl_depth_unit = QLabel("Độ sâu:")
        self.combo_depth_unit = QComboBox()
        self.combo_depth_unit.addItems(["m", "cm", "mm"])
        self.combo_depth_unit.setCurrentText(self.depth_unit)
        self.combo_depth_unit.currentTextChanged.connect(self._on_depth_unit_changed)
        
        self.lbl_velocity_unit = QLabel("Vận tốc:")
        self.combo_velocity_unit = QComboBox()
        self.combo_velocity_unit.addItems(["m/s", "cm/s", "mm/s"])
        self.combo_velocity_unit.setCurrentText(self.velocity_unit)
        self.combo_velocity_unit.currentTextChanged.connect(self._on_velocity_unit_changed)
        
        self.lbl_current = QLabel("Độ sâu: -- m | Vận tốc: -- m/s")
        self.lbl_current.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        
        toolbar.addWidget(self.lbl_current)
        toolbar.addStretch()
        toolbar.addWidget(self.lbl_depth_unit)
        toolbar.addWidget(self.combo_depth_unit)
        toolbar.addWidget(self.lbl_velocity_unit)
        toolbar.addWidget(self.combo_velocity_unit)
        toolbar.addWidget(self.cb_autoscale)
        toolbar.addWidget(self.btn_clear_data)

        chart_layout.addLayout(toolbar)
        chart_layout.addWidget(self.plot_widget, stretch=3)
        
        # Double-click để mở cửa sổ riêng
        self.plot_widget.mouseDoubleClickEvent = lambda event: self._popout_plot(self.plot_widget, "Velocity-Depth")

        # Subplots splitter
        self.subplots_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.subplots_splitter.setMinimumHeight(200)
        self.subplots_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Depth vs Time plot
        self.depth_time_plot = pg.PlotWidget()
        self.depth_time_plot.setBackground('w')
        self.depth_time_plot.showGrid(x=True, y=True)
        self.depth_time_plot.setLabel('left', 'Độ sâu', units='m')
        self.depth_time_plot.setLabel('bottom', 'Thời gian', units='s')
        self.depth_time_plot.setTitle('Độ sâu theo thời gian')
        self.depth_time_plot.setMinimumWidth(200)
        self.depth_time_plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.depth_time_plot.setMouseEnabled(x=True, y=True)
        
        self.depth_time_curve_drill = self.depth_time_plot.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2))
        self.depth_time_curve_stop = self.depth_time_plot.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2))
        self.depth_time_curve_retract = self.depth_time_plot.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2))
        
        try:
            legend_dt = self.depth_time_plot.addLegend()
            legend_dt.addItem(self.depth_time_curve_drill, 'Khoan')
            legend_dt.addItem(self.depth_time_curve_stop, 'Dừng')
            legend_dt.addItem(self.depth_time_curve_retract, 'Rút cần')
        except Exception:
            pass
        
        try:
            self.depth_time_plot.getViewBox().invertY(True)
        except Exception:
            pass
        
        self.subplots_splitter.addWidget(self.depth_time_plot)
        self.depth_time_plot.mouseDoubleClickEvent = lambda event: self._popout_plot(self.depth_time_plot, "Depth-Time")

        # Velocity vs Time plot
        self.velocity_time_plot = pg.PlotWidget()
        self.velocity_time_plot.setBackground('w')
        self.velocity_time_plot.showGrid(x=True, y=True)
        self.velocity_time_plot.setLabel('left', 'Vận tốc', units='m/s')
        self.velocity_time_plot.setLabel('bottom', 'Thời gian', units='s')
        self.velocity_time_plot.setTitle('Vận tốc theo thời gian')
        self.velocity_time_plot.setMinimumWidth(200)
        self.velocity_time_plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.velocity_time_plot.setMouseEnabled(x=True, y=True)
        
        self.velocity_time_curve_drill = self.velocity_time_plot.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2))
        self.velocity_time_curve_stop = self.velocity_time_plot.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2))
        self.velocity_time_curve_retract = self.velocity_time_plot.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2))
        
        try:
            legend_vt = self.velocity_time_plot.addLegend()
            legend_vt.addItem(self.velocity_time_curve_drill, 'Khoan')
            legend_vt.addItem(self.velocity_time_curve_stop, 'Dừng')
            legend_vt.addItem(self.velocity_time_curve_retract, 'Rút cần')
        except Exception:
            pass
        
        # Threshold lines
        self.vel_thr_pos = pg.InfiniteLine(angle=0, pos=self._velocity_threshold, pen=pg.mkPen(color=(0, 160, 0), style=Qt.PenStyle.DashLine))
        self.vel_thr_neg = pg.InfiniteLine(angle=0, pos=-self._velocity_threshold, pen=pg.mkPen(color=(200, 0, 0), style=Qt.PenStyle.DashLine))
        self.velocity_time_plot.addItem(self.vel_thr_pos)
        self.velocity_time_plot.addItem(self.vel_thr_neg)
        
        self.subplots_splitter.addWidget(self.velocity_time_plot)
        self.velocity_time_plot.mouseDoubleClickEvent = lambda event: self._popout_plot(self.velocity_time_plot, "Velocity-Time")

        # Velocity histogram
        self.hist_plot = pg.PlotWidget()
        self.hist_plot.setBackground('w')
        self.hist_plot.showGrid(x=True, y=True)
        self.hist_plot.setLabel('left', 'Tần suất')
        self.hist_plot.setLabel('bottom', 'Vận tốc', units='m/s')
        self.hist_plot.setTitle('Phân bố vận tốc')
        self.hist_plot.setMinimumWidth(200)
        self.hist_plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hist_plot.setMouseEnabled(x=True, y=True)
        
        self._hist_bar = None
        self.subplots_splitter.addWidget(self.hist_plot)
        self.hist_plot.mouseDoubleClickEvent = lambda event: self._popout_plot(self.hist_plot, "Velocity-Histogram")

        chart_layout.addWidget(self.subplots_splitter, stretch=2)
        
        # Thiết lập tỷ lệ cho subplots_splitter
        self.subplots_splitter.setSizes([400, 400, 400])
        self.subplots_splitter.setStretchFactor(0, 1)  # Depth-Time
        self.subplots_splitter.setStretchFactor(1, 1)  # Velocity-Time
        self.subplots_splitter.setStretchFactor(2, 1)  # Histogram
        
        layout.addWidget(chart_container)
    
    def _on_autoscale_toggled(self, checked: bool):
        """Xử lý khi thay đổi tùy chọn autoscale"""
        if checked:
            self.plot_widget.enableAutoRange()
        else:
            self.plot_widget.disableAutoRange()
    
    def _on_depth_unit_changed(self, new_unit: str):
        """Xử lý khi thay đổi đơn vị độ sâu"""
        self.depth_unit = new_unit
        self._update_plot_labels()
        if hasattr(self, 'on_units_changed'):
            self.on_units_changed(self.depth_unit, self.velocity_unit)
    
    def _on_velocity_unit_changed(self, new_unit: str):
        """Xử lý khi thay đổi đơn vị vận tốc"""
        self.velocity_unit = new_unit
        self._update_plot_labels()
        if hasattr(self, 'on_units_changed'):
            self.on_units_changed(self.depth_unit, self.velocity_unit)
    
    def _update_plot_labels(self):
        """Cập nhật labels của các plot theo đơn vị mới"""
        try:
            self.plot_widget.setLabel('left', 'Độ sâu', units=self.depth_unit)
            self.plot_widget.setLabel('bottom', 'Vận tốc', units=self.velocity_unit)
            
            self.depth_time_plot.setLabel('left', 'Độ sâu', units=self.depth_unit)
            self.velocity_time_plot.setLabel('left', 'Vận tốc', units=self.velocity_unit)
            self.hist_plot.setLabel('bottom', 'Vận tốc', units=self.velocity_unit)
        except Exception:
            pass
    
    
    def _clear_data(self):
        """Xóa toàn bộ dữ liệu đang sử dụng để hiển thị trên đồ thị"""
        # Xóa tất cả đồ thị
        self.line_drill.setData([], [])
        self.line_stop.setData([], [])
        self.line_retract.setData([], [])
        
        self.depth_time_curve_drill.setData([], [])
        self.depth_time_curve_stop.setData([], [])
        self.depth_time_curve_retract.setData([], [])
        
        self.velocity_time_curve_drill.setData([], [])
        self.velocity_time_curve_stop.setData([], [])
        self.velocity_time_curve_retract.setData([], [])
        
        if self._hist_bar is not None:
            try:
                self.hist_plot.removeItem(self._hist_bar)
            except Exception:
                pass
            self._hist_bar = None
        
        # Reset giá trị hiện tại
        self.lbl_current.setText("Độ sâu: -- m | Vận tốc: -- m/s")
        
        if self.cb_autoscale.isChecked():
            self.plot_widget.enableAutoRange()
        else:
            self.plot_widget.disableAutoRange()
        
        # Thông báo cho parent để xóa dữ liệu gốc
        if hasattr(self, 'on_data_cleared'):
            self.on_data_cleared()
    
    def _popout_plot(self, source_widget: pg.PlotWidget, title: str):
        """Mở cửa sổ popout cho đồ thị"""
        if hasattr(self, 'on_popout_requested'):
            self.on_popout_requested(source_widget, title)
    
    def update_current_values(self, depth_m: float, velocity_ms: float):
        """Cập nhật giá trị hiện tại trên toolbar"""
        converted_depth = GeotechUtils.convert_depth_value(depth_m, self.depth_unit)
        converted_velocity = GeotechUtils.convert_velocity_value(velocity_ms, self.velocity_unit)
        self.lbl_current.setText(f"Độ sâu: {converted_depth:.3f} {self.depth_unit} | Vận tốc: {converted_velocity:.3f} {self.velocity_unit}")
    
    def update_velocity_threshold(self, threshold: float):
        """Cập nhật ngưỡng vận tốc"""
        self._velocity_threshold = threshold
        converted_thr = GeotechUtils.convert_velocity_value(threshold, self.velocity_unit)
        self.vel_thr_pos.setValue(converted_thr)
        self.vel_thr_neg.setValue(-converted_thr)
    
    def update_main_plot(self, depth_series: List[float], velocity_series: List[float], 
                        state_series: List[str]):
        """Cập nhật đồ thị chính"""
        if not depth_series or not velocity_series:
            self.line_drill.setData([], [])
            self.line_stop.setData([], [])
            self.line_retract.setData([], [])
            return
        
        # Tách dữ liệu theo trạng thái
        separated_data = GeotechUtils.separate_data_by_state(
            depth_series, velocity_series, state_series, 
            self.depth_unit, self.velocity_unit
        )
        
        # Cập nhật các đường
        self.line_drill.setData(separated_data['drill']['velocity'], separated_data['drill']['depth'])
        self.line_stop.setData(separated_data['stop']['velocity'], separated_data['stop']['depth'])
        self.line_retract.setData(separated_data['retract']['velocity'], separated_data['retract']['depth'])
        
        if self.cb_autoscale.isChecked():
            self.plot_widget.enableAutoRange()
        else:
            self.plot_widget.disableAutoRange()
    
    def update_time_plots(self, time_series: List[float], depth_series: List[float], 
                         velocity_series: List[float], state_series: List[str]):
        """Cập nhật các đồ thị thời gian"""
        if not time_series or not depth_series or not velocity_series:
            self.depth_time_curve_drill.setData([], [])
            self.depth_time_curve_stop.setData([], [])
            self.depth_time_curve_retract.setData([], [])
            self.velocity_time_curve_drill.setData([], [])
            self.velocity_time_curve_stop.setData([], [])
            self.velocity_time_curve_retract.setData([], [])
            return
        
        # Tách dữ liệu theo trạng thái
        separated_data = GeotechUtils.separate_time_data_by_state(
            time_series, depth_series, velocity_series, state_series,
            self.depth_unit, self.velocity_unit
        )
        
        # Cập nhật depth-time plot
        self.depth_time_curve_drill.setData(separated_data['drill']['time'], separated_data['drill']['depth'])
        self.depth_time_curve_stop.setData(separated_data['stop']['time'], separated_data['stop']['depth'])
        self.depth_time_curve_retract.setData(separated_data['retract']['time'], separated_data['retract']['depth'])
        
        # Cập nhật velocity-time plot
        self.velocity_time_curve_drill.setData(separated_data['drill']['time'], separated_data['drill']['velocity'])
        self.velocity_time_curve_stop.setData(separated_data['stop']['time'], separated_data['stop']['velocity'])
        self.velocity_time_curve_retract.setData(separated_data['retract']['time'], separated_data['retract']['velocity'])
        
        if self.cb_autoscale.isChecked():
            self.depth_time_plot.enableAutoRange()
            self.velocity_time_plot.enableAutoRange()
        else:
            self.depth_time_plot.disableAutoRange()
            self.velocity_time_plot.disableAutoRange()
    
    def update_histogram(self, velocity_series: List[float]):
        """Cập nhật histogram"""
        if not velocity_series:
            if self._hist_bar is not None:
                try:
                    self.hist_plot.removeItem(self._hist_bar)
                except Exception:
                    pass
                self._hist_bar = None
            return
        
        # Tính toán dữ liệu histogram
        centers, counts, width = GeotechUtils.calculate_histogram_data(
            velocity_series, self.velocity_unit
        )
        
        if centers is None:
            return
        
        # Xóa histogram cũ
        if self._hist_bar is not None:
            try:
                self.hist_plot.removeItem(self._hist_bar)
            except Exception:
                pass
        
        # Tạo histogram mới
        self._hist_bar = pg.BarGraphItem(
            x=centers, height=counts, width=width, 
            brush=pg.mkBrush(120, 160, 240, 180)
        )
        self.hist_plot.addItem(self._hist_bar)
        
        # Cập nhật label trục x
        self.hist_plot.setLabel('bottom', 'Vận tốc', units=self.velocity_unit)
    
    def update_preview(self, depth_m: float, velocity_ms: float, state: Optional[str]):
        """Cập nhật preview điểm gần nhất"""
        converted_vel = GeotechUtils.convert_velocity_value(velocity_ms, self.velocity_unit)
        converted_dep = GeotechUtils.convert_depth_value(depth_m, self.depth_unit)
        
        # Vẽ preview theo trạng thái
        stl = (state or "").lower()
        if stl.startswith('khoan'):
            self.line_drill.setData([converted_vel], [converted_dep])
            self.line_stop.setData([], [])
            self.line_retract.setData([], [])
        elif ('rút' in stl) or ('rut' in stl):
            self.line_retract.setData([converted_vel], [converted_dep])
            self.line_drill.setData([], [])
            self.line_stop.setData([], [])
        else:
            self.line_stop.setData([converted_vel], [converted_dep])
            self.line_drill.setData([], [])
            self.line_retract.setData([], [])
        
        if self.cb_autoscale.isChecked():
            self.plot_widget.enableAutoRange()
        else:
            self.plot_widget.disableAutoRange()
    
    def get_units(self) -> tuple:
        """Lấy đơn vị hiện tại"""
        return self.depth_unit, self.velocity_unit
