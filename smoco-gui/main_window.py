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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QIcon, QShortcut, QKeySequence
from audio_meter_worker import AudioMeterController
from asr_worker import ASRController
from i18n import i18n, LANGUAGES
from settings_dialog import SettingsDialog
from paths import get_settings_path
from startup_dialog import ASRStartupDialog
from transcript_edit import InteractiveTranscriptEdit
from local_whisper_manager import get_local_whisper_manager
from translation_worker import TranslationController
from history_page import HistoryListPage
from history_detail_page import HistoryDetailPage
from log_viewer_page import LogViewerPage
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
    devices_refresh_requested = pyqtSignal()  # 信号：刷新设备列表
    history_requested = pyqtSignal()  # 信号：打开转录历史
    logs_requested = pyqtSignal()  # 信号：打开日志查看

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

        # 历史按钮
        self.btn_history = QPushButton("📋")
        self.btn_history.setObjectName("iconButton")
        self.btn_history.setToolTip(i18n.t("history"))
        self.btn_history.setAccessibleName(i18n.t("history"))
        self.btn_history.setFixedSize(32, 32)
        self.btn_history.clicked.connect(self.history_requested.emit)
        self.btn_history.setShortcut(QKeySequence("Ctrl+H"))
        top_bar.addWidget(self.btn_history)

        # 日志按钮
        self.btn_logs = QPushButton("📜")
        self.btn_logs.setObjectName("iconButton")
        self.btn_logs.setToolTip(i18n.t("logs"))
        self.btn_logs.setAccessibleName(i18n.t("logs"))
        self.btn_logs.setFixedSize(32, 32)
        self.btn_logs.clicked.connect(self.logs_requested.emit)
        self.btn_logs.setShortcut(QKeySequence("Ctrl+L"))
        top_bar.addWidget(self.btn_logs)

        # 设置按钮
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("iconButton")
        self.btn_settings.setToolTip(i18n.t("settings"))
        self.btn_settings.setAccessibleName(i18n.t("settings"))
        self.btn_settings.setFixedSize(32, 32)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        self.btn_settings.setShortcut(QKeySequence("Ctrl+,"))
        top_bar.addWidget(self.btn_settings)

        # 语言选择
        self._lang_label = QLabel(i18n.t("language") + ":")
        top_bar.addWidget(self._lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([name for _, name in LANGUAGES])
        self.lang_combo.setAccessibleName(i18n.t("language"))
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top_bar.addWidget(self.lang_combo)

        layout.addLayout(top_bar)

        # 说明
        desc_layout = QHBoxLayout()
        self.desc = QLabel(i18n.t("select_device_desc"))
        desc_layout.addWidget(self.desc)
        desc_layout.addStretch()

        # 刷新按钮（小图标）
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("iconButton")
        self.btn_refresh.setToolTip(i18n.t("refresh_devices"))
        self.btn_refresh.setAccessibleName(i18n.t("refresh_devices"))
        self.btn_refresh.setFixedSize(24, 24)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        self.btn_refresh.setShortcut(QKeySequence("Ctrl+R"))
        desc_layout.addWidget(self.btn_refresh)

        layout.addLayout(desc_layout)

        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setObjectName("contentList")
        self.device_list.setAccessibleName(i18n.t("select_device"))
        layout.addWidget(self.device_list)

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = QPushButton(i18n.t("start_transcription"))
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_start.setShortcut(QKeySequence("F5"))
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

    def _on_refresh_clicked(self):
        """刷新设备列表按钮点击"""
        # 显示刷新状态
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("⏳")
        self.desc.setText(i18n.t("loading_devices"))
        self.device_list.clear()
        self.btn_start.setEnabled(False)

        # 发送刷新请求
        self.devices_refresh_requested.emit()
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
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.setShortcut(QKeySequence("Esc"))
        top_bar.addWidget(self.btn_stop)

        layout.addLayout(top_bar)

        # 紧凑音量条
        self.audio_meter = CompactAudioMeter()
        layout.addWidget(self.audio_meter)

        # 转录翻译表格
        self.transcript_table = QTableWidget()
        self.transcript_table.setObjectName("contentTable")
        self.transcript_table.setAccessibleName(i18n.t("realtime_transcript"))
        self.transcript_table.setColumnCount(3)
        self.transcript_table.setHorizontalHeaderLabels(["时间", "转录文本", "翻译"])
        self.transcript_table.horizontalHeader().setStretchLastSection(True)
        self.transcript_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transcript_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 启用自动换行
        self.transcript_table.setWordWrap(True)
        # 自适应行高
        self.transcript_table.resizeRowsToContents()
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
        self._page_selection.devices_refresh_requested.connect(self._refresh_devices)
        self._stack.addWidget(self._page_selection)

        # 第二页：转录显示
        self._page_transcript = TranscriptPage()
        self._page_transcript.stop_requested.connect(self._stop_asr)
        self._stack.addWidget(self._page_transcript)

        # 第三页：转录历史列表
        self._page_history = HistoryListPage()
        self._page_history.session_selected.connect(self._show_history_detail)
        self._page_history.back_requested.connect(lambda: self._stack.setCurrentWidget(self._page_selection))
        self._stack.addWidget(self._page_history)

        # 第四页：转录历史详情
        self._page_history_detail = HistoryDetailPage()
        self._page_history_detail.back_requested.connect(lambda: self._stack.setCurrentWidget(self._page_history))
        self._stack.addWidget(self._page_history_detail)

        # 第五页：日志查看
        self._page_logs = LogViewerPage()
        self._page_logs.back_requested.connect(lambda: self._stack.setCurrentWidget(self._page_selection))
        self._stack.addWidget(self._page_logs)

        # 历史按钮 → 跳转历史页
        self._page_selection.history_requested.connect(lambda: self._stack.setCurrentWidget(self._page_history))

        # 日志按钮 → 跳转日志页
        self._page_selection.logs_requested.connect(lambda: self._stack.setCurrentWidget(self._page_logs))

        # 控制器
        self._meter_controller = AudioMeterController()
        self._asr_controller = ASRController()
        self._translation_controller = TranslationController()
        self._device_refresh_thread = None  # 设备刷新线程
        self._is_running = False
        self._translate_lang = None  # 翻译语言

        # 设置
        self._settings = {
            "servers": [],
            "last_server": "",
            "vad": {
                "silence_ms": 300,
                "max_chunk_ms": 10000,
                "min_chunk_ms": 1000,
                "pad_ms": 100,
            }
        }
        self._load_settings()

        # 默认显示设备选择页
        self._stack.setCurrentWidget(self._page_selection)

    def load_devices(self, devices: list):
        """加载设备列表"""
        self._page_selection.load_devices(devices)

    def _show_history_detail(self, session_id: str):
        """切换到 session 详情页"""
        self._page_history_detail.set_session(session_id)
        self._stack.setCurrentWidget(self._page_history_detail)

    def _refresh_devices(self):
        """刷新设备列表（异步）"""
        # 清理旧线程
        if hasattr(self, '_device_refresh_thread') and self._device_refresh_thread and self._device_refresh_thread.isRunning():
            self._device_refresh_thread.quit()
            self._device_refresh_thread.wait()

        # 启动新的刷新线程
        self._device_refresh_thread = DeviceRefreshThread()
        self._device_refresh_thread.finished.connect(self._on_device_refresh_finished)
        self._device_refresh_thread.start()

    def _on_device_refresh_finished(self, devices: list):
        """设备刷新完成"""
        self.load_devices(devices)

        # 恢复UI状态
        self._page_selection.btn_refresh.setEnabled(True)
        self._page_selection.btn_refresh.setText("🔄")
        self._page_selection.desc.setText(i18n.t("select_device_desc"))

    def _start_asr(self, device: dict):
        """开始 ASR"""
        try:
            # 检查服务器配置：Local Whisper 已启动时不强制要求外部服务器
            servers = self._settings.get("servers", [])
            local_manager = get_local_whisper_manager()
            if not servers and not local_manager.is_running:
                QMessageBox.warning(
                    self,
                    i18n.t("start_failed"),
                    i18n.t("need_server_config")
                )
                return

            last_server = self._settings.get("last_server", "")

            # 检查 LLM 配置是否完整（不发 HTTP 请求，避免 UI 卡顿）
            # 真正的连通性验证留给实际翻译时发现
            llm_config = self._settings.get("llm", {})
            llm_ok = bool(
                llm_config.get("base_url")
                and llm_config.get("api_key")
                and llm_config.get("model")
            )

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


class DeviceRefreshThread(QThread):
    """设备刷新线程 - 异步加载音频设备列表"""

    finished = pyqtSignal(list)  # 信号：刷新完成，传递设备列表

    def run(self):
        """执行设备刷新"""
        try:
            from utils import load_wasapi_devices
            devices = load_wasapi_devices()
            self.finished.emit(devices)
        except Exception as e:
            from gui_logger import get_gui_logger
            logger = get_gui_logger(__name__)
            logger.error(f"设备刷新失败: {e}")
            self.finished.emit([])  # 出错时返回空列表
