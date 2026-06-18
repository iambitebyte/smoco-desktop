from __future__ import annotations
from dataclasses import dataclass, field
from .audio import AudioFormat


@dataclass
class Config:
    audio: AudioFormat = field(default_factory=AudioFormat)

    # VAD / chunking
    silence_ms: int = 300          # 静音 >= 此值 -> 切段
    max_chunk_ms: int = 15000      # 段长 >= 此值 -> 强制切
    min_chunk_ms: int = 200        # 段长 < 此值 -> 丢弃
    pad_ms: int = 50               # 切段时尾随 padding
    vad_aggressiveness: int = 2    # 0..3

    # pipeline
    chunk_queue_size: int = 64
    transcriber_concurrency: int = 1
    shutdown_timeout: float = 5.0
    drop_policy: str = "drop_oldest"   # drop_oldest | drop_newest
