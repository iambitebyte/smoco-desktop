from __future__ import annotations
import soundfile as sf
import numpy as np
from ..audio import AudioFormat, to_mono, resample, encode_s16le
from .base import SourceError


class FileSource:
    """按 30ms 帧喂 wav，规范化为目标格式（16k mono S16LE）。跨平台，用于开发与测试。"""

    def __init__(self, path: str, target: AudioFormat | None = None,
                 playback_rate: float = 1.0):
        self._path = path
        self._target = target or AudioFormat()
        self._playback_rate = playback_rate
        self._frames: list[bytes] = []
        self._i = 0

    @property
    def audio_format(self) -> AudioFormat:
        return self._target

    def start(self) -> None:
        try:
            data, src_rate = sf.read(self._path, always_2d=True, dtype="float32")
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"无法读取音频文件 {self._path}: {e}") from e
        mono = to_mono(data)                       # (frames,) float32
        resampled = resample(mono, src_rate, self._target.sample_rate)
        if self._playback_rate != 1.0:
            resampled = resample(resampled,
                                 self._target.sample_rate,
                                 int(self._target.sample_rate / self._playback_rate))
        raw = encode_s16le(resampled)
        bpf = self._target.frame_bytes()
        self._frames = [raw[i:i + bpf] for i in range(0, len(raw) - bpf + 1, bpf)]
        self._i = 0

    def read_frame(self) -> bytes | None:
        if self._i >= len(self._frames):
            return None
        f = self._frames[self._i]
        self._i += 1
        return f

    def stop(self) -> None:
        self._frames = []
        self._i = 0
