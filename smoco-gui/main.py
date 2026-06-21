#!/usr/bin/env python3
"""
Smoco Desktop GUI 主入口

运行:
    python main.py
"""

import sys
import os

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from main_window import MainWindow
from utils import load_wasapi_devices
from i18n import i18n
from gui_logger import setup_gui_logger, get_gui_logger


def main():
    # 初始化日志系统
    logger = setup_gui_logger()
    logger.info("正在启动 Smoco Desktop GUI...")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Smoco Desktop")
        app.setOrganizationName("iambitebyte")

        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoco_logo_circle.png")
        app.setWindowIcon(QIcon(icon_path))
        logger.debug(f"应用图标路径: {icon_path}")

        window = MainWindow()
        window.setWindowIcon(QIcon(icon_path))
        window.show()
        logger.info("主窗口已显示")

        # 加载设备列表
        logger.info("正在加载 WASAPI 设备...")
        devices = load_wasapi_devices()
        logger.info(f"找到 {len(devices)} 个音频设备")

        if devices:
            window.load_devices(devices)
            logger.info("设备列表已加载到窗口")
        else:
            window._page_selection.device_list.clear()
            window._page_selection.device_list.addItem(i18n.t("no_devices"))
            window._page_selection.btn_start.setEnabled(False)
            logger.warning("未找到 WASAPI 设备")
            logger.warning("请确保:")
            logger.warning("  1. 你正在使用 Windows 系统")
            logger.warning("  2. pyaudiowpatch 已正确安装")

        logger.info("开始运行应用事件循环")
        exit_code = app.exec()
        logger.info(f"应用退出，退出码: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.exception(f"应用启动失败: {e}")
        logger.error("详细错误信息已记录到日志文件")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
