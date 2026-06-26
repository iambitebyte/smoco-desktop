"""
转录历史 - session 列表页

显示所有转录 session（按时间倒序），分页浏览。双击某条进入详情页。
"""

import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
)

if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from gui_logger import get_gui_logger
from history_reader import list_sessions, SessionMeta

logger = get_gui_logger(__name__)


PAGE_SIZE = 20


class _SessionLoadThread(QThread):
    """异步加载 session 列表"""
    sessions_loaded = pyqtSignal(list, int)  # (list[SessionMeta], total)

    def __init__(self, offset: int, limit: int):
        super().__init__()
        self._offset = offset
        self._limit = limit

    def run(self):
        try:
            sessions, total = list_sessions(self._offset, self._limit)
            self.sessions_loaded.emit(sessions, total)
        except Exception as e:
            logger.exception(f"加载 session 列表失败: {e}")
            self.sessions_loaded.emit([], 0)


class HistoryListPage(QWidget):
    """转录历史 - session 列表页"""

    session_selected = pyqtSignal(str)  # session_id
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._offset = 0
        self._total = 0
        self._sessions: list[SessionMeta] = []
        self._load_thread: _SessionLoadThread | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部栏：返回 + 标题
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("← " + i18n.t("history_back"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 6px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()

        self._title_label = QLabel(i18n.t("history_title"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        top_bar.addWidget(self._title_label)
        layout.addLayout(top_bar)

        # session 列表
        self.session_list = QListWidget()
        self.session_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
        """)
        self.session_list.itemDoubleClicked.connect(self._on_session_double_clicked)
        layout.addWidget(self.session_list)

        # 分页栏
        pagination_bar = QHBoxLayout()
        pagination_bar.addStretch()

        self.btn_prev = QPushButton("← " + i18n.t("history_prev_page"))
        self.btn_prev.setEnabled(False)
        self.btn_prev.setStyleSheet(self._pagination_button_style())
        self.btn_prev.clicked.connect(self._on_prev_page)
        pagination_bar.addWidget(self.btn_prev)

        self.page_label = QLabel("")
        self.page_label.setStyleSheet("padding: 0 15px; font-size: 13px;")
        pagination_bar.addWidget(self.page_label)

        self.btn_next = QPushButton(i18n.t("history_next_page") + " →")
        self.btn_next.setEnabled(False)
        self.btn_next.setStyleSheet(self._pagination_button_style())
        self.btn_next.clicked.connect(self._on_next_page)
        pagination_bar.addWidget(self.btn_next)

        pagination_bar.addStretch()
        layout.addLayout(pagination_bar)

        self.setLayout(layout)

    @staticmethod
    def _pagination_button_style() -> str:
        return """
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover:!disabled {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #fafafa;
                color: #aaa;
            }
        """

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        """重新加载 session 列表（当前 offset）"""
        if self._load_thread and self._load_thread.isRunning():
            return

        self.session_list.clear()
        loading_item = QListWidgetItem(i18n.t("history_loading"))
        loading_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.session_list.addItem(loading_item)

        self._load_thread = _SessionLoadThread(self._offset, PAGE_SIZE)
        self._load_thread.sessions_loaded.connect(self._on_sessions_loaded)
        self._load_thread.start()

    def _on_sessions_loaded(self, sessions: list, total: int):
        self._sessions = sessions
        self._total = total
        self.session_list.clear()

        if not sessions:
            empty_item = QListWidgetItem(i18n.t("history_no_sessions"))
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.session_list.addItem(empty_item)
        else:
            for s in sessions:
                display = self._format_session_display(s)
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, s.session_id)
                self.session_list.addItem(item)

        self._update_pagination()

    @staticmethod
    def _format_session_display(s: SessionMeta) -> str:
        time_str = HistoryListPage._format_session_id(s.session_id)
        count_str = i18n.t("history_entry_count").replace("{n}", str(s.total_entries))
        preview = s.preview[:60] + ("..." if len(s.preview) > 60 else "")
        return f"{time_str}  ({count_str})  {preview}"

    @staticmethod
    def _format_session_id(session_id: str) -> str:
        try:
            dt = datetime.strptime(session_id, "%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return session_id

    def _update_pagination(self):
        current_page = self._offset // PAGE_SIZE + 1
        total_pages = max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label.setText(
            i18n.t("history_page_n_of_m")
            .replace("{n}", str(current_page))
            .replace("{m}", str(total_pages))
        )
        self.btn_prev.setEnabled(self._offset > 0)
        self.btn_next.setEnabled(self._offset + PAGE_SIZE < self._total)

    def _on_prev_page(self):
        if self._offset > 0:
            self._offset = max(0, self._offset - PAGE_SIZE)
            self.refresh()

    def _on_next_page(self):
        if self._offset + PAGE_SIZE < self._total:
            self._offset += PAGE_SIZE
            self.refresh()

    def _on_session_double_clicked(self, item: QListWidgetItem):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self.session_selected.emit(session_id)

    def update_ui(self):
        """语言切换时刷新文本"""
        self._title_label.setText(i18n.t("history_title"))
        self.btn_back.setText("← " + i18n.t("history_back"))
        self.btn_prev.setText("← " + i18n.t("history_prev_page"))
        self.btn_next.setText(i18n.t("history_next_page") + " →")
        self.refresh()
