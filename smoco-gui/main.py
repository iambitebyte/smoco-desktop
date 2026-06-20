#!/usr/bin/env python3
"""
Smoco Desktop GUI 主入口

运行:
    python main.py
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from main_window import MainWindow
from utils import load_wasapi_devices
from i18n import i18n


def main():
    print("Starting Smoco Desktop GUI...")

    app = QApplication(sys.argv)
    app.setApplicationName("Smoco Desktop")
    app.setOrganizationName("iambitebyte")

    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoco_logo_circle.png")
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_path))
    window.show()

    # 加载设备列表
    print("Loading WASAPI devices...")
    devices = load_wasapi_devices()
    print(f"Found {len(devices)} devices")

    if devices:
        window.load_devices(devices)
    else:
        window._page_selection.device_list.clear()
        window._page_selection.device_list.addItem(i18n.t("no_devices"))
        window._page_selection.btn_start.setEnabled(False)
        print("No WASAPI devices found - please ensure:")
        print("  1. You are on Windows")
        print("  2. pyaudiowpatch is installed")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
