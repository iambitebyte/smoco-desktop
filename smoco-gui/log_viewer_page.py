"""
日志查看页 - 应用内查看 ~/.smoco/logs/ 下的日志

文件结构（来自 gui_logger.py）：
  gui_YYYYMMDD.log    全级别日志
  error_YYYYMMDD.log  仅 ERROR 及以上
"""

import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QCheckBox,
)

if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from gui_logger import get_gui_logger
from paths import get_smoco_log_dir

logger = get_gui_logger(__name__)


MAX_LINES = 5000  # 最多显示尾部 5000 行，避免大文件卡顿


class _LogLoadThread(QThread):
    """异步加载日志文件（尾部 N 行）"""
    log_loaded = pyqtSignal(str, int, int)  # (content, total_lines, file_size_bytes)

    def __init__(self, file_path: Path):
        super().__init__()
        self._file_path = file_path

    def run(self):
        try:
            with open(self._file_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            tail = all_lines[-MAX_LINES:]
            content = "".join(tail)
            size = self._file_path.stat().st_size
            self.log_loaded.emit(content, total, size)
        except Exception as e:
            logger.exception(f"读取日志失败: {e}")
            self.log_loaded.emit(f"[Error loading log: {e}]", 0, 0)


class LogViewerPage(QWidget):
    """日志查看页"""

    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._load_thread: _LogLoadThread | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 顶部栏：返回 + 标题 + 刷新 + 打开目录
        top_bar = QHBoxLayout()

        self.btn_back = QPushButton("← " + i18n.t("history_back"))
        self.btn_back.setObjectName("linkButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)

        top_bar.addStretch()

        title = QLabel(i18n.t("logs_title"))
        title.setStyleSheet("font-weight: bold; font-size: 18px;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.btn_refresh = QPushButton("🔄 " + i18n.t("refresh_logs"))
        self.btn_refresh.setObjectName("secondaryButton")
        self.btn_refresh.setAccessibleName(i18n.t("refresh_logs"))
        self.btn_refresh.setShortcut(QKeySequence("Ctrl+R"))
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        top_bar.addWidget(self.btn_refresh)

        self.btn_open_dir = QPushButton(i18n.t("open_log_dir"))
        self.btn_open_dir.setObjectName("secondaryButton")
        self.btn_open_dir.clicked.connect(self._on_open_dir)
        top_bar.addWidget(self.btn_open_dir)

        layout.addLayout(top_bar)

        # 文件选择栏
        file_bar = QHBoxLayout()

        self.file_combo = QComboBox()
        self.file_combo.setAccessibleName(i18n.t("logs_title"))
        self.file_combo.currentIndexChanged.connect(self._on_file_changed)
        file_bar.addWidget(self.file_combo, 1)

        self.error_only_check = QCheckBox(i18n.t("error_logs_only"))
        self.error_only_check.toggled.connect(self._refresh_file_list)
        file_bar.addWidget(self.error_only_check)

        layout.addLayout(file_bar)

        # 日志内容
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setAccessibleName(i18n.t("logs_title"))
        self.log_view.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                background-color: #fafafa;
            }
        """)
        layout.addWidget(self.log_view, 1)

        # 底部状态栏
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # 快捷键
        QShortcut(QKeySequence("Escape"), self, activated=self.back_requested.emit)

        # 初始加载文件列表
        self._refresh_file_list()

    def showEvent(self, event):
        """每次进入页面时刷新文件列表（可能有新日志）"""
        super().showEvent(event)
        self._refresh_file_list()

    def _refresh_file_list(self):
        """刷新文件下拉"""
        self.file_combo.blockSignals(True)
        self.file_combo.clear()

        log_dir = get_smoco_log_dir()
        if not log_dir.exists():
            self.file_combo.addItem(i18n.t("no_logs"), None)
            self.file_combo.blockSignals(False)
            self.log_view.setPlainText("")
            self.status_label.setText("")
            return

        error_only = self.error_only_check.isChecked()
        prefix = "error_" if error_only else "gui_"

        files = sorted(
            [
                f for f in log_dir.iterdir()
                if f.is_file() and f.name.startswith(prefix) and f.name.endswith(".log")
            ],
            key=lambda f: f.name,
            reverse=True,
        )

        if not files:
            self.file_combo.addItem(i18n.t("no_logs"), None)
            self.file_combo.blockSignals(False)
            self.log_view.setPlainText("")
            self.status_label.setText("")
            return

        for f in files:
            size_kb = f.stat().st_size / 1024
            if size_kb < 1024:
                size_str = f"{size_kb:.0f} KB"
            else:
                size_str = f"{size_kb / 1024:.1f} MB"
            label = f"{f.name}  ({size_str})"
            self.file_combo.addItem(label, str(f))

        self.file_combo.blockSignals(False)
        self._load_current_file()

    def _on_file_changed(self):
        self._load_current_file()

    def _on_refresh_clicked(self):
        self._refresh_file_list()

    def _load_current_file(self):
        file_path_str = self.file_combo.currentData()
        if not file_path_str:
            self.log_view.setPlainText("")
            return

        file_path = Path(file_path_str)
        if not file_path.exists():
            return

        if self._load_thread and self._load_thread.isRunning():
            return

        self.log_view.setPlainText(i18n.t("loading_logs"))
        self.status_label.setText("")

        self._load_thread = _LogLoadThread(file_path)
        self._load_thread.log_loaded.connect(self._on_log_loaded)
        self._load_thread.start()

    def _on_log_loaded(self, content: str, total_lines: int, file_size: int):
        self.log_view.setPlainText(content)

        # 自动滚到底部（最新日志可见）
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

        if file_size == 0:
            self.status_label.setText("")
            return

        if file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.0f} KB"
        else:
            size_str = f"{file_size / 1024 / 1024:.1f} MB"

        shown = min(MAX_LINES, total_lines)
        self.status_label.setText(
            i18n.t("log_status")
            .replace("{shown}", str(shown))
            .replace("{total}", str(total_lines))
            .replace("{size}", size_str)
        )

    def _on_open_dir(self):
        """用系统文件管理打开日志目录"""
        log_dir = get_smoco_log_dir()
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(log_dir)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_dir)])
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as e:
            logger.exception(f"打开日志目录失败: {e}")
