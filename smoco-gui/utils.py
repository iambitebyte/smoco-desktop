"""GUI 工具函数"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# 添加父目录到 Python 路径，以便导入 smoco 模块
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))


def load_wasapi_devices():
    """加载 WASAPI 设备列表

    Returns:
        list[dict]: 设备列表 [{"name": "...", "is_default": bool}, ...]
    """
    log.info("Loading WASAPI devices...")

    try:
        log.debug("Importing WASAPILoopbackSource...")
        from smoco.source.wasapi import WASAPILoopbackSource, _AVAILABLE
        log.debug(f"_AVAILABLE = {_AVAILABLE}")

        if not _AVAILABLE:
            log.warning("WASAPI not available on this platform")
            return []

        log.debug("Calling list_devices()...")
        devices = WASAPILoopbackSource.list_devices()
        log.info(f"Found {len(devices)} devices")

        for i, dev in enumerate(devices):
            log.debug(f"  Device {i}: {dev}")

        return devices
    except ImportError as e:
        log.error(f"Failed to import WASAPILoopbackSource: {e}")
        return []
    except Exception as e:
        log.exception("Error loading devices")
        return []
