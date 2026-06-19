from __future__ import annotations
import asyncio
import wave
from pathlib import Path
from ..audio import AudioChunk
from .base import TranscriptResult


class StubTranscriber:
    """占位实现：立即返回空结果，可选把 chunk 落成 wav 供肉眼检查切分。"""

    def __init__(self, out_dir: str | None = None):
        self.sample_rate = 16000
        self._out_dir = Path(out_dir) if out_dir else None
        if self._out_dir:
            self._out_dir.mkdir(parents=True, exist_ok=True)

    async def transcribe(self, chunk: AudioChunk) -> TranscriptResult:
        await asyncio.sleep(0)
        if self._out_dir and chunk.pcm:
            self._write_wav(chunk)
        return TranscriptResult(
            chunk_id=chunk.id, text="", start_time=chunk.start_time,
            end_time=chunk.end_time, is_final=True, error=None,
        )

    async def close(self) -> None:
        await asyncio.sleep(0)

    def _write_wav(self, chunk: AudioChunk) -> None:
        path = self._out_dir / f"{chunk.id}_{int(chunk.start_time * 1000)}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(chunk.sample_rate)
            w.writeframes(chunk.pcm)
