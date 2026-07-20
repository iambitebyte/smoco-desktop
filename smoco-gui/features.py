"""
构建/运行特性开关。

Lite 模式（仅 Smoco 云端 ASR，不含本地 Whisper）：由环境变量 SMOCO_LITE=1 开启。
lite 打包入口 bundle_lite.py 会在 import main 之前设置该变量；
开发预览可直接 `SMOCO_LITE=1 python main.py`。默认（不设置）= Full 版。
"""

import os

LITE_MODE = os.environ.get("SMOCO_LITE", "0") == "1"
# 是否启用本地 Whisper 相关功能（服务器列表 / VAD / 本地 Whisper 模型）
WHISPER_ENABLED = not LITE_MODE
