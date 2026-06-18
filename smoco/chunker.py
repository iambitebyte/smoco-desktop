from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
import itertools
import math
from .audio import AudioFormat, AudioChunk


@runtime_checkable
class Vad(Protocol):
    def is_speech(self, frame: bytes) -> bool: ...


class WebRtcVad:
    """webrtcvad 包装。frame 必须是 10/20/30ms @ 8/16/32/48k。"""
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        import webrtcvad
        self._vad = webrtcvad.Vad(aggressiveness)
        self._rate = sample_rate

    def is_speech(self, frame: bytes) -> bool:
        return self._vad.is_speech(frame, self._rate)


class FakeVad:
    """测试用：按预置布尔序列判定。超出长度返回 False。"""
    def __init__(self, speech_flags: list[bool]):
        self._flags = list(speech_flags)
        self._i = 0

    def is_speech(self, frame: bytes) -> bool:
        if self._i >= len(self._flags):
            return False
        v = self._flags[self._i]
        self._i += 1
        return v


@dataclass
class _Segment:
    frames: list[tuple[float, bytes]] = field(default_factory=list)
    last_speech_time: float | None = None


class Chunker:
    """有状态分段器：逐帧喂入，输出闭合的 AudioChunk。"""

    def __init__(self, vad: Vad, fmt: AudioFormat, *,
                 silence_ms: int = 300, max_chunk_ms: int = 15000,
                 min_chunk_ms: int = 200, pad_ms: int = 50,
                 counter: itertools.count | None = None):
        self._vad = vad
        self._fmt = fmt
        self._frame_s = fmt.frame_ms / 1000.0
        self._silence_frames = max(1, math.ceil(silence_ms / fmt.frame_ms))
        self._max_frames = max(1, math.ceil(max_chunk_ms / fmt.frame_ms))
        self._min_ms = min_chunk_ms
        self._pad_s = pad_ms / 1000.0
        self._ids = counter or itertools.count(1)
        self._seg: _Segment | None = None
        self._silence_run = 0
        self._t = 0.0                       # 当前帧起始时间

    def feed(self, frame: bytes) -> list[AudioChunk]:
        out: list[AudioChunk] = []
        start_t = self._t
        self._t += self._frame_s
        is_speech = self._vad.is_speech(frame)

        if is_speech:
            if self._seg is None:
                self._seg = _Segment()
            self._seg.frames.append((start_t, frame))
            self._seg.last_speech_time = start_t + self._frame_s
            self._silence_run = 0
            if len(self._seg.frames) >= self._max_frames:
                out.append(self._close(forced=True))
        else:
            if self._seg is not None:
                self._seg.frames.append((start_t, frame))
                self._silence_run += 1
                if self._silence_run >= self._silence_frames:
                    out.append(self._close(forced=False))
        return out

    def flush(self) -> list[AudioChunk]:
        if self._seg is not None and self._seg.frames:
            return [self._close(forced=True)]
        return []

    def _close(self, *, forced: bool) -> AudioChunk:
        seg = self._seg
        self._seg = None
        self._silence_run = 0
        assert seg is not None

        if forced and seg.last_speech_time is None:
            # max-cut 但全静音（理论上 feed 不应累积纯静音）——直接丢
            start = seg.frames[0][0]
            return AudioChunk(id=f"c{next(self._ids)}", pcm=b"",
                              start_time=start, end_time=start,
                              sample_rate=self._fmt.sample_rate, is_final=False)

        if not forced:
            # 静音闭合：尾随只保留到 last_speech + pad
            cut = (seg.last_speech_time or 0.0) + self._pad_s
            kept = [(t, b) for (t, b) in seg.frames if t < cut]
            if not kept:
                kept = seg.frames[:1]
        else:
            kept = seg.frames

        start_time = kept[0][0]
        end_time = kept[-1][0] + self._frame_s
        if (end_time - start_time) * 1000 < self._min_ms:
            # 太短：丢弃，返回空 pcm 标记
            return AudioChunk(id=f"c{next(self._ids)}", pcm=b"",
                              start_time=start_time, end_time=end_time,
                              sample_rate=self._fmt.sample_rate,
                              is_final=not forced)

        pcm = b"".join(b for _, b in kept)
        return AudioChunk(id=f"c{next(self._ids)}", pcm=pcm,
                          start_time=start_time, end_time=end_time,
                          sample_rate=self._fmt.sample_rate,
                          is_final=not forced)
