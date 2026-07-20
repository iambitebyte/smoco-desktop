#!/usr/bin/env python3
"""
Lite 版 PyInstaller 打包入口。

与 bundle.py 的区别：在 import 主程序之前设置 SMOCO_LITE=1，
使 features.WHISPER_ENABLED 为 False → 运行时隐藏 Whisper 设置项。
（Whisper 的 Python 模块仍会被打进包，但运行时不调用。）
"""

import os

# 必须在任何 smoco-gui 模块 import 之前设置，features.py 在 import 时读取它
os.environ["SMOCO_LITE"] = "1"

import sys
from pathlib import Path

# 与开发环境一致的 sys.path（PyInstaller 冻结态下不调整）
if not getattr(sys, "frozen", False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

# 显式 import 所有本地模块，确保 PyInstaller 静态分析能发现（与 bundle.py 一致）
import main_window
import gui_logger
import i18n
import paths
import utils
import audio_meter_worker
import asr_worker
import asr_quality
import asr_chunker
import asr_logger
import smoco_stt_worker
import settings_dialog
import startup_dialog
import transcript_edit
import local_whisper_manager
import translation_worker
import llm_client
import history_page
import history_detail_page
import history_reader
import log_viewer_page
import styles
import toast

# 导入并运行主程序
from main import main

if __name__ == "__main__":
    main()
