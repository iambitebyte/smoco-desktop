"""
GUI 应用日志管理

提供统一的日志配置，输出到控制台和文件
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from paths import get_smoco_log_dir


def setup_gui_logger():
    """设置 GUI 应用日志"""

    # 创建日志目录
    log_dir = get_smoco_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日志文件名（按日期）
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"gui_{today}.log"
    error_log_file = log_dir / f"error_{today}.log"

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 创建格式化器
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    # 1. 控制台处理器（INFO 及以上）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器（所有级别）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # 3. 错误日志文件处理器（仅 ERROR 及以上）
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Smoco Desktop GUI 启动")
    logger.info(f"日志目录: {log_dir}")
    logger.info(f"日志文件: {log_file}")
    logger.info(f"错误日志: {error_log_file}")
    logger.info("=" * 60)

    return logger


def get_gui_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name or __name__)


# 全局初始化标志
_logger_initialized = False


def ensure_logger_initialized():
    """确保日志系统已初始化"""
    global _logger_initialized
    if not _logger_initialized:
        setup_gui_logger()
        _logger_initialized = True
