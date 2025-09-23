"""
Geotech Popout - Logic popout windows cho Geotech Panel
Chứa các cửa sổ popout để hiển thị đồ thị riêng biệt
"""
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout

import pyqtgraph as pg

from .geotech_utils import GeotechUtils


class GeotechPopoutManager:
    """Quản lý các cửa sổ popout cho Geotech Panel"""
    
    def __init__(self):
        self.popout_windows: List[Dict[str, Any]] = []
    
    def create_popout_window(self, parent, source_widget: pg.PlotWidget, title: str, 
                           depth_unit: str = "m", velocity_unit: str = "m/s") -> Optional[Dict[str, Any]]:
        """Tạo cửa sổ popout mới"""
        try:
            # Custom dialog class để xử lý close event
            class PopoutWindow(QDialog):
                def __init__(self, parent, popout_manager):
                    super().__init__(parent)
                    self.popout_manager = popout_manager
                
                def closeEvent(self, event):
                    # Xóa khỏi danh sách popout windows
                    self.popout_manager.popout_windows = [
                        w for w in self.popout_manager.popout_windows if w['window'] != self
                    ]
                    event.accept()
            
            win = PopoutWindow(parent, self)
            win.setWindowTitle(f"{title} - Geotech (Realtime)")
            layout = QVBoxLayout(win)
            
            # Tạo plot mới
            new_plot = pg.PlotWidget()
            new_plot.setBackground('w')
            new_plot.showGrid(x=True, y=True)
            
            # Copy labels/titles với đơn vị hiện tại
            try:
                if title == "Velocity-Depth":
                    new_plot.setLabel('left', 'Độ sâu', units=depth_unit)
                    new_plot.setLabel('bottom', 'Vận tốc', units=velocity_unit)
                    new_plot.getViewBox().invertY(True)
                elif title == "Depth-Time":
                    new_plot.setLabel('left', 'Độ sâu', units=depth_unit)
                    new_plot.setLabel('bottom', 'Thời gian', units='s')
                    new_plot.getViewBox().invertY(True)
                elif title == "Velocity-Time":
                    new_plot.setLabel('left', 'Vận tốc', units=velocity_unit)
                    new_plot.setLabel('bottom', 'Thời gian', units='s')
                elif title == "Velocity-Histogram":
                    new_plot.setLabel('left', 'Tần suất')
                    new_plot.setLabel('bottom', 'Vận tốc', units=velocity_unit)
                new_plot.setTitle(f"{title} ({depth_unit}, {velocity_unit})")
            except Exception:
                pass
            
            # Tạo cấu trúc tương ứng với từng loại plot
            plot_info = {'window': win, 'plot': new_plot, 'title': title, 'items': {}}
            
            if title == "Velocity-Depth":
                # Tạo line items tương ứng
                plot_info['items']['line_drill'] = new_plot.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2), name='Khoan')
                plot_info['items']['line_stop'] = new_plot.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2), name='Dừng')
                plot_info['items']['line_retract'] = new_plot.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2), name='Rút cần')
                
            elif title == "Depth-Time":
                plot_info['items']['curve_drill'] = new_plot.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2))
                plot_info['items']['curve_stop'] = new_plot.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2))
                plot_info['items']['curve_retract'] = new_plot.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2))
                
            elif title == "Velocity-Time":
                plot_info['items']['curve_drill'] = new_plot.plot([], [], pen=pg.mkPen(color=(0, 150, 0), width=2))
                plot_info['items']['curve_stop'] = new_plot.plot([], [], pen=pg.mkPen(color=(200, 0, 0), width=2))
                plot_info['items']['curve_retract'] = new_plot.plot([], [], pen=pg.mkPen(color=(240, 160, 0), width=2))
                # Thêm threshold lines với đơn vị chuyển đổi
                converted_thr = GeotechUtils.convert_velocity_value(0.005, velocity_unit)  # Default threshold
                vel_thr_pos = pg.InfiniteLine(angle=0, pos=converted_thr, pen=pg.mkPen(color=(0, 160, 0), style=Qt.PenStyle.DashLine))
                vel_thr_neg = pg.InfiniteLine(angle=0, pos=-converted_thr, pen=pg.mkPen(color=(200, 0, 0), style=Qt.PenStyle.DashLine))
                new_plot.addItem(vel_thr_pos)
                new_plot.addItem(vel_thr_neg)
                plot_info['items']['thr_pos'] = vel_thr_pos
                plot_info['items']['thr_neg'] = vel_thr_neg
                
            elif title == "Velocity-Histogram":
                plot_info['items']['hist_bar'] = None  # Sẽ được tạo khi có dữ liệu
            
            layout.addWidget(new_plot)
            self.popout_windows.append(plot_info)
            win.resize(900, 600)
            win.show()
            
            return plot_info
            
        except Exception as e:
            print(f"Popout creation error: {e}")
            return None
    
    def update_popout_windows(self, depth_series: List[float], velocity_series: List[float], 
                            time_series: List[float], state_series: List[str], 
                            depth_unit: str = "m", velocity_unit: str = "m/s", 
                            velocity_threshold: float = 0.005):
        """Cập nhật tất cả cửa sổ popout với dữ liệu mới nhất"""
        if not self.popout_windows:
            return
            
        for window_info in self.popout_windows[:]:  # Copy list để tránh lỗi khi modify
            try:
                title = window_info['title']
                items = window_info['items']
                
                if title == "Velocity-Depth":
                    # Tách dữ liệu theo trạng thái với đơn vị chuyển đổi
                    separated_data = GeotechUtils.separate_data_by_state(
                        depth_series, velocity_series, state_series, 
                        depth_unit, velocity_unit
                    )
                    
                    items['line_drill'].setData(separated_data['drill']['velocity'], separated_data['drill']['depth'])
                    items['line_stop'].setData(separated_data['stop']['velocity'], separated_data['stop']['depth'])
                    items['line_retract'].setData(separated_data['retract']['velocity'], separated_data['retract']['depth'])
                    
                elif title == "Depth-Time":
                    if time_series and depth_series:
                        separated_data = GeotechUtils.separate_time_data_by_state(
                            time_series, depth_series, velocity_series, state_series,
                            depth_unit, velocity_unit
                        )
                        
                        items['curve_drill'].setData(separated_data['drill']['time'], separated_data['drill']['depth'])
                        items['curve_stop'].setData(separated_data['stop']['time'], separated_data['stop']['depth'])
                        items['curve_retract'].setData(separated_data['retract']['time'], separated_data['retract']['depth'])
                    
                elif title == "Velocity-Time":
                    if time_series and velocity_series:
                        separated_data = GeotechUtils.separate_time_data_by_state(
                            time_series, depth_series, velocity_series, state_series,
                            depth_unit, velocity_unit
                        )
                        
                        items['curve_drill'].setData(separated_data['drill']['time'], separated_data['drill']['velocity'])
                        items['curve_stop'].setData(separated_data['stop']['time'], separated_data['stop']['velocity'])
                        items['curve_retract'].setData(separated_data['retract']['time'], separated_data['retract']['velocity'])
                        
                        # Cập nhật threshold lines với đơn vị chuyển đổi
                        if 'thr_pos' in items and 'thr_neg' in items:
                            converted_thr = GeotechUtils.convert_velocity_value(velocity_threshold, velocity_unit)
                            items['thr_pos'].setValue(converted_thr)
                            items['thr_neg'].setValue(-converted_thr)
                    
                elif title == "Velocity-Histogram":
                    if velocity_series and len(velocity_series) >= 5:
                        import numpy as np
                        
                        # Tính toán dữ liệu histogram
                        centers, counts, width = GeotechUtils.calculate_histogram_data(
                            velocity_series, velocity_unit
                        )
                        
                        if centers is not None:
                            # Xóa histogram cũ nếu có
                            if items['hist_bar'] is not None:
                                try:
                                    window_info['plot'].removeItem(items['hist_bar'])
                                except Exception:
                                    pass
                            
                            # Tạo histogram mới
                            items['hist_bar'] = pg.BarGraphItem(
                                x=centers, height=counts, width=width, 
                                brush=pg.mkBrush(120, 160, 240, 180)
                            )
                            window_info['plot'].addItem(items['hist_bar'])
                        
            except Exception as e:
                print(f"Popout update error: {e}")
                # Xóa window lỗi khỏi danh sách
                self.popout_windows.remove(window_info)
    
    def clear_popout_windows(self):
        """Xóa tất cả cửa sổ popout"""
        for window_info in self.popout_windows:
            try:
                window_info['window'].close()
            except Exception:
                pass
        self.popout_windows.clear()
    
    def get_popout_count(self) -> int:
        """Lấy số lượng cửa sổ popout đang mở"""
        return len(self.popout_windows)
