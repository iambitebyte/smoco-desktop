#!/usr/bin/env python3
"""
Smoco Desktop GUI 应用入口（PyInstaller 入口点）
"""

import sys
import os

# 确保当前目录在 Python 路径中（用于开发环境）
if not getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

# 导入主程序
from main import main

if __name__ == "__main__":
    main()
