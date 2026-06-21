"""
设置对话框 - Whisper 服务器列表管理
"""

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QPushButton, QDialogButtonBox,
    QGroupBox, QFormLayout, QListWidget, QMessageBox,
    QAbstractItemView, QTabWidget, QWidget, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from paths import get_settings_path
from local_whisper_manager import get_local_whisper_manager, MODELS
from llm_client import get_llm_client


class SettingsDialog(QDialog):
    """设置对话框 - 服务器列表管理"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(i18n.t("settings"))
        self.setMinimumWidth(600)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # === 选项卡 1: 服务器列表 ===
        server_tab = QWidget()
        server_layout = QVBoxLayout()
        server_layout.setSpacing(10)

        # 服务器列表
        self.server_list = QListWidget()
        self.server_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.server_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
        """)
        server_layout.addWidget(self.server_list)
        # 连接选择变化信号
        self.server_list.itemSelectionChanged.connect(self._on_selection_changed)

        # 添加/删除服务器按钮
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton(i18n.t("add_server"))
        self.btn_add.clicked.connect(self._add_server)
        btn_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton(i18n.t("remove_server"))
        self.btn_remove.setEnabled(False)  # 初始禁用
        self.btn_remove.clicked.connect(self._remove_server)
        btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()

        self.btn_set_default = QPushButton(i18n.t("set_default"))
        self.btn_set_default.setEnabled(False)  # 初始禁用
        self.btn_set_default.clicked.connect(self._set_default_server)
        btn_layout.addWidget(self.btn_set_default)

        server_layout.addLayout(btn_layout)

        # 新增服务器输入区
        input_group = QGroupBox(i18n.t("add_server"))
        input_layout = QFormLayout()
        self.new_server_input = QLineEdit()
        self.new_server_input.setPlaceholderText(i18n.t("server_url_placeholder"))
        input_layout.addRow(i18n.t("new_server_url"), self.new_server_input)

        self.server_name_input = QLineEdit()
        self.server_name_input.setPlaceholderText(i18n.t("server_name_placeholder"))
        input_layout.addRow(i18n.t("server_name_optional"), self.server_name_input)
        input_group.setLayout(input_layout)

        server_layout.addWidget(input_group)
        server_layout.addStretch()

        server_tab.setLayout(server_layout)
        self.tab_widget.addTab(server_tab, i18n.t("whisper_servers"))

        # === 选项卡 2: VAD 参数 ===
        vad_tab = QWidget()
        vad_layout = QVBoxLayout()
        vad_layout.setSpacing(15)
        vad_layout.setContentsMargins(20, 20, 20, 20)

        self.silence_ms_spin = QSpinBox()
        self.silence_ms_spin.setRange(100, 2000)
        self.silence_ms_spin.setSuffix(" ms")
        self.silence_ms_spin.setValue(600)

        self.max_chunk_ms_spin = QSpinBox()
        self.max_chunk_ms_spin.setRange(5000, 30000)
        self.max_chunk_ms_spin.setSuffix(" ms")
        self.max_chunk_ms_spin.setValue(15000)

        self.min_chunk_ms_spin = QSpinBox()
        self.min_chunk_ms_spin.setRange(100, 2000)
        self.min_chunk_ms_spin.setSuffix(" ms")
        self.min_chunk_ms_spin.setValue(500)

        self.pad_ms_spin = QSpinBox()
        self.pad_ms_spin.setRange(0, 500)
        self.pad_ms_spin.setSuffix(" ms")
        self.pad_ms_spin.setValue(100)

        # 创建 VAD 参数表单
        vad_form = QFormLayout()
        vad_form.addRow(i18n.t("silence_duration") + ":", self.silence_ms_spin)
        vad_form.addRow(i18n.t("max_chunk_duration") + ":", self.max_chunk_ms_spin)
        vad_form.addRow(i18n.t("min_chunk_duration") + ":", self.min_chunk_ms_spin)
        vad_form.addRow(i18n.t("padding_duration") + ":", self.pad_ms_spin)

        vad_layout.addLayout(vad_form)
        vad_layout.addStretch()

        vad_tab.setLayout(vad_layout)
        self.tab_widget.addTab(vad_tab, i18n.t("vad_parameters"))

        # === 选项卡 3: 本地 Whisper 模型 ===
        local_tab = QWidget()
        local_layout = QVBoxLayout()
        local_layout.setSpacing(15)
        local_layout.setContentsMargins(20, 20, 20, 20)

        # CPU 警告
        warning_label = QLabel(i18n.t("local_cpu_warning"))
        warning_label.setStyleSheet("color: #f57c00; padding: 8px; background-color: #fff3e0; border-radius: 4px;")
        local_layout.addWidget(warning_label)

        # 配置表单
        config_form = QFormLayout()

        # 模型显示（固定为 small）
        for model, desc in MODELS.items():
            model_label = QLabel(f"{model} - {desc}")
            model_label.setStyleSheet("font-weight: bold;")
        config_form.addRow(i18n.t("local_model_size") + ":", model_label)

        # 端口
        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1024, 65535)
        self.local_port_spin.setValue(8000)
        config_form.addRow(i18n.t("local_port") + ":", self.local_port_spin)

        local_layout.addLayout(config_form)

        # 状态显示
        status_layout = QHBoxLayout()
        status_label = QLabel(i18n.t("local_status") + ":")
        self.local_status_label = QLabel(i18n.t("local_status_stopped"))
        self.local_status_label.setStyleSheet("""
            padding: 4px 12px;
            background-color: #e0e0e0;
            border-radius: 4px;
        """)
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.local_status_label)
        status_layout.addStretch()
        local_layout.addLayout(status_layout)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.local_start_btn = QPushButton(i18n.t("local_start"))
        self.local_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.local_start_btn.clicked.connect(self._on_local_start)
        control_layout.addWidget(self.local_start_btn)

        self.local_stop_btn = QPushButton(i18n.t("local_stop"))
        self.local_stop_btn.setEnabled(False)
        self.local_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.local_stop_btn.clicked.connect(self._on_local_stop)
        control_layout.addWidget(self.local_stop_btn)

        control_layout.addStretch()
        local_layout.addLayout(control_layout)

        # 日志输出区域
        log_label = QLabel("服务日志:")
        local_layout.addWidget(log_label)

        self.local_log_output = QTextEdit()
        self.local_log_output.setReadOnly(True)
        self.local_log_output.setMaximumHeight(150)
        self.local_log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        local_layout.addWidget(self.local_log_output)

        local_layout.addStretch()

        local_tab.setLayout(local_layout)
        self.tab_widget.addTab(local_tab, i18n.t("local_whisper_model"))

        # === 选项卡 4: LLM 配置 ===
        llm_tab = QWidget()
        llm_layout = QVBoxLayout()
        llm_layout.setSpacing(15)
        llm_layout.setContentsMargins(20, 20, 20, 20)

        # 说明
        llm_info = QLabel(i18n.t("llm_instructions"))
        llm_info.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        llm_layout.addWidget(llm_info)

        # 配置表单
        llm_form = QFormLayout()

        # Base URL
        self.llm_base_url_input = QLineEdit()
        self.llm_base_url_input.setPlaceholderText(i18n.t("llm_base_url_placeholder"))
        llm_form.addRow(i18n.t("llm_base_url"), self.llm_base_url_input)

        # API Key
        self.llm_api_key_input = QLineEdit()
        self.llm_api_key_input.setPlaceholderText(i18n.t("llm_api_key_placeholder"))
        self.llm_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        llm_form.addRow(i18n.t("llm_api_key"), self.llm_api_key_input)

        # Model ID
        self.llm_model_input = QLineEdit()
        self.llm_model_input.setPlaceholderText(i18n.t("llm_model_placeholder"))
        llm_form.addRow(i18n.t("llm_model"), self.llm_model_input)

        llm_layout.addLayout(llm_form)

        # 验证按钮
        llm_btn_layout = QHBoxLayout()

        self.llm_validate_btn = QPushButton(i18n.t("llm_validate"))
        self.llm_validate_btn.clicked.connect(self._on_llm_validate)
        llm_btn_layout.addWidget(self.llm_validate_btn)

        self.llm_validate_status = QLabel("")
        llm_btn_layout.addWidget(self.llm_validate_status)
        llm_btn_layout.addStretch()

        llm_layout.addLayout(llm_btn_layout)
        llm_layout.addStretch()

        llm_tab.setLayout(llm_layout)
        self.tab_widget.addTab(llm_tab, i18n.t("llm_config"))

        # 连接本地服务状态变化信号
        local_manager = get_local_whisper_manager()
        local_manager.status_changed.connect(self._on_local_status_changed)
        local_manager.error_occurred.connect(self._on_local_error)
        local_manager.output_received.connect(self._on_local_output)

        # 验证线程
        self._validation_thread = None

        # 添加选项卡到主布局
        layout.addWidget(self.tab_widget)

        # 底部按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(i18n.t("save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(i18n.t("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        # 加载设置
        self._load_settings()

    def showEvent(self, event):
        """对话框显示时刷新本地服务状态"""
        super().showEvent(event)
        # 延迟一点刷新，确保对话框已完全显示
        QTimer.singleShot(100, self._refresh_local_status)

    def _refresh_local_status(self):
        """刷新本地服务状态"""
        local_manager = get_local_whisper_manager()
        if local_manager.check_running():
            try:
                import requests
                response = requests.get(f"{local_manager.api_url}/health", timeout=2)
                if response.status_code == 200:
                    result = response.json()
                    running_model = result.get("model", "unknown")
                    if "/" in running_model or "\\" in running_model:
                        running_model = running_model.split("/")[-1].split("\\")[-1]
                    self._on_local_status_changed("running", f"{i18n.t('local_running')} ({running_model})")
                    return
            except:
                pass
        self._on_local_status_changed("stopped", i18n.t("local_status_stopped"))

    def _load_settings(self):
        """从文件加载设置"""
        config_file = get_settings_path()
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)

                # 加载服务器列表
                servers = settings.get("servers", [])
                self._load_servers(servers)

                # 加载 VAD 参数
                vad = settings.get("vad", {})
                self.silence_ms_spin.setValue(vad.get("silence_ms", 600))
                self.max_chunk_ms_spin.setValue(vad.get("max_chunk_ms", 15000))
                self.min_chunk_ms_spin.setValue(vad.get("min_chunk_ms", 500))
                self.pad_ms_spin.setValue(vad.get("pad_ms", 100))

                # 加载本地 Whisper 配置
                local_whisper = settings.get("local_whisper", {})
                model = "small"  # 固定使用 small 模型
                port = local_whisper.get("port", 8000)

                self.local_port_spin.setValue(port)

                # 检查本地服务实际运行状态
                local_manager = get_local_whisper_manager()
                local_manager.set_config(model, port, local_whisper.get("enabled", False))

                # 检查实际是否在运行
                if local_manager.check_running():
                    # 服务正在运行，获取当前模型信息
                    try:
                        import requests
                        response = requests.get(f"{local_manager.api_url}/health", timeout=2)
                        if response.status_code == 200:
                            result = response.json()
                            running_model = result.get("model", "unknown")
                            if "/" in running_model or "\\" in running_model:
                                running_model = running_model.split("/")[-1].split("\\")[-1]
                            self._on_local_status_changed("running", f"{i18n.t('local_running')} ({running_model})")
                        else:
                            self._on_local_status_changed("stopped", i18n.t("local_status_stopped"))
                    except:
                        self._on_local_status_changed("stopped", i18n.t("local_status_stopped"))
                else:
                    self._on_local_status_changed("stopped", i18n.t("local_status_stopped"))
            except Exception as e:
                print(f"加载设置失败: {e}")

            try:
                # 加载 LLM 配置
                llm_config = settings.get("llm", {})
                self.llm_base_url_input.setText(llm_config.get("base_url", ""))
                self.llm_api_key_input.setText(llm_config.get("api_key", ""))
                self.llm_model_input.setText(llm_config.get("model", ""))
            except Exception as e:
                print(f"加载 LLM 配置失败: {e}")

    def _load_servers(self, servers: list):
        """加载服务器列表到 UI"""
        self.server_list.clear()
        for server in servers:
            url = server.get("url", "")
            name = server.get("name", "")
            is_default = server.get("default", False)

            if name:
                display = f"{name} - {url}"
            else:
                display = url

            if is_default:
                display += " ✓"
                # 默认服务器排在最前面
            self.server_list.addItem(display)

    def _on_selection_changed(self):
        """列表选择变化时更新按钮状态"""
        has_selection = self.server_list.currentRow() >= 0
        self.btn_remove.setEnabled(has_selection)
        self.btn_set_default.setEnabled(has_selection)

    def _add_server(self):
        """添加新服务器"""
        url = self.new_server_input.text().strip()
        if not url:
            QMessageBox.warning(self, i18n.t("hint"), i18n.t("hint_enter_url"))
            return

        name = self.server_name_input.text().strip()

        # 检查是否已存在
        for i in range(self.server_list.count()):
            item_text = self.server_list.item(i).text()
            if url in item_text:
                QMessageBox.warning(self, i18n.t("hint"), i18n.t("hint_server_exists"))
                return

        # 添加到列表
        if name:
            display = f"{name} - {url}"
        else:
            display = url

        self.server_list.addItem(display)

        # 清空输入
        self.new_server_input.clear()
        self.server_name_input.clear()

    def _remove_server(self):
        """删除选中的服务器"""
        row = self.server_list.currentRow()
        if row >= 0:
            item = self.server_list.item(row)
            text = item.text()

            # 检查是否是默认服务器
            if "✓" in text:
                QMessageBox.warning(self, i18n.t("hint"), i18n.t("hint_cannot_delete_default"))
                return

            self.server_list.takeItem(row)

    def _set_default_server(self):
        """设置选中的服务器为默认"""
        row = self.server_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, i18n.t("hint"), i18n.t("hint_select_server"))
            return

        # 移除所有 ✓ 标记
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            text = item.text().replace(" ✓", "")
            self.server_list.item(i).setText(text)

        # 在选中项添加 ✓
        item = self.server_list.item(row)
        text = item.text()
        if "✓" not in text:
            self.server_list.item(row).setText(text + " ✓")

        # 将默认服务器移到列表顶部
        default_text = self.server_list.item(row).text()
        self.server_list.takeItem(row)
        self.server_list.insertItem(0, default_text)
        self.server_list.setCurrentRow(0)

    def _save_settings(self):
        """保存设置到文件"""
        config_file = get_settings_path()
        try:
            # 解析服务器列表
            servers = []
            last_server = None

            for i in range(self.server_list.count()):
                item = self.server_list.item(i)
                text = item.text()

                is_default = "✓" in text
                display_text = text.replace(" ✓", "").replace("✓", "")

                # 解析 URL 和名称
                if " - " in display_text:
                    name, url = display_text.split(" - ", 1)
                else:
                    name = ""
                    url = display_text

                server = {
                    "url": url.strip(),
                    "name": name.strip(),
                    "default": is_default
                }
                servers.append(server)

                if is_default:
                    last_server = url.strip()

            settings = {
                "servers": servers,
                "last_server": last_server,
                "vad": {
                    "silence_ms": self.silence_ms_spin.value(),
                    "max_chunk_ms": self.max_chunk_ms_spin.value(),
                    "min_chunk_ms": self.min_chunk_ms_spin.value(),
                    "pad_ms": self.pad_ms_spin.value(),
                },
                "local_whisper": {
                    "model": "small",  # 固定使用 small 模型
                    "port": self.local_port_spin.value(),
                    "enabled": get_local_whisper_manager().is_running,
                },
                "llm": {
                    "base_url": self.llm_base_url_input.text().strip(),
                    "api_key": self.llm_api_key_input.text().strip(),
                    "model": self.llm_model_input.text().strip(),
                }
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")

    def accept(self):
        """确定按钮"""
        if self.server_list.count() == 0:
            QMessageBox.warning(self, i18n.t("hint"), i18n.t("hint_need_server"))
            return

        self._save_settings()
        super().accept()

    def get_settings(self) -> dict:
        """获取当前设置"""
        servers = []
        last_server = None

        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            text = item.text()

            is_default = "✓" in text
            display_text = text.replace(" ✓", "").replace("✓", "")

            if " - " in display_text:
                name, url = display_text.split(" - ", 1)
            else:
                name = ""
                url = display_text

            server = {
                "url": url.strip(),
                "name": name.strip(),
                "default": is_default
            }
            servers.append(server)

            if is_default:
                last_server = url.strip()

        return {
            "servers": servers,
            "last_server": last_server,
            "vad": {
                "silence_ms": self.silence_ms_spin.value(),
                "max_chunk_ms": self.max_chunk_ms_spin.value(),
                "min_chunk_ms": self.min_chunk_ms_spin.value(),
                "pad_ms": self.pad_ms_spin.value(),
            },
            "local_whisper": {
                "model": "small",  # 固定使用 small 模型
                "port": self.local_port_spin.value(),
                "enabled": get_local_whisper_manager().is_running,
            },
            "llm": {
                "base_url": self.llm_base_url_input.text().strip(),
                "api_key": self.llm_api_key_input.text().strip(),
                "model": self.llm_model_input.text().strip(),
            }
        }

    def _on_local_start(self):
        """启动本地 Whisper 服务"""
        model = "small"  # 固定使用 small 模型
        port = self.local_port_spin.value()

        local_manager = get_local_whisper_manager()
        local_manager.set_config(model, port, enabled=True)
        local_manager.start()

    def _on_local_stop(self):
        """停止本地 Whisper 服务"""
        local_manager = get_local_whisper_manager()
        local_manager.stop()

    def _on_local_status_changed(self, status: str, message: str):
        """本地服务状态变化"""
        # 更新状态标签
        self.local_status_label.setText(message)

        # 更新按钮状态
        if status == "running":
            self.local_start_btn.setEnabled(False)
            self.local_stop_btn.setEnabled(True)
            self.local_status_label.setStyleSheet("""
                padding: 4px 12px;
                background-color: #D4EDDA;
                color: #155724;
                border-radius: 4px;
            """)
        elif status == "starting" or status == "downloading":
            self.local_start_btn.setEnabled(False)
            self.local_stop_btn.setEnabled(True)
            self.local_status_label.setStyleSheet("""
                padding: 4px 12px;
                background-color: #FFF3CD;
                color: #856404;
                border-radius: 4px;
            """)
        else:  # stopped
            self.local_start_btn.setEnabled(True)
            self.local_stop_btn.setEnabled(False)
            self.local_status_label.setStyleSheet("""
                padding: 4px 12px;
                background-color: #e0e0e0;
                border-radius: 4px;
            """)

    def _on_local_error(self, message: str):
        """本地服务错误"""
        QMessageBox.warning(self, i18n.t("error"), message)

    def _on_local_output(self, line: str):
        """本地服务输出"""
        # 添加时间戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.local_log_output.append(f"[{timestamp}] {line}")
        # 自动滚动到底部
        cursor = self.local_log_output.textCursor()
        self.local_log_output.setTextCursor(cursor)

    def _on_llm_validate(self):
        """验证 LLM 配置"""
        base_url = self.llm_base_url_input.text().strip()
        api_key = self.llm_api_key_input.text().strip()
        model = self.llm_model_input.text().strip()

        if not all([base_url, api_key, model]):
            QMessageBox.warning(self, i18n.t("hint"), i18n.t("llm_config_incomplete"))
            return

        self.llm_validate_btn.setEnabled(False)
        self.llm_validate_status.setText(i18n.t("llm_validating"))
        self.llm_validate_status.setStyleSheet("color: #f57c00;")

        llm_client = get_llm_client()
        llm_client.set_config(base_url, api_key, model)

        # 清理旧线程
        if self._validation_thread and self._validation_thread.isRunning():
            self._validation_thread.quit()
            self._validation_thread.wait()

        # 异步验证
        self._validation_thread = LLMValidationThread(llm_client)
        self._validation_thread.finished.connect(
            self._on_llm_validation_finished,
            Qt.ConnectionType.QueuedConnection
        )
        self._validation_thread.start()

    def _on_llm_validation_finished(self, result: tuple[bool, str]):
        """LLM 验证完成"""
        # 检查对话框是否还存在
        if not self.isVisible():
            return

        self.llm_validate_btn.setEnabled(True)
        success, message = result

        if success:
            self.llm_validate_status.setText(message)
            self.llm_validate_status.setStyleSheet("color: #28a745;")
        else:
            self.llm_validate_status.setText(message)
            self.llm_validate_status.setStyleSheet("color: #dc3545;")


class LLMValidationThread(QThread):
    """LLM 配置验证线程"""

    finished = pyqtSignal(tuple)  # (success, message)

    def __init__(self, llm_client):
        super().__init__()
        self._llm_client = llm_client

    def run(self):
        """执行验证"""
        result = self._llm_client.validate()
        self.finished.emit(result)

    def closeEvent(self, event):
        """对话框关闭时清理线程"""
        # 清理验证线程
        if self._validation_thread and self._validation_thread.isRunning():
            self._validation_thread.quit()
            self._validation_thread.wait()
        super().closeEvent(event)

