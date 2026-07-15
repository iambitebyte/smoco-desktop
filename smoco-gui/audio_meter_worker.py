"""
音频采集和音量计算 Worker
"""

import sys
import numpy as np
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from smoco.source.wasapi import WASAPILoopbackSource, MicInputSource


class AudioMeterWorker(QObject):
    """音频采集 Worker - 在后台线程运行"""

    level_ready = pyqtSignal(float)  # 信号：音量电平 (0.0 - 1.0)
    audio_ready = pyqtSignal(bytes)   # 信号：原始音频帧 (S16LE)
    error_occurred = pyqtSignal(str)  # 信号：错误信息

    def __init__(self, device_index: int, kind: str = "loopback"):
        super().__init__()
        self.device_index = device_index
        self._kind = kind
        self._source: WASAPILoopbackSource | None = None
        self._running = False

    def start(self):
        """启动音频采集"""
        try:
            source_cls = MicInputSource if self._kind == "input" else WASAPILoopbackSource
            self._source = source_cls(device_index=self.device_index)
            self._source.start()
            self._running = True
            self._process()
        except Exception as e:
            self.error_occurred.emit(f"Failed to start audio: {e}")

    def stop(self):
        """停止音频采集"""
        self._running = False
        if self._source:
            self._source.stop()
            self._source = None

    def _process(self):
        """处理音频数据并计算 RMS"""
        while self._running and self._source:
            frame = self._source.read_frame()
            if frame is None:
                continue

            # 解码 S16LE 音频数据
            audio = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0

            # 计算 RMS
            rms = float(np.sqrt(np.mean(audio ** 2)))

            # 转换为 0-1 范围的显示值（对数刻度）
            # 使用 dB 刻度：20*log10(rms)，然后映射到 0-1
            if rms > 0:
                db = 20 * np.log10(rms)
                # 假设 -60dB 为最小，0dB 为最大
                level = np.clip((db + 60) / 60, 0, 1)
            else:
                level = 0

            self.level_ready.emit(level)
            self.audio_ready.emit(frame)


class AudioMeterController:
    """音频采集控制器 - 管理 Worker 线程"""

    def __init__(self):
        self._thread: QThread | None = None
        self._worker: AudioMeterWorker | None = None

    def start(self, device_index: int, level_callback, error_callback, kind: str = "loopback"):
        """启动音频采集

        Args:
            device_index: WASAPI 设备索引
            level_callback: 音量更新回调 (level: float) -> None
            error_callback: 错误回调 (msg: str) -> None
            kind: "loopback"（扬声器）或 "input"（麦克风）
        """
        self.stop()  # 先停止旧的

        self._thread = QThread()
        self._worker = AudioMeterWorker(device_index, kind=kind)
        self._worker.moveToThread(self._thread)

        # 连接信号
        self._worker.level_ready.connect(level_callback)
        self._worker.error_occurred.connect(error_callback)
        self._thread.started.connect(self._worker.start)

        # 启动线程
        self._thread.start()

    def stop(self):
        """停止音频采集"""
        if self._worker:
            self._worker.stop()
            self._worker = None

        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
