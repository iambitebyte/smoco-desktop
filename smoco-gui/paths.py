"""
路径工具 - 跨平台用户目录
"""

import sys
import os
from pathlib import Path

# 添加父目录到 Python 路径
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))


def get_user_home() -> Path:
    """获取用户主目录（跨平台）"""
    return Path.home()


def get_smoco_config_dir() -> Path:
    """获取 smoco 配置目录 ~/.smoco"""
    config_dir = get_user_home() / ".smoco"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_smoco_data_dir() -> Path:
    """获取 smoco 数据目录 ~/.smoco/data"""
    data_dir = get_smoco_config_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_settings_path() -> Path:
    """获取设置文件路径 ~/.smoco/settings.json"""
    return get_smoco_config_dir() / "settings.json"
