"""
全局样式加载

从 styles.qss 加载 QSS，应用到 QApplication。
开发环境从源文件加载；打包环境从 _internal/ 加载（PyInstaller --add-data）。
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication


def _qss_path() -> Path:
    """定位 styles.qss 文件位置"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后：_internal/styles.qss
        return Path(sys.executable).parent / "_internal" / "styles.qss"
    # 开发环境：与 styles.py 同目录
    return Path(__file__).parent / "styles.qss"


def load_global_stylesheet(app: QApplication) -> None:
    """读取 styles.qss 并应用为全局样式。文件不存在时静默跳过（不阻塞启动）"""
    qss_file = _qss_path()
    try:
        qss = qss_file.read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except FileNotFoundError:
        # 不阻塞启动，但打印警告让开发者知道
        print(f"[WARN] styles.qss not found at {qss_file}")
    except Exception as e:
        print(f"[WARN] Failed to load styles.qss: {e}")
