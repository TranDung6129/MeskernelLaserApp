"""
Geotech Stats - Bảng thống kê cho Geotech Panel
Chứa widget bảng thống kê và logic tính toán các chỉ số
"""
from typing import Dict, Any, List
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QStyledItemDelegate
)

from .geotech_utils import GeotechUtils


class ColumnSeparatorDelegate(QStyledItemDelegate):
    """Vẽ đường kẻ phân cách dọc ở bên phải cột 0 để ngăn cách hai cột."""

    def __init__(self, parent=None, color: QColor | None = None, thickness: int = 1):
        super().__init__(parent)
        self._color = color or QColor(208, 208, 208)
        self._thickness = thickness

    def paint(self, painter, option, index):  # type: ignore[override]
        # Vẽ nội dung mặc định
        super().paint(painter, option, index)
        # Chỉ vẽ separator cho cột 0
        if index.column() == 0:
            painter.save()
            painter.setPen(QPen(self._color, self._thickness))
            x = option.rect.right()
            painter.drawLine(x, option.rect.top(), x, option.rect.bottom())
            painter.restore()


class GeotechStatsWidget(QWidget):
    """Widget bảng thống kê cho Geotech Panel"""
    
    def __init__(self):
        super().__init__()
        self.depth_unit = "m"
        self.velocity_unit = "m/s"
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Bảng thông số
        stats_group = QGroupBox("Thông số khoan")
        try:
            stats_group.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Thông số", "Giá trị"])
        
        self.stats_rows = {
            "current_depth": ("Độ sâu hiện tại", "m"),
            "max_depth": ("Độ sâu tối đa", "m"),
            "current_velocity": ("Vận tốc hiện tại", "m/s"), 
            "avg_velocity": ("Vận tốc TB", "m/s"),
            "min_velocity": ("Vận tốc min", "m/s"),
            "max_velocity": ("Vận tốc max", "m/s"),
            "state": ("Trạng thái", ""),
            "time_drilling_s": ("TG khoan", "s"),
            "time_stopped_s": ("TG dừng", "s"),
            "efficiency_percent": ("Hiệu suất", "%"),
            "velocity_threshold": ("Ngưỡng v", "m/s"),
            "total_samples": ("Số mẫu", "")
        }
        
        self.stats_table.setRowCount(len(self.stats_rows))
        for i, (key, (label, unit)) in enumerate(self.stats_rows.items()):
            # Tạo tên cột với đơn vị nếu có
            display_label = f"{label} ({unit})" if unit else label
            
            name_item = QTableWidgetItem(display_label)
            value_item = QTableWidgetItem("--")
            # Căn chỉnh để cân đối hiển thị
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            name_item.setToolTip(display_label)
            value_item.setToolTip("--")
            self.stats_table.setItem(i, 0, name_item)
            self.stats_table.setItem(i, 1, value_item)

        # Cân đối bảng: cột tên hẹp hơn, cột giá trị rộng hơn
        header = self.stats_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # Đặt chiều rộng tối đa cho cột thông số
        self.stats_table.setColumnWidth(0, 120)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        try:
            header.resizeSection(0, 180)
            # Tránh elide tiêu đề cột
            header.setTextElideMode(Qt.TextElideMode.ElideNone)
            header.setMinimumSectionSize(120)
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        except Exception:
            pass
        
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #e6f3ff;
            }
        """)
        self.stats_table.setShowGrid(False)
        self.stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.stats_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stats_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stats_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stats_table.setWordWrap(True)
        
        # Gắn delegate để vẽ đường phân cách giữa hai cột
        self.stats_table.setItemDelegate(ColumnSeparatorDelegate(self.stats_table))
        
        # Tự động giãn hàng theo nội dung để hiển thị đẹp trên màn hình ban đầu
        try:
            self.stats_table.resizeRowsToContents()
            total_h = header.height()
            for i in range(self.stats_table.rowCount()):
                total_h += self.stats_table.rowHeight(i)
            self.stats_table.setFixedHeight(total_h + 6)
        except Exception:
            pass
        
        stats_layout.addWidget(self.stats_table)
        layout.addWidget(stats_group)
    
    def update_units(self, depth_unit: str, velocity_unit: str):
        """Cập nhật đơn vị đo"""
        self.depth_unit = depth_unit
        self.velocity_unit = velocity_unit
        self._update_labels()
    
    def _update_labels(self):
        """Cập nhật labels của bảng thống kê theo đơn vị mới"""
        new_labels = {
            "current_depth": f"Độ sâu hiện tại ({self.depth_unit})",
            "max_depth": f"Độ sâu tối đa ({self.depth_unit})",
            "current_velocity": f"Vận tốc hiện tại ({self.velocity_unit})",
            "avg_velocity": f"Vận tốc TB ({self.velocity_unit})",
            "min_velocity": f"Vận tốc min ({self.velocity_unit})",
            "max_velocity": f"Vận tốc max ({self.velocity_unit})",
            "state": "Trạng thái",
            "time_drilling_s": "TG khoan (s)",
            "time_stopped_s": "TG dừng (s)",
            "efficiency_percent": "Hiệu suất (%)",
            "velocity_threshold": f"Ngưỡng v ({self.velocity_unit})",
            "total_samples": "Số mẫu"
        }
        
        for i, (key, (old_label, unit)) in enumerate(self.stats_rows.items()):
            if key in new_labels:
                # Update the tuple in stats_rows to maintain structure
                self.stats_rows[key] = (new_labels[key].split(' (')[0], unit)
                item = self.stats_table.item(i, 0)
                if item:
                    item.setText(new_labels[key])
    
    def update_stats(self, depth_series: List[float], velocity_series: List[float], 
                    state_series: List[str], velocity_threshold: float = 0.005):
        """Cập nhật bảng thống kê với dữ liệu mới"""
        try:
            # Nếu không có dữ liệu, hiển thị giá trị mặc định
            if not depth_series or not velocity_series:
                self._reset_to_default()
                return
                
            # Tính toán thống kê cơ bản
            basic_stats = GeotechUtils.calculate_stats(
                depth_series, velocity_series, state_series, 
                self.depth_unit, self.velocity_unit
            )
            
            # Thêm threshold
            basic_stats["velocity_threshold"] = GeotechUtils.convert_velocity_value(
                velocity_threshold, self.velocity_unit
            )
            
            # Cập nhật giá trị trong bảng
            for i, (key, _) in enumerate(self.stats_rows.items()):
                item = self.stats_table.item(i, 1)
                if item and key in basic_stats:
                    if key in ["current_depth", "max_depth", "current_velocity", 
                              "avg_velocity", "min_velocity", "max_velocity", "velocity_threshold"]:
                        text_val = f"{basic_stats[key]:.3f}"
                    elif key == "total_samples":
                        text_val = str(basic_stats[key])
                    else:
                        text_val = str(basic_stats[key])
                    
                    item.setText(text_val)
                    
                    # Tô màu theo trạng thái
                    if key == "state":
                        stl = (text_val or "").lower()
                        if stl.startswith('khoan'):
                            item.setBackground(QColor(200, 255, 200))
                        elif ('rút' in stl) or ('rut' in stl):
                            item.setBackground(QColor(255, 230, 180))
                        elif stl:
                            item.setBackground(QColor(255, 200, 200))
                        else:
                            item.setBackground(QColor(255, 255, 255))
                    else:
                        # Các ô khác dùng màu nền trắng
                        item.setBackground(QColor(255, 255, 255))
            
            # Tự động giãn hàng theo nội dung và cập nhật chiều cao bảng
            self.stats_table.resizeRowsToContents()
            header = self.stats_table.horizontalHeader()
            total_h = header.height()
            for i in range(self.stats_table.rowCount()):
                total_h += self.stats_table.rowHeight(i)
            self.stats_table.setFixedHeight(total_h + 6)
            
        except Exception as e:
            print(f"GeotechStatsWidget update error: {e}")
    
    def _reset_to_default(self):
        """Reset tất cả giá trị về '--' và xóa màu nền"""
        for i in range(len(self.stats_rows)):
            item = self.stats_table.item(i, 1)
            if item:
                item.setText("--")
                item.setBackground(QColor(255, 255, 255))  # Màu nền trắng
                item.setToolTip("--")
    
    def update_statistics_from_processor(self, stats: Dict[str, Any]):
        """Cập nhật thống kê từ DataProcessor"""
        try:
            # Mapping cho các giá trị từ processor
            mapping = {
                "time_drilling_s": lambda v: f"{float(v):.1f}",
                "time_stopped_s": lambda v: f"{float(v):.1f}",
                "efficiency_percent": lambda v: f"{float(v):.1f}",
                "state": lambda v: str(v),
            }
            
            for i, (key, _) in enumerate(self.stats_rows.items()):
                if key in mapping and key in stats:
                    item = self.stats_table.item(i, 1)
                    if item:
                        text_val = mapping[key](stats[key])
                        item.setText(text_val)
                        
                        # Tô màu theo trạng thái
                        if key == 'state':
                            stl = (text_val or "").lower()
                            if stl.startswith('khoan'):
                                item.setBackground(QColor(200, 255, 200))
                            elif ('rút' in stl) or ('rut' in stl):
                                item.setBackground(QColor(255, 230, 180))
                            elif stl:
                                item.setBackground(QColor(255, 200, 200))
                            else:
                                item.setBackground(QColor(255, 255, 255))
                        else:
                            # Các ô khác từ processor cũng dùng màu nền trắng
                            item.setBackground(QColor(255, 255, 255))
        except Exception:
            pass