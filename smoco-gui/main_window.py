"""
主窗口 - 两页设计：设备选择 + 转录显示
"""

import sys
import time
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QProgressBar, QMessageBox,
    QTextEdit, QStackedWidget, QComboBox, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QIcon, QShortcut, QKeySequence, QColor
from audio_meter_worker import AudioMeterController
from asr_worker import ASRController
from smoco_stt_worker import SmocoSttController
from i18n import i18n, LANGUAGES
from settings_dialog import SettingsDialog, SmocoAuthCheckThread
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
    language_changed = pyqtSignal(str)  # 信号：语言切换（lang_code）

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

        # 历史按钮 + 文字
        history_container = QWidget()
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(2)
        history_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_history = QPushButton("📋")
        self.btn_history.setObjectName("iconButton")
        self.btn_history.setToolTip(i18n.t("history"))
        self.btn_history.setAccessibleName(i18n.t("history"))
        self.btn_history.setFixedSize(32, 32)
        self.btn_history.clicked.connect(self.history_requested.emit)
        self.btn_history.setShortcut(QKeySequence("Ctrl+H"))
        history_layout.addWidget(self.btn_history, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_history = QLabel(i18n.t("history"))
        self.lbl_history.setObjectName("iconLabel")
        self.lbl_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_layout.addWidget(self.lbl_history)
        history_container.setLayout(history_layout)
        top_bar.addWidget(history_container)

        # 日志按钮 + 文字
        logs_container = QWidget()
        logs_layout = QVBoxLayout()
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(2)
        logs_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_logs = QPushButton("📜")
        self.btn_logs.setObjectName("iconButton")
        self.btn_logs.setToolTip(i18n.t("logs"))
        self.btn_logs.setAccessibleName(i18n.t("logs"))
        self.btn_logs.setFixedSize(32, 32)
        self.btn_logs.clicked.connect(self.logs_requested.emit)
        self.btn_logs.setShortcut(QKeySequence("Ctrl+L"))
        logs_layout.addWidget(self.btn_logs, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_logs = QLabel(i18n.t("logs"))
        self.lbl_logs.setObjectName("iconLabel")
        self.lbl_logs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logs_layout.addWidget(self.lbl_logs)
        logs_container.setLayout(logs_layout)
        top_bar.addWidget(logs_container)

        # 设置按钮 + 文字
        settings_container = QWidget()
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(2)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("iconButton")
        self.btn_settings.setToolTip(i18n.t("settings"))
        self.btn_settings.setAccessibleName(i18n.t("settings"))
        self.btn_settings.setFixedSize(32, 32)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        self.btn_settings.setShortcut(QKeySequence("Ctrl+,"))
        settings_layout.addWidget(self.btn_settings, alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_settings = QLabel(i18n.t("settings"))
        self.lbl_settings.setObjectName("iconLabel")
        self.lbl_settings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_layout.addWidget(self.lbl_settings)
        settings_container.setLayout(settings_layout)
        top_bar.addWidget(settings_container)

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
        self._row_to_device: list[dict | None] = []  # row -> device（分组标题行用 None 占位）

    def update_ui(self):
        """更新 UI 文本"""
        self._title_label.setText(i18n.t("select_device"))
        self._lang_label.setText(i18n.t("language") + ":")
        self.desc.setText(i18n.t("select_device_desc"))
        self.btn_start.setText(i18n.t("start_transcription"))
        self.lbl_history.setText(i18n.t("history"))
        self.lbl_logs.setText(i18n.t("logs"))
        self.lbl_settings.setText(i18n.t("settings"))
        self.btn_history.setToolTip(i18n.t("history"))
        self.btn_logs.setToolTip(i18n.t("logs"))
        self.btn_settings.setToolTip(i18n.t("settings"))

    def load_devices(self, devices: list):
        """加载设备列表（按 扬声器/麦克风 分组）"""
        self._devices = devices
        self.device_list.clear()
        # row -> device dict（分组标题行用 None 占位，不可选）
        self._row_to_device: list[dict | None] = []

        loopback_devs = [d for d in devices if d.get("kind") != "input"]
        input_devs = [d for d in devices if d.get("kind") == "input"]

        def _add_section(title: str):
            item = QListWidgetItem(title)
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可选、不响应
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            item.setForeground(QColor(120, 120, 120))
            self.device_list.addItem(item)
            self._row_to_device.append(None)

        def _add_device(dev: dict):
            name = dev.get("name", "Unknown")
            is_default = " ✓" if dev.get("is_default") else ""
            self.device_list.addItem(f"{name}{is_default}")
            self._row_to_device.append(dev)

        if loopback_devs:
            _add_section(i18n.t("speaker"))
            for d in loopback_devs:
                _add_device(d)
        if input_devs:
            _add_section(i18n.t("microphone"))
            for d in input_devs:
                _add_device(d)

        # 默认选中第一个"默认"设备，否则第一个可选设备
        rows = list(enumerate(self._row_to_device))
        default_row = next((i for i, d in rows if d and d.get("is_default")), None)
        if default_row is None:
            default_row = next((i for i, d in rows if d), None)
        if default_row is not None:
            self.device_list.setCurrentRow(default_row)
            self.btn_start.setEnabled(True)
        else:
            self.btn_start.setEnabled(False)

    def selected_device(self) -> dict | None:
        """获取当前选中的设备"""
        row = self.device_list.currentRow()
        if 0 <= row < len(self._row_to_device):
            return self._row_to_device[row]
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
        self.language_changed.emit(lang_code)

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
        # Smoco 流式：当前临时行（中间结果），收到最终结果时转正
        self._interim_row = None

    def update_ui(self):
        """更新 UI 文本"""
        self._title_label.setText(i18n.t("realtime_transcript"))
        self.btn_stop.setText(i18n.t("stop"))

    def start_recording(self):
        """开始录制"""
        self._start_time = time.time()
        self.transcript_table.setRowCount(0)
        self._transcript_data.clear()
        self._interim_row = None

    def _fmt_time(self, total_seconds: float) -> str:
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def set_interim(self, text: str, start_time: float):
        """Smoco 中间增量结果：更新/创建临时行（灰色斜体），不提交翻译"""
        if self._start_time is None or not text:
            return
        if self._interim_row is None:
            row = self.transcript_table.rowCount()
            self.transcript_table.insertRow(row)
            timestamp = self._fmt_time(start_time)

            time_item = QTableWidgetItem(timestamp)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.transcript_table.setItem(row, 0, time_item)

            asr_item = QTableWidgetItem(text)
            asr_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            _f = asr_item.font()
            _f.setItalic(True)
            asr_item.setFont(_f)
            asr_item.setForeground(QColor(120, 120, 120))
            self.transcript_table.setItem(row, 1, asr_item)

            trans_item = QTableWidgetItem("")
            trans_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.transcript_table.setItem(row, 2, trans_item)

            self._interim_row = row
            self._transcript_data[row] = {
                "entry_id": None, "timestamp": timestamp,
                "asr_text": text, "translation": "", "row": row,
            }
            self.transcript_table.resizeRowToContents(row)
            self.transcript_table.scrollToBottom()
        else:
            row = self._interim_row
            item = self.transcript_table.item(row, 1)
            if item:
                item.setText(text)
                self._transcript_data[row]["asr_text"] = text
                self.transcript_table.resizeRowToContents(row)
                self.transcript_table.scrollToBottom()

    def append_text(self, text: str, chunk_start_time: float, entry_id: int = 0):
        """追加转录文本（带时间戳）。若有 Smoco 临时行则转正为最终文本。"""
        if self._start_time is None:
            return

        timestamp = self._fmt_time(chunk_start_time)

        # Smoco 流式：把临时行转正为最终结果（恢复正常样式 + 记录 entry_id）
        if self._interim_row is not None:
            row = self._interim_row
            self._interim_row = None
            asr_item = self.transcript_table.item(row, 1)
            if asr_item:
                asr_item.setText(text)
                _f = asr_item.font()
                _f.setItalic(False)
                asr_item.setFont(_f)
                asr_item.setForeground(QColor(0, 0, 0))
            self._transcript_data[row] = {
                "entry_id": entry_id, "timestamp": timestamp,
                "asr_text": text, "translation": "", "row": row,
            }
            self.transcript_table.resizeRowToContents(row)
            self.transcript_table.scrollToBottom()
            return

        # Whisper 路径（无临时行）：新增一行
        row = self.transcript_table.rowCount()
        self.transcript_table.insertRow(row)

        time_item = QTableWidgetItem(timestamp)
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 0, time_item)

        asr_item = QTableWidgetItem(text)
        asr_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 1, asr_item)

        trans_item = QTableWidgetItem("")
        trans_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_table.setItem(row, 2, trans_item)

        self._transcript_data[row] = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "asr_text": text,
            "translation": "",
            "row": row
        }

        self.transcript_table.resizeRowToContents(row)
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

        # 语言切换 → 刷新所有 page 的 UI 文本
        self._page_selection.language_changed.connect(self._apply_language_change)

        # 控制器
        self._meter_controller = AudioMeterController()
        self._asr_controller = ASRController()
        self._smoco_controller = SmocoSttController()
        self._active_asr = None  # 当前在用的 ASR 控制器（Whisper 或 Smoco）
        self._translation_controller = TranslationController()
        self._device_refresh_thread = None  # 设备刷新线程
        self._startup_smoco_thread = None   # 启动时验证 smoco 账户的线程
        self._is_running = False
        self._source_lang = "ja"  # 转录来源语言
        self._translate_lang = None  # 翻译目标语言

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

        # 启动后异步验证已配置的 smoco 账户（失效则提示）
        QTimer.singleShot(800, self._startup_validate_smoco)

    def load_devices(self, devices: list):
        """加载设备列表"""
        self._page_selection.load_devices(devices)

    def _show_history_detail(self, session_id: str):
        """切换到 session 详情页"""
        self._page_history_detail.set_session(session_id)
        self._stack.setCurrentWidget(self._page_history_detail)

    def _apply_language_change(self, _lang_code: str):
        """语言切换后刷新整个 UI 的可见文本"""
        self.setWindowTitle(i18n.t("window_title"))
        for page in (
            self._page_selection,
            self._page_transcript,
            self._page_history,
            self._page_history_detail,
            self._page_logs,
        ):
            if hasattr(page, "update_ui"):
                page.update_ui()

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
            smoco_cfg = self._settings.get("smoco_stt", {})
            smoco_configured = bool(smoco_cfg.get("email") and smoco_cfg.get("password"))
            if not servers and not local_manager.is_running and not smoco_configured:
                QMessageBox.warning(
                    self,
                    i18n.t("start_failed"),
                    i18n.t("need_server_config")
                )
                # 自动打开设置，定位到本地 Whisper 模型 tab
                self._show_settings(initial_tab=SettingsDialog.TAB_LOCAL_WHISPER)
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
            dialog = ASRStartupDialog(servers, last_server, llm_ok, smoco_configured, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            selected_server = dialog.get_selected_server()
            selected_lang = dialog.get_selected_language()
            selected_translate_lang = dialog.get_selected_translate_language()
            use_prompt = dialog.get_use_prompt()
            source_type = dialog.get_source_type()

            # 记录上次选择（Whisper 源记 url；Smoco 源记 sentinel）
            self._settings["last_server"] = selected_server
            self._source_lang = selected_lang
            self._translate_lang = selected_translate_lang

            # 启动音频采集（两种源共用同一套 16k/mono/S16LE 帧）
            self._meter_controller.start(
                device_index=device["index"],
                kind=device.get("kind", "loopback"),
                level_callback=self._page_transcript.audio_meter.update_level,
                error_callback=self._on_meter_error
            )

            # 按源类型分流到对应 ASR 控制器
            if source_type == "smoco":
                self._smoco_controller.set_config(
                    host=smoco_cfg.get("host", "https://dx-smoco-dev.sony.com.cn"),
                    email=smoco_cfg.get("email", ""),
                    password=smoco_cfg.get("password", ""),
                    language=selected_lang,
                    service_type="local",
                    use_punctuator=smoco_cfg.get("use_punctuator", True),
                    verify_ssl=smoco_cfg.get("verify_ssl", False),
                )
                self._active_asr = self._smoco_controller
                self._smoco_controller.start(
                    transcript_callback=self._on_transcript_ready,
                    interim_callback=self._on_interim_ready,
                    error_callback=self._on_asr_error,
                )
            else:
                # 应用设置到 Whisper ASR 控制器
                self._asr_controller.set_config(
                    api_url=selected_server,
                    language=selected_lang
                )
                self._asr_controller.set_use_prompt(use_prompt)
                vad_params = self._settings.get("vad", {})
                self._asr_controller.set_vad_params(**vad_params)
                self._active_asr = self._asr_controller
                self._asr_controller.start(
                    transcript_callback=self._on_transcript_ready,
                    error_callback=self._on_asr_error
                )

            # 启动翻译（如果选择了翻译语言）
            if self._translate_lang:
                self._translation_controller.set_language(self._source_lang, self._translate_lang)
                self._translation_controller.start(
                    translation_callback=self._page_transcript.update_translation,
                    error_callback=self._on_translation_error
                )

            # 连接音频到当前 ASR 控制器
            if hasattr(self._meter_controller, '_worker') and self._meter_controller._worker:
                self._meter_controller._worker.audio_ready.connect(self._active_asr.submit_audio)

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
        if self._active_asr:
            self._active_asr.stop()
        self._active_asr = None
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

    def _on_interim_ready(self, text: str, start_time: float):
        """Smoco 中间增量结果：刷新临时行（不提交翻译）"""
        self._page_transcript.set_interim(text, start_time)

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

    def _show_settings(self, initial_tab: int = 0):
        """显示设置对话框，可选指定初始 tab（见 SettingsDialog.TAB_*）"""
        dialog = SettingsDialog(self, initial_tab=initial_tab)
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

    def _startup_validate_smoco(self):
        """启动后若记录了 smoco 账户，异步验证登录；失败则提示账户不可用。"""
        smoco = self._settings.get("smoco_stt", {})
        email = smoco.get("email", "")
        password = smoco.get("password", "")
        if not email or not password:
            return  # 未配置，跳过
        host = smoco.get("host", "https://dx-smoco-dev.sony.com.cn")
        verify_ssl = smoco.get("verify_ssl", False)
        if self._startup_smoco_thread and self._startup_smoco_thread.isRunning():
            return
        self._startup_smoco_thread = SmocoAuthCheckThread(host, email, password, verify_ssl)
        self._startup_smoco_thread.finished.connect(self._on_startup_smoco_validated)
        self._startup_smoco_thread.start()

    def _on_startup_smoco_validated(self, result: tuple):
        """启动验证完成：失败则提示用户账户不可用。"""
        if not self.isVisible():
            return
        ok, msg = result
        if not ok:
            logger.warning(f"smoco 启动验证失败: {msg}")
            QMessageBox.warning(
                self,
                i18n.t("window_title"),
                f"{i18n.t('smoco_account_unavailable')}（{msg}）"
            )

    def closeEvent(self, event):
        """窗口关闭时检查状态：转录中禁止关闭；并检查 Local Whisper 服务"""
        logger.info("应用正在关闭...")

        # 正在转录：不允许关闭，必须先停止转录
        if self._is_running:
            QMessageBox.warning(self, i18n.t("window_title"), i18n.t("cannot_close_while_transcribing"))
            event.ignore()
            return

        # 无论是否在录制，都要停止翻译控制器（防止后台线程继续运行）
        self._translation_controller.stop()

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
        """显示 Local Whisper 仍在运行的警告，提供打开设置按钮"""
        from PyQt6.QtWidgets import QMessageBox

        logger.warning(f"阻止关闭应用：Local Whisper 服务正在运行 (端口 {port})")

        message = (
            f"Local Whisper 服务正在运行 (端口 {port})\n\n"
            f"请先停止服务后再关闭应用。\n\n"
            f"点击「打开设置」将跳转到「本地 Whisper 模型」选项卡停止服务。"
        )

        reply = QMessageBox.question(
            self,
            "Local Whisper 服务正在运行",
            message,
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Open,
        )

        if reply == QMessageBox.StandardButton.Open:
            logger.info("用户选择打开设置以停止 Local Whisper 服务")
            self._show_settings(initial_tab=SettingsDialog.TAB_LOCAL_WHISPER)
        else:
            logger.info("用户取消关闭（未打开设置）")


class DeviceRefreshThread(QThread):
    """设备刷新线程 - 异步加载音频设备列表"""

    finished = pyqtSignal(list)  # 信号：刷新完成，传递设备列表

    def run(self):
        """执行设备刷新（同时加载 扬声器 loopback 与 麦克风 input）"""
        try:
            from utils import load_wasapi_devices
            devices = load_wasapi_devices("loopback") + load_wasapi_devices("input")
            self.finished.emit(devices)
        except Exception as e:
            from gui_logger import get_gui_logger
            logger = get_gui_logger(__name__)
            logger.error(f"设备刷新失败: {e}")
            self.finished.emit([])  # 出错时返回空列表
