"""
主窗口 - 两页设计：设备选择 + 转录显示
"""

import sys
import time
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QProgressBar, QMessageBox,
    QTextEdit, QStackedWidget, QComboBox, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from audio_meter_worker import AudioMeterController
from asr_worker import ASRController
from i18n import i18n, LANGUAGES
from settings_dialog import SettingsDialog
from paths import get_settings_path
from startup_dialog import ASRStartupDialog
from transcript_edit import InteractiveTranscriptEdit
from local_whisper_manager import get_local_whisper_manager
from translation_worker import TranslationController
from PyQt6.QtCore import QTimer
from gui_logger import get_gui_logger

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

# 获取日志记录器
logger = get_gui_logger(__name__)


class CompactAudioMeter(QWidget):
    """紧凑型音量条"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(8)
        self._level = 0.0

    def update_level(self, level: float):
        """更新音量显示"""
        self._level = level
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QBrush
        from PyQt6.QtCore import QRect

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        rect = self.rect()
        painter.fillRect(rect, QColor(220, 220, 220))

        # 音量条 (绿色到红色渐变)
        level = self._level

        if level > 0:
            width = int(rect.width() * level)
            bar_rect = QRect(0, 0, width, rect.height())

            # 颜色从绿到红
            if level < 0.5:
                color = QColor(76, 175, 80)  # 绿
            elif level < 0.8:
                color = QColor(255, 193, 7)  # 黄
            else:
                color = QColor(244, 67, 54)  # 红

            painter.fillRect(bar_rect, color)


class SpeakerSelectionPage(QWidget):
    """第一页：设备选择"""

    start_asr = pyqtSignal(dict)  # 信号：开始 ASR，传递设备信息
    settings_requested = pyqtSignal()  # 信号：打开设置

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 顶部栏：标题 + 语言选择 + 设置按钮
        top_bar = QHBoxLayout()

        self._title_label = QLabel(i18n.t("select_device"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        top_bar.addWidget(self._title_label)

        top_bar.addStretch()

        # 设置按钮
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setToolTip(i18n.t("settings"))
        self.btn_settings.setFixedSize(32, 32)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 16px;
            }
        """)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        top_bar.addWidget(self.btn_settings)

        # 语言选择
        self._lang_label = QLabel(i18n.t("language") + ":")
        top_bar.addWidget(self._lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([name for _, name in LANGUAGES])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top_bar.addWidget(self.lang_combo)

        layout.addLayout(top_bar)

        # 说明
        self.desc = QLabel(i18n.t("select_device_desc"))
        layout.addWidget(self.desc)

        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
        """)
        layout.addWidget(self.device_list)

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = QPushButton(i18n.t("start_transcription"))
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_start)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # 存储设备列表
        self._devices: list[dict] = []

    def update_ui(self):
        """更新 UI 文本"""
        self._title_label.setText(i18n.t("select_device"))
        self._lang_label.setText(i18n.t("language") + ":")
        self.desc.setText(i18n.t("select_device_desc"))
        self.btn_start.setText(i18n.t("start_transcription"))
        self.btn_settings.setToolTip(i18n.t("settings"))

    def load_devices(self, devices: list):
        """加载设备列表"""
        self._devices = devices
        self.device_list.clear()
        for i, device in enumerate(devices):
            name = device.get("name", "Unknown")
            is_default = " ✓" if device.get("is_default") else ""
            self.device_list.addItem(f"{name}{is_default}")

        # 默认选中默认设备
        if self._devices:
            default_idx = next((i for i, d in enumerate(devices) if d.get("is_default")), 0)
            self.device_list.setCurrentRow(default_idx)
            self.btn_start.setEnabled(True)

    def selected_device(self) -> dict | None:
        """获取当前选中的设备"""
        row = self.device_list.currentRow()
        if 0 <= row < len(self._devices):
            return self._devices[row]
        return None

    def _on_start_clicked(self):
        """开始按钮点击"""
        device = self.selected_device()
        if device:
            self.start_asr.emit(device)

    def _on_language_changed(self, index: int):
        """语言切换"""
        lang_code, _ = LANGUAGES[index]
        i18n.set_language(lang_code)
        self.update_ui()


class TranscriptPage(QWidget):
    """第二页：转录显示"""

    stop_requested = pyqtSignal()  # 信号：停止录制

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 顶部栏
        top_bar = QHBoxLayout()

        # Logo（小尺寸）
        logo_path = Path(__file__).parent / "smoco_logo_circle.png"
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            scaled_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio)
            logo_label.setPixmap(scaled_pixmap)
            top_bar.addWidget(logo_label)

        # 标题
        self._title_label = QLabel(i18n.t("realtime_transcript"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        top_bar.addWidget(self._title_label)

        top_bar.addStretch()

        # 停止按钮
        self.btn_stop = QPushButton(i18n.t("stop"))
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        top_bar.addWidget(self.btn_stop)

        layout.addLayout(top_bar)

        # 紧凑音量条
        self.audio_meter = CompactAudioMeter()
        layout.addWidget(self.audio_meter)

        # 转录翻译表格
        self.transcript_table = QTableWidget()
        self.transcript_table.setColumnCount(3)
        self.transcript_table.setHorizontalHeaderLabels(["时间", "转录文本", "翻译"])
        self.transcript_table.horizontalHeader().setStretchLastSection(True)
        self.transcript_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transcript_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 启用自动换行
        self.transcript_table.setWordWrap(True)
        # 自适应行高
        self.transcript_table.resizeRowsToContents()
        self.transcript_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ccc;
                font-weight: bold;
            }
        """)
        # 设置列宽
        header = self.transcript_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # 设置行高自适应
        self.transcript_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.transcript_table)

        self.setLayout(layout)

        self._start_time = None
        # 存储转录数据 {row_id: {entry_id, timestamp, asr_text, translation}}
        self._transcript_data = {}

    def update_ui(self):
        """更新 UI 文本"""
        self._title_label.setText(i18n.t("realtime_transcript"))
        self.btn_stop.setText(i18n.t("stop"))

    def start_recording(self):
        """开始录制"""
        self._start_time = time.time()
        self.transcript_table.setRowCount(0)
        self._transcript_data.clear()

    def append_text(self, text: str, chunk_start_time: float, entry_id: int = 0):
        """追加转录文本（带时间戳）"""
        if self._start_time is None:
            return

        # 计算从 chunk 开始到现在的总时间
        total_seconds = chunk_start_time

        # 格式化为 HH:MM:SS
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # 添加到表格
        row = self.transcript_table.rowCount()
        self.transcript_table.insertRow(row)

        # 时间戳
        time_item = QTableWidgetItem(timestamp)
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 0, time_item)

        # ASR 文本
        asr_item = QTableWidgetItem(text)
        asr_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 1, asr_item)

        # 翻译（初始为空）
        trans_item = QTableWidgetItem("")
        trans_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 2, trans_item)

        # 存储数据
        self._transcript_data[row] = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "asr_text": text,
            "translation": "",
            "row": row
        }

        # 调整行高以适应内容
        self.transcript_table.resizeRowToContents(row)

        # 滚动到底部
        self.transcript_table.scrollToBottom()

    def update_translation(self, translations: list):
        """更新翻译文本
        Args:
            translations: [(entry_id, translation), ...]
        """
        for entry_id, translation in translations:
            # 查找对应的行
            for row_id, data in self._transcript_data.items():
                if data["entry_id"] == entry_id:
                    # 更新翻译
                    trans_item = self.transcript_table.item(data["row"], 2)
                    if trans_item:
                        trans_item.setText(translation)
                        data["translation"] = translation
                        # 调整行高以适应新内容
                        self.transcript_table.resizeRowToContents(data["row"])
                    break


