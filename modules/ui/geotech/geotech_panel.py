"""
Geotech Panel - Phân tích chuyên sâu (Khoan địa chất)
Hiển thị đồ thị lớn: Vận tốc (trục X) theo Độ sâu (trục Y)
Kèm form nhập thông tin hố khoan và lưu dữ liệu theo từng hố khoan.
"""
from __future__ import annotations

import time
import sys
import os
from typing import Dict, Any, List, Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QMessageBox

# Thêm path để import API module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .geotech_charts import GeotechChartsWidget
from .geotech_form import GeotechFormWidget
from .geotech_stats import GeotechStatsWidget
from .geotech_popout import GeotechPopoutManager
from .geotech_utils import GeotechUtils

try:
    from modules.api.holes_api import HolesAPIClient
    from modules.api.drilling_data_service import DrillingDataService
    from modules.api.gnss_location_service import GNSSLocationService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    HolesAPIClient = None
    DrillingDataService = None
    GNSSLocationService = None


class GeotechPanel(QWidget):
	"""Panel phân tích khoan địa chất.

	- Đồ thị: Vận tốc (m/s) theo Độ sâu (m)
	- Bảng thông số: độ sâu hiện tại/tối đa, vận tốc hiện tại/trung bình/tối đa/tối thiểu, số mẫu
	- Form: thông tin hố khoan và lưu dữ liệu theo hố khoan
	"""

	def __init__(self):
		super().__init__()
		self._init_state()
		self._setup_ui()
		self._connect_signals()

	def _init_state(self):
		# Dữ liệu theo hố khoan hiện tại
		self.depth_series_m: List[float] = []
		self.velocity_series_ms: List[float] = []
		self.quality_series: List[int] = []
		self.time_series: List[float] = []
		self.state_series: List[str] = []

		self._velocity_threshold: float = 0.005

		# Giới hạn và throttle để giảm lag UI
		self.max_points: int = 1500
		self.update_interval_s: float = 0.2
		self._last_redraw_ts: float = 0.0
		self.hist_update_interval_s: float = 1.0
		self._hist_last_update_ts: float = 0.0
		
		# API service để gửi drilling data
		self.drilling_data_service: Optional[DrillingDataService] = None
		self.api_client: Optional[HolesAPIClient] = None
		
		# Reference đến MQTT panel để cập nhật drilling data cho GNSS service
		self.mqtt_panel = None

	def _setup_ui(self):
		layout = QVBoxLayout(self)

		# Splitter trái-phải: trái là chart, phải là form + stats
		main_splitter = QSplitter(Qt.Orientation.Horizontal)
		main_splitter.setChildrenCollapsible(False)
		main_splitter.setHandleWidth(8)

		# Tạo các component
		self.charts_widget = GeotechChartsWidget()
		self.form_widget = GeotechFormWidget()
		self.stats_widget = GeotechStatsWidget()
		self.popout_manager = GeotechPopoutManager()

		# Khu vực phải: form + stats
		right_container = QWidget()
		right_container.setMinimumWidth(340)
		right_container.setMaximumWidth(560)
		right_layout = QVBoxLayout(right_container)
		right_layout.setContentsMargins(8, 8, 8, 8)
		right_layout.setSpacing(8)

		right_layout.addWidget(self.form_widget)
		right_layout.addWidget(self.stats_widget)
		right_layout.addStretch()

		main_splitter.addWidget(self.charts_widget)
		main_splitter.addWidget(right_container)
		
		# Thiết lập tỷ lệ
		main_splitter.setSizes([1200, 400])
		main_splitter.setStretchFactor(0, 3)  # Chart container
		main_splitter.setStretchFactor(1, 1)  # Right container

		layout.addWidget(main_splitter)

	def _connect_signals(self):
		"""Kết nối các signal giữa các component"""
		# Charts widget signals
		self.charts_widget.on_units_changed = self._on_units_changed
		self.charts_widget.on_data_cleared = self._on_data_cleared
		self.charts_widget.on_popout_requested = self._on_popout_requested
		
		# Form widget signals
		self.form_widget.session_started.connect(self._on_session_started)
		self.form_widget.recording_started.connect(self._on_recording_started)
		self.form_widget.recording_stopped.connect(self._on_recording_stopped)
		self.form_widget.on_save_requested = self._on_save_requested
		self.form_widget.on_export_requested = self._on_export_requested

	@pyqtSlot(dict)
	def on_new_processed_data(self, data: Dict[str, Any]):
		"""Nhận dữ liệu từ DataProcessor và cập nhật biểu đồ + bảng."""
		try:
			depth_m: Optional[float] = None
			velocity_ms: Optional[float] = None
			quality: Optional[int] = None
			state: Optional[str] = None
			ts: float = data.get('timestamp', time.time())

			if 'distance_m' in data:
				depth_m = float(data['distance_m'])
			elif 'distance_mm' in data:
				depth_m = float(data['distance_mm']) / 1000.0

			if 'velocity_ms' in data:
				velocity_ms = float(data['velocity_ms'])
			if 'signal_quality' in data:
				quality = int(data['signal_quality'])
			if 'state' in data:
				state = str(data['state'])
			if 'velocity_threshold' in data:
				try:
					self._velocity_threshold = float(data['velocity_threshold'])
					self.charts_widget.update_velocity_threshold(self._velocity_threshold)
				except Exception:
					pass

			if depth_m is None or velocity_ms is None:
				return

			# Chỉ cập nhật và ghi dữ liệu khi đang trong trạng thái recording
			if self.form_widget.is_recording:
				# Cập nhật giá trị hiện tại
				self.charts_widget.update_current_values(depth_m, velocity_ms)
				self.depth_series_m.append(depth_m)
				self.velocity_series_ms.append(velocity_ms)
				self.time_series.append(ts)
				self.quality_series.append(quality if quality is not None else 0)
				self.state_series.append(state if state is not None else "")
				
				# Gửi dữ liệu lên API nếu có service
				if self.drilling_data_service:
					self.drilling_data_service.add_velocity_data(
						velocity_ms=velocity_ms,
						depth_m=depth_m,
						timestamp=ts
					)
				
				# Cập nhật dữ liệu tốc độ khoan cho GNSS Location Service (nếu đang chạy trong MQTT panel)
				if self.mqtt_panel and hasattr(self.mqtt_panel, 'set_drilling_data'):
					self.mqtt_panel.set_drilling_data(velocity_ms, depth_m)

				# Giới hạn số điểm để tránh lag UI
				if len(self.depth_series_m) > self.max_points:
					self.depth_series_m = self.depth_series_m[-self.max_points:]
					self.velocity_series_ms = self.velocity_series_ms[-self.max_points:]
					self.time_series = self.time_series[-self.max_points:]
					self.quality_series = self.quality_series[-self.max_points:]
					self.state_series = self.state_series[-self.max_points:]

			# Throttle vẽ - chỉ cập nhật khi đang recording
			should_update_popout = False
			if self.form_widget.is_recording and ts - self._last_redraw_ts >= self.update_interval_s:
				self._refresh_all_plots()
				self._last_redraw_ts = ts
				should_update_popout = True
			# Histogram cập nhật thưa hơn
			if self.form_widget.is_recording and ts - self._hist_last_update_ts >= self.hist_update_interval_s:
				self.charts_widget.update_histogram(self.velocity_series_ms)
				self._hist_last_update_ts = ts
				should_update_popout = True
			
			# Cập nhật popout windows nếu có thay đổi
			if should_update_popout:
				self._update_popout_windows()
		except Exception as e:
			print(f"GeotechPanel update error: {e}")

	def _refresh_all_plots(self):
		"""Cập nhật tất cả các đồ thị"""
		# Cập nhật main plot
		self.charts_widget.update_main_plot(
			self.depth_series_m, self.velocity_series_ms, self.state_series
		)
		
		# Cập nhật time plots
		self.charts_widget.update_time_plots(
			self.time_series, self.depth_series_m, self.velocity_series_ms, self.state_series
		)
		
		# Chỉ cập nhật stats khi đang recording
		if self.form_widget.is_recording:
			self.stats_widget.update_stats(
				self.depth_series_m, self.velocity_series_ms, self.state_series, self._velocity_threshold
			)

	def _update_popout_windows(self):
		"""Cập nhật tất cả cửa sổ popout với dữ liệu mới nhất"""
		depth_unit, velocity_unit = self.charts_widget.get_units()
		self.popout_manager.update_popout_windows(
			self.depth_series_m, self.velocity_series_ms, self.time_series, 
			self.state_series, depth_unit, velocity_unit, self._velocity_threshold
		)

	def _reset_statistics(self):
		"""Reset tất cả thống kê về giá trị mặc định"""
		# Reset stats widget về trạng thái rỗng
		self.stats_widget.update_stats([], [], [], self._velocity_threshold)

	# Signal handlers
	def _on_units_changed(self, depth_unit: str, velocity_unit: str):
		"""Xử lý khi thay đổi đơn vị đo"""
		self.stats_widget.update_units(depth_unit, velocity_unit)
		self._update_popout_windows()

	def _on_data_cleared(self):
		"""Xử lý khi xóa toàn bộ dữ liệu"""
		# Xóa dữ liệu gốc
		self.depth_series_m.clear()
		self.velocity_series_ms.clear()
		self.quality_series.clear()
		self.time_series.clear()
		self.state_series.clear()
		
		# Reset thống kê
		self._reset_statistics()
		
		# Cập nhật popout windows
		self._update_popout_windows()

	def _on_popout_requested(self, source_widget, title: str):
		"""Xử lý khi yêu cầu mở popout window"""
		depth_unit, velocity_unit = self.charts_widget.get_units()
		self.popout_manager.create_popout_window(
			self, source_widget, title, depth_unit, velocity_unit
		)

	def _on_session_started(self):
		"""Xử lý khi bắt đầu phiên mới"""
		self.depth_series_m.clear()
		self.velocity_series_ms.clear()
		self.quality_series.clear()
		self.time_series.clear()
		self.state_series.clear()
		self._refresh_all_plots()
		self._update_popout_windows()
		
		# Reset thống kê khi bắt đầu phiên mới
		self._reset_statistics()
	
	def _on_recording_started(self, settings: Dict[str, Any]):
		"""Xử lý khi bắt đầu recording - khởi tạo API service"""
		if not API_AVAILABLE:
			return
		
		try:
			# Lấy project và hole info
			project_manager = self.form_widget.project_manager
			if not project_manager.current_project or not project_manager.current_hole:
				return
			
			# Lấy API config từ project
			project_info = project_manager.current_project
			api_base_url = project_info.get('api_base_url', 'http://localhost:3000/api')
			api_project_id = project_info.get('api_project_id')
			
			if not api_project_id:
				print("Warning: API project_id not configured")
				return
			
			try:
				api_project_id = int(api_project_id)
			except (ValueError, TypeError):
				print(f"Warning: Invalid API project_id: {api_project_id}")
				return
			
			# Lấy hole info
			hole_info = project_manager.current_hole
			api_hole_id = hole_info.get('api_hole_id')
			
			# Kiểm tra api_hole_id có hợp lệ không (None, 0, "", False đều không hợp lệ)
			# Nhưng phải cho phép cả string và số
			api_hole_id_valid = False
			if api_hole_id is not None:
				if isinstance(api_hole_id, str) and api_hole_id.strip():
					api_hole_id_valid = True
				elif isinstance(api_hole_id, (int, float)) and api_hole_id != 0:
					api_hole_id_valid = True
			
			if not api_hole_id_valid:
				# Thử tìm hole trong API bằng hole name
				api_client = HolesAPIClient(base_url=api_base_url)
				hole_name = hole_info.get('name', '')
				if hole_name:
					try:
						api_hole = api_client.find_hole_by_hole_id(api_project_id, hole_name)
						if api_hole:
							# Ưu tiên dùng hole_id string nếu có, nếu không thì dùng database id
							api_hole_id = api_hole.get('hole_id') or api_hole.get('id')
							if api_hole_id:
								# Lưu lại vào hole_info
								hole_info['api_hole_id'] = api_hole_id
								api_hole_id_valid = True
					except Exception as e:
						print(f"Error finding hole by name: {e}")
			
			if not api_hole_id_valid:
				print(f"Warning: API hole_id not found. Hole name: {hole_info.get('name', 'Unknown')}, api_hole_id: {api_hole_id}")
				return
			
			# Khởi tạo API client và service
			self.api_client = HolesAPIClient(base_url=api_base_url)
			self.drilling_data_service = DrillingDataService(
				api_client=self.api_client,
				project_id=api_project_id,
				hole_id=api_hole_id
			)
			
			# Bắt đầu service
			self.drilling_data_service.start()
			print(f"Drilling data service started for project {api_project_id}, hole {api_hole_id}")
			
			# Lưu ý: GNSS Location Service được quản lý trong tab MQTT, không khởi động ở đây
			
		except Exception as e:
			print(f"Error starting drilling data service: {e}")
			self.drilling_data_service = None
	
	def _on_recording_stopped(self):
		"""Xử lý khi dừng recording - dừng API service"""
		if self.drilling_data_service:
			try:
				self.drilling_data_service.stop()
				stats = self.drilling_data_service.get_stats()
				print(f"Drilling data service stopped. Stats: {stats}")
			except Exception as e:
				print(f"Error stopping drilling data service: {e}")
			finally:
				self.drilling_data_service = None
		
		# Lưu ý: GNSS Location Service được quản lý trong tab MQTT, không dừng ở đây

	def _on_save_requested(self):
		"""Xử lý khi yêu cầu lưu dữ liệu CSV"""
		if not self.depth_series_m or not self.velocity_series_ms:
			QMessageBox.information(self, "Không có dữ liệu", "Chưa có dữ liệu để lưu.")
			return
		
		data = {
			'depth_series': self.depth_series_m,
			'velocity_series': self.velocity_series_ms,
			'time_series': self.time_series,
			'state_series': self.state_series,
			'quality_series': self.quality_series
		}
		self.form_widget.save_data_to_csv(data)
	
	def _on_export_requested(self):
		"""Xử lý khi yêu cầu xuất dữ liệu"""
		if not self.depth_series_m or not self.velocity_series_ms:
			QMessageBox.information(self, "Không có dữ liệu", "Chưa có dữ liệu để xuất.")
			return
		
		# Hiển thị dialog chọn định dạng xuất
		from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
		
		dialog = QDialog(self)
		dialog.setWindowTitle("Xuất dữ liệu")
		dialog.setModal(True)
		layout = QVBoxLayout(dialog)
		
		layout.addWidget(QLabel("Chọn định dạng xuất:"))
		
		format_combo = QComboBox()
		format_combo.addItems(["CSV", "Excel (.xlsx)", "JSON", "TXT"])
		layout.addWidget(format_combo)
		
		buttons_layout = QHBoxLayout()
		btn_export = QPushButton("Xuất")
		btn_cancel = QPushButton("Hủy")
		
		btn_export.clicked.connect(lambda: self._export_data_format(format_combo.currentText(), dialog))
		btn_cancel.clicked.connect(dialog.reject)
		
		buttons_layout.addWidget(btn_export)
		buttons_layout.addWidget(btn_cancel)
		layout.addLayout(buttons_layout)
		
		dialog.exec()
	
	def _export_data_format(self, format_type: str, dialog):
		"""Xuất dữ liệu theo định dạng được chọn"""
		dialog.accept()
		
		data = {
			'depth_series': self.depth_series_m,
			'velocity_series': self.velocity_series_ms,
			'time_series': self.time_series,
			'state_series': self.state_series,
			'quality_series': self.quality_series
		}
		
		if format_type == "CSV":
			self.form_widget.save_data_to_csv(data)
		elif format_type == "Excel (.xlsx)":
			self._export_to_excel(data)
		elif format_type == "JSON":
			self._export_to_json(data)
		elif format_type == "TXT":
			self._export_to_txt(data)
	
	def _export_to_excel(self, data: Dict[str, Any]):
		"""Xuất dữ liệu ra file Excel"""
		try:
			import pandas as pd
			from PyQt6.QtWidgets import QFileDialog
			
			# Tạo DataFrame
			df = pd.DataFrame({
				'timestamp': data['time_series'],
				'depth_m': data['depth_series'],
				'velocity_ms': data['velocity_series'],
				'state': data['state_series'],
				'signal_quality': data['quality_series']
			})
			
			# Thêm thông tin hố khoan
			borehole_info = self.form_widget.get_borehole_info()
			df['borehole_name'] = borehole_info.get('name', '')
			df['location'] = borehole_info.get('location', '')
			df['operator'] = borehole_info.get('operator', '')
			df['notes'] = borehole_info.get('notes', '')
			
			# Chọn file
			filename, _ = QFileDialog.getSaveFileName(
				self, "Xuất Excel", f"{borehole_info.get('name', 'data')}.xlsx", 
				"Excel Files (*.xlsx)"
			)
			
			if filename:
				df.to_excel(filename, index=False)
				QMessageBox.information(self, "Thành công", f"Đã xuất dữ liệu ra:\n{filename}")
		except ImportError:
			QMessageBox.warning(self, "Lỗi", "Cần cài đặt pandas để xuất Excel: pip install pandas openpyxl")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể xuất Excel: {e}")
	
	def _export_to_json(self, data: Dict[str, Any]):
		"""Xuất dữ liệu ra file JSON"""
		try:
			import json
			from PyQt6.QtWidgets import QFileDialog
			
			# Chuẩn bị dữ liệu
			export_data = {
				'borehole_info': self.form_widget.get_borehole_info(),
				'data': {
					'timestamps': data['time_series'],
					'depths_m': data['depth_series'],
					'velocities_ms': data['velocity_series'],
					'states': data['state_series'],
					'qualities': data['quality_series']
				}
			}
			
			# Chọn file
			borehole_info = self.form_widget.get_borehole_info()
			filename, _ = QFileDialog.getSaveFileName(
				self, "Xuất JSON", f"{borehole_info.get('name', 'data')}.json", 
				"JSON Files (*.json)"
			)
			
			if filename:
				with open(filename, 'w', encoding='utf-8') as f:
					json.dump(export_data, f, indent=2, ensure_ascii=False)
				QMessageBox.information(self, "Thành công", f"Đã xuất dữ liệu ra:\n{filename}")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể xuất JSON: {e}")
	
	def _export_to_txt(self, data: Dict[str, Any]):
		"""Xuất dữ liệu ra file TXT"""
		try:
			from PyQt6.QtWidgets import QFileDialog
			
			# Chọn file
			borehole_info = self.form_widget.get_borehole_info()
			filename, _ = QFileDialog.getSaveFileName(
				self, "Xuất TXT", f"{borehole_info.get('name', 'data')}.txt", 
				"Text Files (*.txt)"
			)
			
			if filename:
				with open(filename, 'w', encoding='utf-8') as f:
					# Ghi header
					f.write("=== THÔNG TIN HỐ KHOAN ===\n")
					f.write(f"Tên hố khoan: {borehole_info.get('name', '')}\n")
					f.write(f"Vị trí: {borehole_info.get('location', '')}\n")
					f.write(f"Người vận hành: {borehole_info.get('operator', '')}\n")
					f.write(f"Ghi chú: {borehole_info.get('notes', '')}\n\n")
					
					# Ghi dữ liệu
					f.write("=== DỮ LIỆU ĐO ===\n")
					f.write("Timestamp\tDepth(m)\tVelocity(m/s)\tState\tQuality\n")
					f.write("-" * 60 + "\n")
					
					for i in range(len(data['time_series'])):
						f.write(f"{data['time_series'][i]:.6f}\t")
						f.write(f"{data['depth_series'][i]:.6f}\t")
						f.write(f"{data['velocity_series'][i]:.6f}\t")
						f.write(f"{data['state_series'][i] if i < len(data['state_series']) else ''}\t")
						f.write(f"{data['quality_series'][i] if i < len(data['quality_series']) else ''}\n")
				
				QMessageBox.information(self, "Thành công", f"Đã xuất dữ liệu ra:\n{filename}")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể xuất TXT: {e}")

	@pyqtSlot(dict)
	def on_statistics_updated(self, stats: Dict[str, Any]):
		"""Nhận thống kê cập nhật từ DataProcessor"""
		try:
			# Chỉ cập nhật thống kê khi đang trong trạng thái recording
			if not self.form_widget.is_recording:
				return
				
			if 'velocity_threshold' in stats:
				try:
					self._velocity_threshold = float(stats['velocity_threshold'])
					self.charts_widget.update_velocity_threshold(self._velocity_threshold)
					self._update_popout_windows()
				except Exception:
					pass
			
			# Cập nhật stats widget
			self.stats_widget.update_statistics_from_processor(stats)
		except Exception:
			pass

