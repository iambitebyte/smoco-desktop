#!/usr/bin/env python3
"""
测试所有模块导入
"""
import sys
import os

# 添加当前目录到 Python 路径
if not getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

print("Python 路径:")
for p in sys.path[:5]:
    print(f"  {p}")

print("\n测试导入模块:")

modules = [
    'PyQt6.QtWidgets',
    'main_window',
    'gui_logger',
    'i18n',
    'paths',
    'utils',
    'audio_meter_worker',
    'asr_worker',
    'asr_chunker',
    'asr_logger',
    'settings_dialog',
    'startup_dialog',
    'transcript_edit',
    'local_whisper_manager',
    'translation_worker',
    'llm_client',
]

for module in modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError as e:
        print(f"  ✗ {module}: {e}")

print("\n测试完成!")
