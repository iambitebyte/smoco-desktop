from __future__ import annotations
from .base import AudioSource
from ..audio import frame_rms


class MeteringSource:
    """装饰任意 AudioSource：透传帧，并实时更新 latest_rms / latest_peak。"""

    def __init__(self, inner: AudioSource):
        self._inner = inner
        self.latest_rms: float = 0.0
        self.latest_peak: float = 0.0

    @property
    def audio_format(self):
        return self._inner.audio_format

    def start(self) -> None:
        self._inner.start()

    def read_frame(self) -> bytes | None:
        frame = self._inner.read_frame()
        if frame:
            rms = frame_rms(frame, self._inner.audio_format.sample_width)
            self.latest_rms = rms
            if rms > self.latest_peak:
                self.latest_peak = rms
        return frame

    def stop(self) -> None:
        self._inner.stop()
