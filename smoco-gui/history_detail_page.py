"""
转录历史 - session 详情页（entries 表格 + 单条详情弹窗）

entries 表格只显示 metadata.json 里已有的摘要（id/timestamp/text 预览）。
译文列在 metadata 里没有，保持空，详情弹窗加载完整翻译。
"""

import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QTextEdit, QMessageBox, QFileDialog, QAbstractItemView,
)

if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from gui_logger import get_gui_logger
from history_reader import get_session_entries, get_entry_detail, export_session, build_translation_index, EntrySummary
from paths import get_smoco_data_dir

logger = get_gui_logger(__name__)


PAGE_SIZE = 50


def _format_session_id(session_id: str) -> str:
    """YYYYMMDD_HHMMSS → YYYY-MM-DD HH:MM:SS"""
    try:
        dt = datetime.strptime(session_id, "%Y%m%d_%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return session_id


class _EntriesLoadThread(QThread):
    """异步加载 entries + 整个 session 的翻译索引"""
    entries_loaded = pyqtSignal(list, int, dict)  # (entries, total, translation_index)

    def __init__(self, session_id: str, offset: int, limit: int):
        super().__init__()
        self._session_id = session_id
        self._offset = offset
        self._limit = limit

    def run(self):
        try:
            entries, total = get_session_entries(self._session_id, self._offset, self._limit)
            session_path = get_smoco_data_dir() / self._session_id
            translation_index = build_translation_index(session_path)
            self.entries_loaded.emit(entries, total, translation_index)
        except Exception as e:
            logger.exception(f"加载 entries 失败: {e}")
            self.entries_loaded.emit([], 0, {})


class EntryDetailDialog(QDialog):
    """单条 entry 详情弹窗：完整原文 + 译文 + 复制按钮"""

    def __init__(self, session_id: str, entry_id: int, parent=None):
        super().__init__(parent)
        self._detail = get_entry_detail(session_id, entry_id)

        if not self._detail:
            QMessageBox.warning(parent, i18n.t("error"), f"Entry {entry_id} not found")
            return

        self.setWindowTitle(i18n.t("history_detail_title").replace("{id}", str(entry_id)))
        self.setMinimumWidth(550)
        self.setMinimumHeight(420)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        time_label = QLabel(f"⏱ {self._detail.timestamp[:19].replace('T', ' ')}")
        time_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(time_label)

        # 原文
        original_label = QLabel("📝 " + i18n.t("history_original_column"))
        original_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(original_label)

        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setPlainText(self._detail.text)
        self.original_text.setStyleSheet(self._text_edit_style())
        layout.addWidget(self.original_text)

        # 译文（如果有）
        if self._detail.translation:
            translation_label = QLabel("🌐 " + i18n.t("history_translation_column"))
            translation_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(translation_label)

            self.translation_text = QTextEdit()
            self.translation_text.setReadOnly(True)
            self.translation_text.setPlainText(self._detail.translation)
            self.translation_text.setStyleSheet(self._text_edit_style())
            layout.addWidget(self.translation_text)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.btn_copy_original = QPushButton(i18n.t("history_copy_original"))
        self.btn_copy_original.setStyleSheet(self._button_style(primary=True))
        self.btn_copy_original.clicked.connect(self._copy_original)
        btn_layout.addWidget(self.btn_copy_original)

        if self._detail.translation:
            self.btn_copy_translation = QPushButton(i18n.t("history_copy_translation"))
            self.btn_copy_translation.setStyleSheet(self._button_style(primary=True))
            self.btn_copy_translation.clicked.connect(self._copy_translation)
            btn_layout.addWidget(self.btn_copy_translation)

        btn_layout.addStretch()

        self.btn_close = QPushButton(i18n.t("history_close"))
        self.btn_close.setStyleSheet(self._button_style(primary=False))
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _copy_original(self):
        QGuiApplication.clipboard().setText(self._detail.text)
        self._flash_button()

    def _copy_translation(self):
        if self._detail.translation:
            QGuiApplication.clipboard().setText(self._detail.translation)
            self._flash_button()

    def _flash_button(self):
        """关闭按钮短暂显示「已复制」反馈"""
        original_text = self.btn_close.text()
        self.btn_close.setText(i18n.t("history_copy_done"))
        QTimer.singleShot(1200, lambda: self.btn_close.setText(original_text))

    @staticmethod
    def _text_edit_style() -> str:
        return """
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """

    @staticmethod
    def _button_style(primary: bool = True) -> str:
        if primary:
            return """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 18px;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #45a049; }
            """
        return """
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 8px 18px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #616161; }
        """


class HistoryDetailPage(QWidget):
    """转录历史 - session 详情页（entries 列表 + 分页 + 导出）"""

    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._session_id: str | None = None
        self._offset = 0
        self._total = 0
        self._entries: list[EntrySummary] = []
        self._load_thread: _EntriesLoadThread | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部栏：返回 + 标题 + 导出
        top_bar = QHBoxLayout()

        self.btn_back = QPushButton("← " + i18n.t("history_back"))
        self.btn_back.setStyleSheet(self._link_button_style())
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)

        top_bar.addStretch()

        self._title_label = QLabel(i18n.t("history_title"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        top_bar.addWidget(self._title_label)

        top_bar.addStretch()

        self.btn_export = QPushButton(i18n.t("history_export_this"))
        self.btn_export.setStyleSheet(self._export_button_style())
        self.btn_export.clicked.connect(self._on_export)
        top_bar.addWidget(self.btn_export)

        layout.addLayout(top_bar)

        # entries 表格
        self.entries_table = QTableWidget()
        self.entries_table.setColumnCount(3)
        self.entries_table.setHorizontalHeaderLabels([
            i18n.t("history_time_column"),
            i18n.t("history_original_column"),
            i18n.t("history_translation_column"),
        ])
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entries_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.entries_table.doubleClicked.connect(self._on_entry_double_clicked)

        header = self.entries_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 180)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.entries_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                gridline-color: #eee;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ccc;
                font-weight: bold;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
        """)
        layout.addWidget(self.entries_table)

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
    def _link_button_style() -> str:
        return """
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
        """

    @staticmethod
    def _export_button_style() -> str:
        return """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """

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
            QPushButton:hover:!disabled { background-color: #e0e0e0; }
            QPushButton:disabled {
                background-color: #fafafa;
                color: #aaa;
            }
        """

    def set_session(self, session_id: str):
        """切换到新 session，重置 offset 并加载"""
        self._session_id = session_id
        self._offset = 0
        self._title_label.setText(_format_session_id(session_id))
        self.refresh()

    def refresh(self):
        if not self._session_id:
            return
        if self._load_thread and self._load_thread.isRunning():
            return

        self.entries_table.setRowCount(1)
        self.entries_table.setItem(0, 0, QTableWidgetItem(i18n.t("history_loading")))

        self._load_thread = _EntriesLoadThread(self._session_id, self._offset, PAGE_SIZE)
        self._load_thread.entries_loaded.connect(self._on_entries_loaded)
        self._load_thread.start()

    def _on_entries_loaded(self, entries: list, total: int, translation_index: dict):
        self._entries = entries
        self._total = total
        self.entries_table.setRowCount(0)

        if not entries:
            self.entries_table.setRowCount(1)
            empty_item = QTableWidgetItem(i18n.t("history_no_entries"))
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.entries_table.setItem(0, 0, empty_item)
        else:
            self.entries_table.setRowCount(len(entries))
            for row, e in enumerate(entries):
                time_str = e.timestamp[:19].replace("T", " ") if e.timestamp else ""
                time_item = QTableWidgetItem(time_str)
                time_item.setData(Qt.ItemDataRole.UserRole, e.id)
                original_item = QTableWidgetItem(e.text_preview)
                original_item.setData(Qt.ItemDataRole.UserRole, e.id)

                # 译文预览（来自 translation_index，截断到 40 字）
                full_translation = translation_index.get(e.id, "")
                if full_translation:
                    preview = full_translation[:40] + ("..." if len(full_translation) > 40 else "")
                else:
                    preview = i18n.t("history_no_translation")
                translation_item = QTableWidgetItem(preview)
                translation_item.setData(Qt.ItemDataRole.UserRole, e.id)

                self.entries_table.setItem(row, 0, time_item)
                self.entries_table.setItem(row, 1, original_item)
                self.entries_table.setItem(row, 2, translation_item)

        self._update_pagination()

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

    def _on_entry_double_clicked(self, index):
        row = index.row()
        item = self.entries_table.item(row, 0)
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if entry_id and self._session_id:
            dialog = EntryDetailDialog(self._session_id, entry_id, self)
            if dialog._detail:
                dialog.exec()

    def _on_export(self):
        if not self._session_id:
            return

        default_name = f"{self._session_id}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            i18n.t("history_export"),
            default_name,
            "Text files (*.txt);;Markdown files (*.md)",
        )
        if not file_path:
            return

        fmt = "markdown" if file_path.lower().endswith(".md") else "txt"

        try:
            export_session(self._session_id, fmt, Path(file_path))
            QMessageBox.information(
                self,
                i18n.t("success"),
                i18n.t("history_export_done").replace("{path}", file_path),
            )
        except Exception as e:
            logger.exception(f"导出失败: {e}")
            QMessageBox.critical(self, i18n.t("error"), f"{e}")

    def update_ui(self):
        self.btn_back.setText("← " + i18n.t("history_back"))
        self.btn_export.setText(i18n.t("history_export_this"))
        self.btn_prev.setText("← " + i18n.t("history_prev_page"))
        self.btn_next.setText(i18n.t("history_next_page") + " →")
        self.entries_table.setHorizontalHeaderLabels([
            i18n.t("history_time_column"),
            i18n.t("history_original_column"),
            i18n.t("history_translation_column"),
        ])
        if self._session_id:
            self._title_label.setText(_format_session_id(self._session_id))
            self.refresh()
