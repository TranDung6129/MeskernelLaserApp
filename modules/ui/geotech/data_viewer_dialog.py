"""
Data Viewer Dialog - Hiển thị dữ liệu đã lưu dưới dạng bảng
"""
import os
import csv
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QAbstractItemModel
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableView, QFileDialog, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QColor


class PandasModel(QAbstractTableModel):
    """Mô hình dữ liệu cho QTableView, tương thích với dữ liệu dạng danh sách từ điển"""
    
    def __init__(self, data: List[Dict], headers: List[str] = None):
        super().__init__()
        self._data = data
        self._headers = headers or []
        
        # Tự động xác định headers nếu không được cung cấp
        if not self._headers and self._data:
            self._headers = list(self._data[0].keys())
    
    def rowCount(self, parent=None) -> int:
        return len(self._data)
    
    def columnCount(self, parent=None) -> int:
        return len(self._headers) if self._headers else 0
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()
        
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            row = self._data[index.row()]
            header = self._headers[index.column()]
            return str(row.get(header, ''))
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()
        
        if orientation == Qt.Orientation.Horizontal and section < len(self._headers):
            return self._headers[section]
        elif orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        
        return QVariant()
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sắp xếp dữ liệu theo cột"""
        if not self._headers or not self._data:
            return
        
        self.layoutAboutToBeChanged.emit()
        
        try:
            # Lấy key của cột hiện tại
            sort_key = self._headers[column]
            
            # Sắp xếp dữ liệu
            self._data.sort(
                key=lambda x: float(x.get(sort_key, 0)) if str(x.get(sort_key, '')).replace('.', '').isdigit() else str(x.get(sort_key, '')),
                reverse=order == Qt.SortOrder.DescendingOrder
            )
        except (ValueError, IndexError):
            # Nếu có lỗi khi sắp xếp, bỏ qua
            pass
        
        self.layoutChanged.emit()


class DataViewerDialog(QDialog):
    """Hộp thoại xem dữ liệu dạng bảng"""
    
    def __init__(self, data: List[Dict], title: str = "Xem dữ liệu", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.data = data
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Bảng hiển thị dữ liệu
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        
        # Tạo mô hình dữ liệu
        self.model = PandasModel(self.data)
        self.table_view.setModel(self.model)
        
        # Điều chỉnh kích thước cột
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        # Nút điều khiển
        button_layout = QHBoxLayout()
        
        self.btn_export = QPushButton("Xuất ra CSV")
        self.btn_export.clicked.connect(self._export_to_csv)
        
        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_export)
        button_layout.addWidget(self.btn_close)
        
        # Thêm các thành phần vào layout
        layout.addWidget(self.table_view, 1)  # Cho phép bảng co giãn
        layout.addLayout(button_layout)
    
    def _export_to_csv(self):
        """Xuất dữ liệu ra file CSV"""
        if not self.data:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có dữ liệu để xuất.")
            return
        
        # Mở hộp thoại chọn file
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu dữ liệu ra CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_name:
            return
        
        # Đảm bảo có đuôi .csv
        if not file_name.lower().endswith('.csv'):
            file_name += '.csv'
        
        try:
            # Lấy headers từ mô hình
            headers = []
            for i in range(self.model.columnCount()):
                headers.append(self.model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole))
            
            # Ghi dữ liệu ra file CSV
            with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.data)
            
            QMessageBox.information(self, "Xuất dữ liệu", f"Đã xuất dữ liệu thành công vào file:\n{file_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất dữ liệu: {str(e)}")


if __name__ == "__main__":
    # Dữ liệu mẫu để test
    sample_data = [
        {"STT": 1, "Độ sâu (m)": 0.5, "Vận tốc (m/s)": 1.2, "Lực đập (N)": 50, "Nhiệt độ (°C)": 25.5},
        {"STT": 2, "Độ sâu (m)": 1.0, "Vận tốc (m/s)": 1.5, "Lực đập (N)": 52, "Nhiệt độ (°C)": 25.7},
        {"STT": 3, "Độ sâu (m)": 1.5, "Vận tốc (m/s)": 1.3, "Lực đập (N)": 51, "Nhiệt độ (°C)": 25.6},
        {"STT": 4, "Độ sâu (m)": 2.0, "Vận tốc (m/s)": 1.4, "Lực đập (N)": 53, "Nhiệt độ (°C)": 25.8},
        {"STT": 5, "Độ sâu (m)": 2.5, "Vận tốc (m/s)": 1.6, "Lực đập (N)": 54, "Nhiệt độ (°C)": 25.9},
    ]
    
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Tạo và hiển thị hộp thoại
    dialog = DataViewerDialog(sample_data, "Xem dữ liệu mẫu")
    dialog.exec()
    
    sys.exit()
