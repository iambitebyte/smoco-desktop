"""
Toast 通知组件

提供瞬时反馈（2 秒自动消失），不抢焦点、不阻塞。
用于"复制成功"、"导出完成"等操作反馈，替代部分 QMessageBox。

用法:
    from toast import show_toast
    show_toast(self, "已复制到剪贴板", level="success")

定位：浮在 parent 所属顶层窗口的右下角，跟随窗口缩放。
"""

from typing import Literal

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


Level = Literal["info", "success", "error"]


_LEVEL_STYLES = {
    "info": {"bg": "#333333", "fg": "#ffffff"},
    "success": {"bg": "#4CAF50", "fg": "#ffffff"},
    "error": {"bg": "#f44336", "fg": "#ffffff"},
}


class Toast(QFrame):
    """单个 toast 提示框"""

    def __init__(
        self,
        message: str,
        level: Level = "info",
        duration_ms: int = 2000,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        style = _LEVEL_STYLES.get(level, _LEVEL_STYLES["info"])
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 鼠标穿透 + 不抢焦点，避免影响用户操作
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # WA_StyledBackground 让 QFrame 的 background-color 样式生效
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {style['bg']};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        label = QLabel(message)
        label.setStyleSheet(
            f"color: {style['fg']}; background-color: transparent; font-size: 13px;"
        )
        layout.addWidget(label)

        self.adjustSize()

        # 定位到 parent 右下角
        if parent is not None:
            margin = 20
            x = parent.width() - self.width() - margin
            y = parent.height() - self.height() - margin
            self.move(max(0, x), max(0, y))
            self.raise_()

        self.show()

        # 定时关闭
        QTimer.singleShot(duration_ms, self._close)

    def _close(self):
        self.setParent(None)
        self.deleteLater()


def show_toast(
    parent: QWidget | None,
    message: str,
    level: Level = "info",
    duration_ms: int = 2000,
) -> Toast:
    """在 parent 所属顶层窗口的右下角显示 toast。

    自动找顶层 window，所以无论传 page 还是 dialog，toast 都浮在整个窗口的右下角。
    """
    window = parent.window() if parent is not None else None
    return Toast(message, level, duration_ms, window)