class MainWindow(QMainWindow):
    """主窗口 - 两页设计"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(i18n.t("window_title"))
        self.setMinimumSize(700, 600)

        # 页面容器
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # 第一页：设备选择
        self._page_selection = SpeakerSelectionPage()
        self._page_selection.start_asr.connect(self._start_asr)
        self._page_selection.settings_requested.connect(self._show_settings)
        self._stack.addWidget(self._page_selection)

        # 第二页：转录显示
        self._page_transcript = TranscriptPage()
        self._page_transcript.stop_requested.connect(self._stop_asr)
        self._stack.addWidget(self._page_transcript)

        # 控制器
        self._meter_controller = AudioMeterController()
        self._asr_controller = ASRController()
        self._translation_controller = TranslationController()
        self._is_running = False
        self._translate_lang = None  # 翻译语言

        # 设置
        self._settings = {
            "servers": [],
            "last_server": "",
            "vad": {
                "silence_ms": 600,
                "max_chunk_ms": 15000,
                "min_chunk_ms": 500,
                "pad_ms": 100,
            }
        }
        self._load_settings()

        # 默认显示设备选择页
        self._stack.setCurrentWidget(self._page_selection)

    def load_devices(self, devices: list):
        """加载设备列表"""
        self._page_selection.load_devices(devices)

    def _start_asr(self, device: dict):
        """开始 ASR"""
        try:
            # 检查服务器配置
            servers = self._settings.get("servers", [])
            if not servers:
                QMessageBox.warning(
                    self,
                    i18n.t("start_failed"),
                    i18n.t("need_server_config")
                )
                return

            last_server = self._settings.get("last_server", "")

            # 自动验证 LLM 配置
            from llm_client import get_llm_client
            llm_client = get_llm_client()
            llm_ok, llm_msg = llm_client.validate()
            print(f"[LLM 自动验证] {'成功' if llm_ok else '失败'}: {llm_msg}")

            # 显示启动对话框（服务器选择 + 健康检查 + 语言选择）
            dialog = ASRStartupDialog(servers, last_server, llm_ok, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            selected_server = dialog.get_selected_server()
            selected_lang = dialog.get_selected_language()
            selected_translate_lang = dialog.get_selected_translate_language()

            # 更新上次使用的服务器
            self._settings["last_server"] = selected_server
            self._translate_lang = selected_translate_lang
            self._settings["last_server"] = selected_server

            # 应用设置到 ASR 控制器
            self._asr_controller.set_config(
                api_url=selected_server,
                language=selected_lang
            )

            # 应用 VAD 参数
            vad_params = self._settings.get("vad", {})
            self._asr_controller.set_vad_params(**vad_params)

            # 启动音频采集
            self._meter_controller.start(
                device_index=device["index"],
                level_callback=self._page_transcript.audio_meter.update_level,
                error_callback=self._on_meter_error
            )

            # 启动 ASR
            self._asr_controller.start(
                transcript_callback=self._on_transcript_ready,
                error_callback=self._on_asr_error
            )

            # 启动翻译（如果选择了翻译语言）
            if self._translate_lang:
                self._translation_controller.set_language(self._translate_lang)
                self._translation_controller.start(
                    translation_callback=self._page_transcript.update_translation,
                    error_callback=self._on_translation_error
                )

            # 连接音频到 ASR
            if hasattr(self._meter_controller, '_worker') and self._meter_controller._worker:
                self._meter_controller._worker.audio_ready.connect(self._asr_controller.submit_audio)

            self._is_running = True
            self._page_transcript.start_recording()
            self._stack.setCurrentWidget(self._page_transcript)

        except Exception as e:
            logger.exception(f"启动 ASR 失败: {e}")
            QMessageBox.critical(
                self,
                i18n.t("start_failed"),
                i18n.t("unable_to_start") + f" {e}"
            )

    def _stop_asr(self):
        """停止 ASR"""
        self._asr_controller.stop()
        self._meter_controller.stop()
        self._translation_controller.stop()
        self._is_running = False
        self._stack.setCurrentWidget(self._page_selection)

    def _on_meter_error(self, msg: str):
        """音频错误"""
        logger.error(f"音频采集错误: {msg}")
        self._stop_asr()
        QMessageBox.critical(
            self,
            i18n.t("audio_error"),
            i18n.t("audio_capture_failed") + msg
        )

    def _on_asr_error(self, msg: str):
        """ASR 错误"""
        # 不停止，只记录警告
        logger.warning(f"ASR 错误: {msg}")

    def _on_transcript_ready(self, text: str, chunk_start_time: float, entry_id: int):
        """转录完成回调"""
        # 添加到表格
        self._page_transcript.append_text(text, chunk_start_time, entry_id)

        # 提交翻译任务（带上下文）
        if self._translate_lang and self._translation_controller._worker:
            # 获取最近的 N 条转录作为上下文
            context_length = self._settings.get("llm", {}).get("context_length", 5)
            recent_entries = []
            transcript_data = self._page_transcript._transcript_data
            for row_id in sorted(transcript_data.keys())[-context_length:]:
                data = transcript_data[row_id]
                recent_entries.append({
                    "id": data["entry_id"],
                    "text": data["asr_text"]
                })

            # 提交翻译
            if recent_entries:
                from asr_logger import get_asr_logger
                session_dir = get_asr_logger()._session_dir
                self._translation_controller.submit(recent_entries, session_dir)

    def _on_translation_error(self, entry_id: int, error_msg: str):
        """翻译错误"""
        logger.error(f"翻译错误 (entry_id={entry_id}): {error_msg}")

    def _load_settings(self):
        """加载设置"""
        import json
        config_file = get_settings_path()
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)

                # 配置 LLM 客户端
                llm_config = self._settings.get("llm", {})
                if llm_config:
                    from llm_client import get_llm_client
                    llm_client = get_llm_client()
                    llm_client.set_config(
                        base_url=llm_config.get("base_url", ""),
                        api_key=llm_config.get("api_key", ""),
                        model=llm_config.get("model", "")
                    )
                    logger.info(f"LLM 配置已加载: {llm_config.get('model', 'unknown')}")
            except Exception as e:
                logger.error(f"加载设置失败: {e}")

    def _show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings = dialog.get_settings()
            logger.info("设置已保存")

            # 配置 LLM 客户端
            llm_config = self._settings.get("llm", {})
            if llm_config:
                from llm_client import get_llm_client
                llm_client = get_llm_client()
                llm_client.set_config(
                    base_url=llm_config.get("base_url", ""),
                    api_key=llm_config.get("api_key", ""),
                    model=llm_config.get("model", "")
                )
                logger.info(f"LLM 配置已更新: {llm_config.get('model', 'unknown')}")

    def closeEvent(self, event):
        """窗口关闭时检查 Local Whisper 状态"""
        logger.info("应用正在关闭...")

        if self._is_running:
            self._stop_asr()

        # 检查 Local Whisper 服务状态
        local_manager = get_local_whisper_manager()
        port = local_manager._config.get('port', 8000)

        # 检查服务是否还在运行
        has_service = self._check_local_whisper_service(port)

        if has_service:
            logger.warning(f"Local Whisper 服务仍在运行 (端口 {port})")
            self._show_local_whisper_running_warning(port)
            event.ignore()  # 阻止窗口关闭
            return

        logger.info("应用关闭完成")
        super().closeEvent(event)

    def _check_local_whisper_service(self, port: int) -> bool:
        """检查本地 Whisper 服务是否正在运行"""
        try:
            import requests
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
            return response.status_code == 200
        except:
            return False

    def _show_local_whisper_running_warning(self, port: int):
        """显示 Local Whisper 仍在运行的警告"""
        from PyQt6.QtWidgets import QMessageBox

        logger.warning(f"阻止关闭应用：Local Whisper 服务正在运行 (端口 {port})")

        message = (
            f"Local Whisper 服务正在运行 (端口 {port})\n\n"
            f"请先手动停止服务后再关闭应用：\n"
            f"1. 点击「设定」按钮\n"
            f"2. 切换到「本地 Whisper 模型」选项卡\n"
            f"3. 点击「停止服务」按钮\n\n"
            f"是否强制关闭应用？\n"
            f"(可能会导致服务残留，需要手动终止进程)"
        )

        reply = QMessageBox.question(
            self,
            "Local Whisper 服务正在运行",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.warning("用户选择强制关闭应用（可能有服务残留）")
            # 允许关闭
        else:
            logger.info("用户取消关闭，需要先停止 Local Whisper 服务")
            # 阻止关闭 - 已经在 closeEvent 中调用 event.ignore()
