"""
MQTT Panel - Tab quản lý kết nối MQTT (Publish và Subscribe cho GNSS)
"""
import sys
import os
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QSpinBox, QCheckBox, QTextEdit, QFileDialog,
    QComboBox, QSplitter, QDoubleSpinBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QSettings

# Thêm path để import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ...mqtt.mqtt_publisher import MQTTPublisher

try:
    from modules.mqtt.mqtt_subscriber import MQTTSubscriber
    from modules.api.gnss_location_service import GNSSLocationService
    from modules.api.holes_api import HolesAPIClient
    GNSS_AVAILABLE = True
except ImportError:
    GNSS_AVAILABLE = False
    MQTTSubscriber = None
    GNSSLocationService = None
    HolesAPIClient = None


class MQTTPanel(QWidget):
    """Panel cấu hình và quản lý MQTT - Publish dữ liệu và Subscribe GNSS"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.publisher: Optional[MQTTPublisher] = None
        self.gnss_subscriber: Optional[MQTTSubscriber] = None
        self.gnss_service: Optional[GNSSLocationService] = None
        self.is_connected: bool = False
        self.is_gnss_active: bool = False
        self.latest_data: Dict[str, Any] = {}
        self.latest_stats: Dict[str, Any] = {}

        self._setup_ui()
        self._connect_signals()
        
        # Timer để cập nhật stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_gnss_stats)
        self.stats_timer.start(1000)  # Update mỗi giây
        
        # Load settings
        if GNSS_AVAILABLE:
            self._load_gnss_settings()

    # === UI setup ===
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Tạo tab widget để tách Publish và Subscribe
        tab_widget = QTabWidget()
        
        # Tab 1: Publish (dữ liệu đo)
        publish_tab = self._create_publish_tab()
        tab_widget.addTab(publish_tab, "Publish Dữ Liệu")
        
        # Tab 2: Subscribe GNSS (nếu có)
        if GNSS_AVAILABLE:
            gnss_tab = self._create_gnss_tab()
            tab_widget.addTab(gnss_tab, "Subscribe GNSS RTK")
        
        layout.addWidget(tab_widget)

    def _create_publish_tab(self) -> QWidget:
        """Tạo tab Publish dữ liệu"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # --- Connection group ---
        conn_group = QGroupBox("Kết nối MQTT Broker")
        conn_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        conn_layout = QGridLayout(conn_group)

        self.host_edit = QLineEdit("localhost")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(1883)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.tls_cb = QCheckBox("Bật TLS")
        self.ca_path_edit = QLineEdit()
        self.ca_path_edit.setPlaceholderText("CA certificate path (tuỳ chọn)")
        self.ca_browse_btn = QPushButton("Chọn file...")
        self.ca_path_edit.setEnabled(False)
        self.ca_browse_btn.setEnabled(False)

        self.connect_btn = QPushButton("Kết nối")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        self.disconnect_btn = QPushButton("Ngắt kết nối")
        self.disconnect_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px;")
        self.disconnect_btn.setEnabled(False)
        self.status_label = QLabel("Chưa kết nối")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")

        row = 0
        conn_layout.addWidget(QLabel("Host:"), row, 0)
        conn_layout.addWidget(self.host_edit, row, 1)
        conn_layout.addWidget(QLabel("Port:"), row, 2)
        conn_layout.addWidget(self.port_spin, row, 3)
        row += 1
        conn_layout.addWidget(QLabel("Username:"), row, 0)
        conn_layout.addWidget(self.username_edit, row, 1)
        conn_layout.addWidget(QLabel("Password:"), row, 2)
        conn_layout.addWidget(self.password_edit, row, 3)
        row += 1
        conn_layout.addWidget(self.tls_cb, row, 0)
        conn_layout.addWidget(self.ca_path_edit, row, 1, 1, 2)
        conn_layout.addWidget(self.ca_browse_btn, row, 3)
        row += 1
        conn_layout.addWidget(self.connect_btn, row, 0, 1, 2)
        conn_layout.addWidget(self.disconnect_btn, row, 2, 1, 2)
        row += 1
        conn_layout.addWidget(QLabel("Trạng thái:"), row, 0)
        conn_layout.addWidget(self.status_label, row, 1, 1, 3)

        layout.addWidget(conn_group)

        # --- Publish config group ---
        pub_group = QGroupBox("Cấu hình Publish")
        pub_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        pub_layout = QGridLayout(pub_group)

        self.topic_edit = QLineEdit("sensors/laser")
        self.topic_edit.setToolTip("Có thể dùng placeholder, ví dụ: sensors/laser/{serial_number}")
        self.qos_combo = QComboBox()
        self.qos_combo.addItems(["0", "1", "2"])
        self.retain_cb = QCheckBox("Retain")
        self.auto_publish_cb = QCheckBox("Publish tự động mỗi mẫu đo")
        self.auto_publish_cb.setChecked(False)

        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "JSON (đầy đủ)",
            "JSON (tối giản)",
            "Tuỳ biến (template)"
        ])
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText("Ví dụ: {\n  \"timestamp\": {timestamp},\n  \"distance_mm\": {distance_mm},\n  \"quality\": {signal_quality},\n  \"velocity_ms\": {velocity_ms}\n}")
        self.template_edit.setVisible(False)
        self.template_edit.setMaximumHeight(100)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText("Xem trước payload sẽ publish")
        self.preview_edit.setMaximumHeight(150)

        self.publish_now_btn = QPushButton("Publish ngay")
        self.publish_now_btn.setEnabled(False)
        self.publish_now_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")

        row = 0
        pub_layout.addWidget(QLabel("Topic:"), row, 0)
        pub_layout.addWidget(self.topic_edit, row, 1, 1, 3)
        row += 1
        pub_layout.addWidget(QLabel("QoS:"), row, 0)
        pub_layout.addWidget(self.qos_combo, row, 1)
        pub_layout.addWidget(self.retain_cb, row, 2)
        pub_layout.addWidget(self.auto_publish_cb, row, 3)
        row += 1
        pub_layout.addWidget(QLabel("Định dạng:"), row, 0)
        pub_layout.addWidget(self.format_combo, row, 1, 1, 3)
        row += 1
        pub_layout.addWidget(QLabel("Template:"), row, 0)
        pub_layout.addWidget(self.template_edit, row, 1, 1, 3)
        row += 1
        pub_layout.addWidget(QLabel("Xem trước:"), row, 0)
        pub_layout.addWidget(self.preview_edit, row, 1, 1, 3)
        row += 1
        pub_layout.addWidget(self.publish_now_btn, row, 3)

        layout.addWidget(pub_group)

        # --- Log group ---
        log_group = QGroupBox("Nhật ký Publish")
        log_layout = QVBoxLayout(log_group)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(150)
        log_controls = QHBoxLayout()
        self.clear_log_btn = QPushButton("Xoá log")
        log_controls.addStretch()
        log_controls.addWidget(self.clear_log_btn)
        log_layout.addWidget(self.log_edit)
        log_layout.addLayout(log_controls)
        layout.addWidget(log_group)

        layout.addStretch()
        return tab

    def _create_gnss_tab(self) -> QWidget:
        """Tạo tab Subscribe GNSS RTK"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # --- MQTT Broker Connection Config ---
        mqtt_conn_group = QGroupBox("Kết nối MQTT Broker cho GNSS")
        mqtt_conn_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        mqtt_conn_layout = QGridLayout(mqtt_conn_group)

        self.gnss_mqtt_host_edit = QLineEdit("localhost")
        self.gnss_mqtt_host_edit.setPlaceholderText("localhost hoặc IP của broker")
        self.gnss_mqtt_port_spin = QSpinBox()
        self.gnss_mqtt_port_spin.setRange(1, 65535)
        self.gnss_mqtt_port_spin.setValue(1883)
        self.gnss_mqtt_username_edit = QLineEdit()
        self.gnss_mqtt_username_edit.setPlaceholderText("Tùy chọn")
        self.gnss_mqtt_password_edit = QLineEdit()
        self.gnss_mqtt_password_edit.setPlaceholderText("Tùy chọn")
        self.gnss_mqtt_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gnss_show_pass_cb = QCheckBox("Hiện")
        self.gnss_show_pass_cb.stateChanged.connect(
            lambda state: self.gnss_mqtt_password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password
            )
        )

        row = 0
        mqtt_conn_layout.addWidget(QLabel("Broker Host/IP:"), row, 0)
        mqtt_conn_layout.addWidget(self.gnss_mqtt_host_edit, row, 1)
        mqtt_conn_layout.addWidget(QLabel("Port:"), row, 2)
        mqtt_conn_layout.addWidget(self.gnss_mqtt_port_spin, row, 3)
        row += 1
        mqtt_conn_layout.addWidget(QLabel("Username:"), row, 0)
        mqtt_conn_layout.addWidget(self.gnss_mqtt_username_edit, row, 1)
        mqtt_conn_layout.addWidget(QLabel("Password:"), row, 2)
        mqtt_conn_layout.addWidget(self.gnss_mqtt_password_edit, row, 3)
        mqtt_conn_layout.addWidget(self.gnss_show_pass_cb, row, 4)

        layout.addWidget(mqtt_conn_group)

        # --- GNSS Service Config ---
        config_group = QGroupBox("Cấu hình GNSS Location Service")
        config_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        config_layout = QGridLayout(config_group)

        self.gnss_topic_edit = QLineEdit("device/+/upload")
        self.gnss_topic_edit.setPlaceholderText("device/+/upload")
        self.gnss_max_distance_spin = QDoubleSpinBox()
        self.gnss_max_distance_spin.setMinimum(0.1)
        self.gnss_max_distance_spin.setMaximum(1000.0)
        self.gnss_max_distance_spin.setValue(10.0)
        self.gnss_max_distance_spin.setSuffix(" m")
        self.gnss_max_distance_spin.setDecimals(1)
        
        # API Config - Đã ẩn vì tách biệt chức năng
        # Nếu cần liên kết với dự án để cập nhật tốc độ khoan, 
        # hãy chọn dự án trong tab Phân Tích Khoan.

        self.gnss_start_btn = QPushButton("Bắt đầu GNSS Service")
        self.gnss_start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        self.gnss_stop_btn = QPushButton("Dừng GNSS Service")
        self.gnss_stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px;")
        self.gnss_stop_btn.setEnabled(False)
        self.gnss_status_label = QLabel("Chưa khởi động")
        self.gnss_status_label.setStyleSheet("font-weight: bold; padding: 5px;")

        row = 0
        config_layout.addWidget(QLabel("MQTT Topic:"), row, 0)
        config_layout.addWidget(self.gnss_topic_edit, row, 1, 1, 3)
        row += 1
        config_layout.addWidget(QLabel("Khoảng cách tối đa:"), row, 0)
        config_layout.addWidget(self.gnss_max_distance_spin, row, 1)
        row += 1
        config_layout.addWidget(self.gnss_start_btn, row, 0, 1, 2)
        config_layout.addWidget(self.gnss_stop_btn, row, 2, 1, 2)
        row += 1
        config_layout.addWidget(QLabel("Trạng thái:"), row, 0)
        config_layout.addWidget(self.gnss_status_label, row, 1, 1, 3)

        layout.addWidget(config_group)

        # --- Stats Group ---
        stats_group = QGroupBox("Thống kê GNSS Service")
        stats_layout = QGridLayout(stats_group)

        self.gnss_messages_label = QLabel("0")
        self.gnss_locations_label = QLabel("0")
        self.gnss_holes_updated_label = QLabel("0")
        self.gnss_last_update_label = QLabel("Chưa có")
        self.gnss_last_location_label = QLabel("Chưa có")

        row = 0
        stats_layout.addWidget(QLabel("Messages nhận được:"), row, 0)
        stats_layout.addWidget(self.gnss_messages_label, row, 1)
        row += 1
        stats_layout.addWidget(QLabel("Locations xử lý:"), row, 0)
        stats_layout.addWidget(self.gnss_locations_label, row, 1)
        row += 1
        stats_layout.addWidget(QLabel("Holes đã cập nhật:"), row, 0)
        stats_layout.addWidget(self.gnss_holes_updated_label, row, 1)
        row += 1
        stats_layout.addWidget(QLabel("Cập nhật cuối:"), row, 0)
        stats_layout.addWidget(self.gnss_last_update_label, row, 1)
        row += 1
        stats_layout.addWidget(QLabel("Vị trí cuối:"), row, 0)
        stats_layout.addWidget(self.gnss_last_location_label, row, 1, 1, 2)

        layout.addWidget(stats_group)

        # --- GNSS Log ---
        gnss_log_group = QGroupBox("Nhật ký GNSS")
        gnss_log_layout = QVBoxLayout(gnss_log_group)
        self.gnss_log_edit = QTextEdit()
        self.gnss_log_edit.setReadOnly(True)
        self.gnss_log_edit.setMaximumHeight(200)
        gnss_log_controls = QHBoxLayout()
        self.clear_gnss_log_btn = QPushButton("Xoá log")
        gnss_log_controls.addStretch()
        gnss_log_controls.addWidget(self.clear_gnss_log_btn)
        gnss_log_layout.addWidget(self.gnss_log_edit)
        gnss_log_layout.addLayout(gnss_log_controls)
        layout.addWidget(gnss_log_group)

        layout.addStretch()
        return tab

    def _connect_signals(self):
        # Publish signals
        self.tls_cb.stateChanged.connect(self._on_tls_toggled)
        self.ca_browse_btn.clicked.connect(self._browse_ca_file)
        self.connect_btn.clicked.connect(self._connect_broker)
        self.disconnect_btn.clicked.connect(self._disconnect_broker)
        self.publish_now_btn.clicked.connect(self._publish_now)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.clear_log_btn.clicked.connect(lambda: self.log_edit.clear())
        
        # GNSS signals
        if GNSS_AVAILABLE:
            self.gnss_start_btn.clicked.connect(self._start_gnss_service)
            self.gnss_stop_btn.clicked.connect(self._stop_gnss_service)
            self.clear_gnss_log_btn.clicked.connect(lambda: self.gnss_log_edit.clear())

    # === Publish Event handlers ===
    def _on_tls_toggled(self, _state: int):
        enabled = self.tls_cb.isChecked()
        self.ca_path_edit.setEnabled(enabled)
        self.ca_browse_btn.setEnabled(enabled)

    def _browse_ca_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn CA certificate", "", "Certificates (*.crt *.pem);;All Files (*)")
        if path:
            self.ca_path_edit.setText(path)

    def _append_log(self, message: str):
        self.log_edit.append(message)

    def _set_connected_ui(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.publish_now_btn.setEnabled(connected)
        if connected:
            self.status_label.setText("Đã kết nối")
            self.status_label.setStyleSheet("font-weight: bold; color: green; padding: 5px;")
        else:
            self.status_label.setText("Chưa kết nối")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")

    def _connect_broker(self):
        try:
            host = self.host_edit.text().strip() or "localhost"
            port = int(self.port_spin.value())
            username = self.username_edit.text().strip() or None
            password = self.password_edit.text() or None
            tls_enabled = self.tls_cb.isChecked()
            ca_path = self.ca_path_edit.text().strip() or None

            self.publisher = MQTTPublisher(
                broker_host=host,
                broker_port=port,
                username=username,
                password=password,
                tls_enabled=tls_enabled,
                ca_certs=ca_path
            )
            ok = self.publisher.connect()
            if ok:
                self._set_connected_ui(True)
                self._append_log(f"[INFO] Kết nối MQTT thành công: {host}:{port}")
            else:
                self._append_log("[ERROR] Kết nối MQTT thất bại")
        except Exception as e:
            self._append_log(f"[ERROR] Lỗi kết nối MQTT: {e}")

    def _disconnect_broker(self):
        try:
            if self.publisher:
                self.publisher.disconnect()
            self._set_connected_ui(False)
            self._append_log("[INFO] Đã ngắt kết nối MQTT")
        except Exception as e:
            self._append_log(f"[ERROR] Lỗi ngắt kết nối: {e}")

    def _build_payload(self, data: Dict[str, Any]) -> str:
        fmt = self.format_combo.currentText()
        try:
            combined = {**self.latest_stats, **data}
            if fmt.startswith("JSON (đầy đủ)"):
                import json
                return json.dumps(combined, ensure_ascii=False, indent=2)
            if fmt.startswith("JSON (tối giản)"):
                minimal = {
                    'timestamp': combined.get('timestamp'),
                    'distance_mm': combined.get('distance_mm'),
                    'signal_quality': combined.get('signal_quality'),
                    'velocity_ms': combined.get('velocity_ms')
                }
                import json
                return json.dumps(minimal, ensure_ascii=False)
            # Custom template
            template = self.template_edit.toPlainText().strip()
            if not template:
                template = "{timestamp},{distance_mm},{signal_quality},{velocity_ms}"
            class SafeDict(dict):
                def __missing__(self, key):
                    return ''
            return template.format_map(SafeDict(combined))
        except Exception as e:
            return f"[ERROR] Lỗi tạo payload: {e}"

    def _build_topic(self, data: Dict[str, Any]) -> str:
        topic_template = self.topic_edit.text().strip() or "sensors/laser"
        class SafeDict(dict):
            def __missing__(self, key):
                return ''
        try:
            combined = {**self.latest_stats, **data}
            return topic_template.format_map(SafeDict(combined))
        except Exception:
            return topic_template

    def _refresh_preview(self):
        if not self.latest_data:
            self.preview_edit.setPlainText("")
            return
        payload = self._build_payload(self.latest_data)
        topic = self._build_topic(self.latest_data)
        self.preview_edit.setPlainText(f"Topic: {topic}\n\n{payload}")

    def _on_format_changed(self, _index: int):
        is_template = self.format_combo.currentText().startswith("Tuỳ biến")
        self.template_edit.setVisible(is_template)
        self._refresh_preview()

    def _publish_now(self):
        if not self.publisher or not self.is_connected:
            self._append_log("[WARNING] Chưa kết nối MQTT")
            return
        if not self.latest_data:
            self._append_log("[WARNING] Chưa có dữ liệu để publish")
            return

        topic = self._build_topic(self.latest_data)
        payload = self._build_payload(self.latest_data)
        qos = int(self.qos_combo.currentText())
        retain = self.retain_cb.isChecked()

        ok = self.publisher.publish(topic, payload, qos=qos, retain=retain)
        if ok:
            self._append_log(f"[SUCCESS] Published → {topic}")
        else:
            self._append_log(f"[ERROR] Publish thất bại → {topic}")

    # === GNSS Event handlers ===
    def _start_gnss_service(self):
        """Bắt đầu GNSS Location Service"""
        if not GNSS_AVAILABLE:
            self._append_gnss_log("[ERROR] GNSS module không khả dụng")
            return
        
        # Lưu cấu hình trước khi bắt đầu
        self._save_gnss_settings()
        
        try:
            # Lấy thông tin dự án nếu có (Optional)
            from modules.ui.geotech.project_manager import ProjectManager
            project_manager = ProjectManager()
            
            api_client = None
            api_project_id = None
            
            if project_manager.current_project:
                project_info = project_manager.current_project
                api_base_url = project_info.get('api_base_url', 'https://nomin.wintech.io.vn/api')
                proj_id_val = project_info.get('api_project_id')
                
                if proj_id_val:
                    try:
                        api_project_id = int(proj_id_val)
                        api_client = HolesAPIClient(base_url=api_base_url)
                        self._append_gnss_log(f"[INFO] Đã liên kết với dự án ID: {api_project_id}")
                    except (ValueError, TypeError):
                        self._append_gnss_log(f"[WARNING] Project ID không hợp lệ: {proj_id_val}")
            
            if not api_project_id:
                self._append_gnss_log("[INFO] Chạy chế độ Monitor (không cập nhật drilling data lên server)")

            # Lấy MQTT config từ UI GNSS tab
            mqtt_host = self.gnss_mqtt_host_edit.text().strip() or 'localhost'
            mqtt_port = int(self.gnss_mqtt_port_spin.value())
            mqtt_username = self.gnss_mqtt_username_edit.text().strip() or None
            mqtt_password = self.gnss_mqtt_password_edit.text().strip() or None
            mqtt_topic = self.gnss_topic_edit.text().strip() or 'device/+/upload'
            max_distance = self.gnss_max_distance_spin.value()
            
            # Khởi tạo API client và GNSS service
            self.gnss_service = GNSSLocationService(
                mqtt_broker_host=mqtt_host,
                mqtt_broker_port=mqtt_port,
                mqtt_topic=mqtt_topic,
                api_client=api_client,
                project_id=api_project_id,
                max_distance_threshold=max_distance,
                mqtt_username=mqtt_username,
                mqtt_password=mqtt_password
            )
            
            # Set callback để log
            def on_gnss_message(topic: str, payload: Dict[str, Any]):
                self._append_gnss_log(f"[GNSS] Nhận từ {topic}: {payload}")
            
            # Bắt đầu service
            self.gnss_service.start()
            self.is_gnss_active = True
            self.gnss_start_btn.setEnabled(False)
            self.gnss_stop_btn.setEnabled(True)
            self.gnss_status_label.setText("Đang chạy")
            self.gnss_status_label.setStyleSheet("font-weight: bold; color: green; padding: 5px;")
            self._append_gnss_log(f"[INFO] GNSS Service đã khởi động (Topic: {mqtt_topic})")
            
        except Exception as e:
            self._append_gnss_log(f"[ERROR] Lỗi khởi động GNSS Service: {e}")
            import traceback
            self._append_gnss_log(traceback.format_exc())
    
    def _stop_gnss_service(self):
        """Dừng GNSS Location Service"""
        if self.gnss_service:
            try:
                self.gnss_service.stop()
                stats = self.gnss_service.get_stats()
                self._append_gnss_log(f"[INFO] GNSS Service đã dừng. Stats: {stats}")
            except Exception as e:
                self._append_gnss_log(f"[ERROR] Lỗi dừng GNSS Service: {e}")
            finally:
                self.gnss_service = None
        
        self.is_gnss_active = False
        self.gnss_start_btn.setEnabled(True)
        self.gnss_stop_btn.setEnabled(False)
        self.gnss_status_label.setText("Chưa khởi động")
        self.gnss_status_label.setStyleSheet("font-weight: bold; padding: 5px;")
    
    def _update_gnss_stats(self):
        """Cập nhật thống kê GNSS Service"""
        if not self.gnss_service or not self.is_gnss_active:
            return
        
        try:
            stats = self.gnss_service.get_stats()
            self.gnss_messages_label.setText(str(stats.get('messages_received', 0)))
            self.gnss_locations_label.setText(str(stats.get('locations_processed', 0)))
            self.gnss_holes_updated_label.setText(str(stats.get('holes_updated', 0)))
            
            last_update = stats.get('last_update_time')
            if last_update:
                self.gnss_last_update_label.setText(str(last_update))
            
            last_location = stats.get('last_location')
            if last_location:
                lat = last_location.get('lat', 'N/A')
                lon = last_location.get('lon', 'N/A')
                self.gnss_last_location_label.setText(f"Lat: {lat}, Lon: {lon}")
        except Exception:
            pass
    
    def _append_gnss_log(self, message: str):
        """Thêm log vào GNSS log"""
        self.gnss_log_edit.append(message)
        # Auto scroll to bottom
        scrollbar = self.gnss_log_edit.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())
    
    def set_drilling_data(self, velocity_ms: float, depth_m: float):
        """Set dữ liệu tốc độ khoan cho GNSS service"""
        if self.gnss_service and self.is_gnss_active:
            self.gnss_service.set_drilling_data(velocity_ms, depth_m)

    # === Public API ===
    @pyqtSlot(dict)
    def on_new_processed_data(self, processed: Dict[str, Any]):
        """Nhận dữ liệu từ DataProcessor.new_data_processed để xem trước/publish."""
        self.latest_data = processed or {}
        self._refresh_preview()
        if self.auto_publish_cb.isChecked() and self.publisher and self.is_connected:
            self._publish_now()
        
        # Cập nhật drilling data cho GNSS service
        if self.gnss_service and self.is_gnss_active:
            velocity_ms = processed.get('velocity_ms', 0.0)
            depth_m = processed.get('distance_m', 0.0) or (processed.get('distance_mm', 0) / 1000.0)
            if velocity_ms and depth_m:
                self.set_drilling_data(velocity_ms, depth_m)

    @pyqtSlot(dict)
    def on_statistics_updated(self, stats: Dict[str, Any]):
        """Nhận thống kê/metadata thiết bị để làm giàu payload và topic placeholders."""
        self.latest_stats = stats or {}
        self._refresh_preview()

    def _save_gnss_settings(self):
        """Lưu cấu hình GNSS MQTT"""
        settings = QSettings("Aitogy", "MeskernelLaserApp")
        settings.setValue("gnss_mqtt_host", self.gnss_mqtt_host_edit.text())
        settings.setValue("gnss_mqtt_port", self.gnss_mqtt_port_spin.value())
        settings.setValue("gnss_mqtt_username", self.gnss_mqtt_username_edit.text())
        settings.setValue("gnss_mqtt_password", self.gnss_mqtt_password_edit.text())
        settings.setValue("gnss_topic", self.gnss_topic_edit.text())
        settings.setValue("gnss_max_distance", self.gnss_max_distance_spin.value())

    def _load_gnss_settings(self):
        """Tải cấu hình GNSS MQTT"""
        settings = QSettings("Aitogy", "MeskernelLaserApp")
        
        host = settings.value("gnss_mqtt_host", "localhost")
        self.gnss_mqtt_host_edit.setText(str(host))
        
        try:
            port = int(settings.value("gnss_mqtt_port", 1883))
            self.gnss_mqtt_port_spin.setValue(port)
        except:
            pass
            
        username = settings.value("gnss_mqtt_username", "")
        self.gnss_mqtt_username_edit.setText(str(username))
        
        password = settings.value("gnss_mqtt_password", "")
        self.gnss_mqtt_password_edit.setText(str(password))
        
        topic = settings.value("gnss_topic", "device/+/upload")
        self.gnss_topic_edit.setText(str(topic))
        
        try:
            dist = float(settings.value("gnss_max_distance", 10.0))
            self.gnss_max_distance_spin.setValue(dist)
        except:
            pass

    def disconnect(self):
        """Ngắt kết nối khi đóng ứng dụng"""
        try:
            if self.publisher:
                self.publisher.disconnect()
            if self.gnss_service:
                self._stop_gnss_service()
        except Exception:
            pass
        finally:
            self._set_connected_ui(False)
