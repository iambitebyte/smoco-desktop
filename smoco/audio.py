from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.signal import resample_poly


@dataclass(frozen=True)
class AudioFormat:
    """Canonical pipeline format: 16 kHz mono 16-bit PCM, 30 ms frames."""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2          # bytes (S16LE)
    frame_ms: int = 30

    def frame_samples(self) -> int:
        # samples per frame (incl. all channels)
        return int(self.sample_rate * self.frame_ms / 1000) * self.channels

    def frame_bytes(self) -> int:
        return self.frame_samples() * self.sample_width


@dataclass(frozen=True)
class AudioChunk:
    id: str
    pcm: bytes                      # S16LE mono at sample_rate
    start_time: float               # seconds, pipeline-relative
    end_time: float
    sample_rate: int
    is_final: bool = True


def to_mono(samples: np.ndarray) -> np.ndarray:
    """float32 ndarray -> mono float32. Averages channels if >1D."""
    if samples.ndim == 1:
        return samples.astype(np.float32, copy=False)
    # shape (frames, channels) -> mean across channels
    return samples.astype(np.float32).mean(axis=1)


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Anti-aliased resample of mono float32 via polyphase filter."""
    if src_rate == dst_rate:
        return samples.astype(np.float32, copy=False)
    from math import gcd
    g = gcd(int(src_rate), int(dst_rate))
    up = dst_rate // g
    down = src_rate // g
    return resample_poly(samples, up, down).astype(np.float32)


def encode_s16le(samples: np.ndarray) -> bytes:
    """float32 [-1,1] -> little-endian int16 bytes, clipping to [-1,1]."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def frame_rms(pcm: bytes, sample_width: int = 2) -> float:
    """S16LE（默认）PCM 帧的 RMS 电平，归一化到 [0,1]。
    全静音 -> 0.0；满幅 -> ≈1.0；空数据 -> 0.0。"""
    if not pcm:
        return 0.0
    arr = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(arr * arr)))
