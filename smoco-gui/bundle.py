#!/usr/bin/env python3
"""
PyInstaller 打包入口点
确保所有本地模块被 PyInstaller 正确识别和包含
"""

import sys

# 显式导入所有本地模块，确保 PyInstaller 分析时能发现它们
# 这些导入语句不会被 PyInstaller 优化掉
import main_window
import gui_logger
import i18n
import paths
import utils
import audio_meter_worker
import asr_worker
import asr_chunker
import asr_logger
import settings_dialog
import startup_dialog
import transcript_edit
import local_whisper_manager
import translation_worker
import llm_client

# 导入并运行主程序
from main import main

if __name__ == "__main__":
    main()
