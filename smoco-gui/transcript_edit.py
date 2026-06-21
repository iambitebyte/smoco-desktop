"""
转录文本交互组件
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QTextEdit, QMenu, QApplication
)
from PyQt6.QtGui import QAction, QTextCursor
from PyQt6.QtCore import Qt

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n


class InteractiveTranscriptEdit(QTextEdit):
    """可交互的转录文本编辑器"""

    def __init__(self):
        super().__init__()

        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 12px;
                background-color: #f5f5f5;
                font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
        """)

        # 存储每行的原始数据
        self._line_data = []  # [(timestamp, text, entry_id), ...]

    def append_line(self, timestamp: str, text: str, entry_id: int = None):
        """追加一行转录文本"""
        line = f"{timestamp} {text}"
        self.append(line)

        # 存储行数据
        self._line_data.append((timestamp, text, entry_id))

    def get_current_line_data(self):
        """获取当前行的数据"""
        cursor = self.textCursor()
        line_num = cursor.blockNumber()
        if 0 <= line_num < len(self._line_data):
            return self._line_data[line_num]
        return None

    def get_selected_text(self):
        """获取选中的文本（只包含转录内容，不含时间戳）"""
        cursor = self.textCursor()
        text = cursor.selectedText()
        if not text:
            return ""

        # 移除时间戳前缀（格式：HH:MM:SS 文本）
        lines = text.split("\n")
        clean_lines = []
        for line in lines:
            # 查找时间戳后的第一个空格
            if " " in line and line.index(" ") == 9:  # 时间戳格式 "00:00:00 "
                clean_lines.append(line[10:])
            else:
                clean_lines.append(line)
        return "\n".join(clean_lines)

    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = self.createStandardContextMenu()

        # 添加自定义菜单项
        menu.addSeparator()

        copy_text_action = QAction(i18n.t("copy_transcript"), self)
        copy_text_action.triggered.connect(self._copy_transcript_text)
        menu.addAction(copy_text_action)

        copy_timestamp_action = QAction(i18n.t("copy_with_timestamp"), self)
        copy_timestamp_action.triggered.connect(self._copy_with_timestamp)
        menu.addAction(copy_timestamp_action)

        menu.exec(event.globalPos())

    def _copy_transcript_text(self):
        """复制转录文本（不含时间戳）"""
        text = self.get_selected_text()
        if not text:
            # 如果没有选中，复制当前行
            data = self.get_current_line_data()
            if data:
                text = data[1]  # 只复制文本

        if text:
            QApplication.clipboard().setText(text)

    def _copy_with_timestamp(self):
        """复制带时间戳的文本"""
        text = self.textCursor().selectedText()
        if not text:
            # 如果没有选中，复制当前行
            data = self.get_current_line_data()
            if data:
                text = f"{data[0]} {data[1]}"

        if text:
            QApplication.clipboard().setText(text)

    def mouseDoubleClickEvent(self, event):
        """双击事件 - 可以扩展为编辑功能"""
        super().mouseDoubleClickEvent(event)
        # TODO: 可以添加双击编辑功能
