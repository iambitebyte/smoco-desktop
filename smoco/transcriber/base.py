from __future__ import annotations
from typing import Protocol, TypedDict, runtime_checkable


class TranscriptResult(TypedDict):
    chunk_id: str
    text: str
    start_time: float
    end_time: float
    is_final: bool
    error: str | None


@runtime_checkable
class Transcriber(Protocol):
    sample_rate: int

    async def transcribe(self, chunk) -> TranscriptResult: ...

    async def close(self) -> None: ...
