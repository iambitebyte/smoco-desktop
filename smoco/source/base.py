from __future__ import annotations
from typing import Protocol, runtime_checkable
from ..audio import AudioFormat


class SourceError(RuntimeError):
    """采集源错误（设备掉线、被占用等）。"""


@runtime_checkable
class AudioSource(Protocol):
    """同步阻塞式采集源，每次返回一个 30ms 帧（已规范化为 16k mono S16LE）。"""

    @property
    def audio_format(self) -> AudioFormat: ...

    def start(self) -> None: ...

    def read_frame(self) -> bytes | None:
        """阻塞直到一帧就绪；返回 None 表示流结束。"""
        ...

    def stop(self) -> None: ...
