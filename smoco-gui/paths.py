"""
路径工具 - 跨平台用户目录
"""

import sys
import os
from pathlib import Path


def get_smoco_root() -> Path:
    """获取 smoco 项目根目录（支持开发环境和打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：从可执行文件位置推断
        exe_dir = Path(sys.executable).parent
        # 优先检查 _internal 目录（PyInstaller 打包结构）
        if (exe_dir / "_internal" / "whisper-local").exists():
            return exe_dir / "_internal"
        # 检查 exe 父目录是否有 whisper-local
        if (exe_dir.parent / "whisper-local").exists():
            return exe_dir.parent
        # 检查 exe 同级目录
        if (exe_dir / "whisper-local").exists():
            return exe_dir
        # 默认返回 _internal 目录
        return exe_dir / "_internal"
    else:
        # 开发环境：从 __file__ 推断
        return Path(__file__).parent.parent


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


def get_smoco_log_dir() -> Path:
    """获取 smoco 日志目录 ~/.smoco/logs"""
    log_dir = get_smoco_config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_settings_path() -> Path:
    """获取设置文件路径 ~/.smoco/settings.json"""
    return get_smoco_config_dir() / "settings.json"


# 注意：不再在模块级别修改 sys.path，避免路径混乱
# 各个模块在导入时根据需要自行处理
