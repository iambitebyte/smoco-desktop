"""GUI 工具函数"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))


def load_wasapi_devices(kind: str = "loopback"):
    """加载 WASAPI 设备列表

    Args:
        kind: "loopback"（扬声器/系统输出）或 "input"（麦克风）

    Returns:
        list[dict]: 设备列表 [{"name","is_default","kind",...}, ...]
    """
    log.info(f"Loading WASAPI devices (kind={kind})...")

    try:
        from smoco.source.wasapi import WASAPILoopbackSource, MicInputSource, _AVAILABLE
        log.debug(f"_AVAILABLE = {_AVAILABLE}")

        if not _AVAILABLE:
            log.warning("WASAPI not available on this platform")
            return []

        cls = MicInputSource if kind == "input" else WASAPILoopbackSource
        log.debug(f"Calling {cls.__name__}.list_devices()...")
        devices = cls.list_devices()
        for dev in devices:
            dev["kind"] = kind
        log.info(f"Found {len(devices)} devices (kind={kind})")

        for i, dev in enumerate(devices):
            log.debug(f"  Device {i}: {dev}")

        return devices
    except ImportError as e:
        log.error(f"Failed to import WASAPI source: {e}")
        return []
    except Exception as e:
        log.exception("Error loading devices")
        return []
