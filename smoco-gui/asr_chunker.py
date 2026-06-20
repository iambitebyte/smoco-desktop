"""
音频分块器 - VAD 断句
"""

import sys
import logging
import itertools
import math
from dataclasses import dataclass, field
from pathlib import Path

# 添加父目录到 Python 路径
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))

from smoco.audio import AudioChunk

logging.getLogger("webrtcvad").setLevel(logging.WARNING)


class WebRtcVad:
    """WebRTC VAD 包装"""
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        import webrtcvad
        self._vad = webrtcvad.Vad(aggressiveness)
        self._rate = sample_rate

    def is_speech(self, frame: bytes) -> bool:
        """判断帧是否为语音"""
        return self._vad.is_speech(frame, self._rate)


@dataclass
class _Segment:
    frames: list[tuple[float, bytes]] = field(default_factory=list)
    last_speech_time: float | None = None


class AudioChunker:
    """VAD 分块器 - 按静音断句"""

    def __init__(self, sample_rate: int = 16000, frame_ms: int = 30, *,
                 silence_ms: int = 600,
                 max_chunk_ms: int = 15000,
                 min_chunk_ms: int = 500,
                 pad_ms: int = 100):
        """
        Args:
            sample_rate: 采样率 (16k)
            frame_ms: 帧长度 (30ms)
            silence_ms: 静音多久后断句 (默认 600ms，比原来 300ms 宽松)
            max_chunk_ms: 最大块长度
            min_chunk_ms: 最小块长度
            pad_ms: 断句后保留的尾部静音
        """
        self._vad = WebRtcVad(sample_rate=sample_rate)
        self._frame_s = frame_ms / 1000.0
        self._silence_frames = max(1, math.ceil(silence_ms / frame_ms))
        self._max_frames = max(1, math.ceil(max_chunk_ms / frame_ms))
        self._min_ms = min_chunk_ms
        self._pad_s = pad_ms / 1000.0
        self._ids = itertools.count(1)
        self._seg: _Segment | None = None
        self._silence_run = 0
        self._t = 0.0

    def feed(self, frame: bytes) -> list[tuple[bytes, float]]:
        """喂入音频帧，返回 (pcm, start_time) 列表"""
        out: list[tuple[bytes, float]] = []
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
                result = self._close(forced=True)
                if result:
                    out.append(result)
        else:
            if self._seg is not None:
                self._seg.frames.append((start_t, frame))
                self._silence_run += 1
                if self._silence_run >= self._silence_frames:
                    result = self._close(forced=False)
                    if result:
                        out.append(result)
        return out

    def flush(self) -> list[tuple[bytes, float]]:
        """刷新，返回所有剩余块"""
        if self._seg is not None and self._seg.frames:
            result = self._close(forced=True)
            if result:
                return [result]
        return []

    def _close(self, *, forced: bool) -> tuple[bytes, float] | None:
        """关闭当前段，返回 (pcm, start_time) 或 None"""
        seg = self._seg
        self._seg = None
        self._silence_run = 0
        assert seg is not None

        if forced and seg.last_speech_time is None:
            # 强制闭合但全是静音 - 丢弃
            return None

        if not forced:
            # 静音闭合：只保留到 last_speech + pad
            cut = (seg.last_speech_time or 0.0) + self._pad_s
            kept = [(t, b) for (t, b) in seg.frames if t < cut]
            if not kept:
                kept = seg.frames[:1]
        else:
            kept = seg.frames

        start_time = kept[0][0]
        end_time = kept[-1][0] + self._frame_s
        if (end_time - start_time) * 1000 < self._min_ms:
            # 太短 - 丢弃
            return None

        pcm = b"".join(b for _, b in kept)
        return (pcm, start_time)
