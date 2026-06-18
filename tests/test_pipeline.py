import asyncio
from smoco.audio import AudioFormat, AudioChunk
from smoco.chunker import Chunker, FakeVad
from smoco.config import Config
from smoco.pipeline import Pipeline
from smoco.source.base import AudioSource
from smoco.transcriber.base import TranscriptResult


class FakeSource:
    """按预置帧序列产出，结束后返回 None。"""
    def __init__(self, frames, fmt):
        self._frames = list(frames)
        self._i = 0
        self.audio_format = fmt

    def start(self): pass
    def stop(self): pass
    def read_frame(self):
        if self._i >= len(self._frames):
            return None
        f = self._frames[self._i]; self._i += 1
        return f


class FakeTranscriber:
    def __init__(self):
        self.sample_rate = 16000
        self.received: list[AudioChunk] = []
        self.closed = False

    async def transcribe(self, chunk):
        self.received.append(chunk)
        return TranscriptResult(chunk_id=chunk.id, text=f"t{chunk.id}",
                                start_time=chunk.start_time,
                                end_time=chunk.end_time,
                                is_final=chunk.is_final, error=None)

    async def close(self):
        self.closed = True


_FMT = AudioFormat()


def _frames(plan):
    frames, vad = [], []
    for kind, count in plan:
        for _ in range(count):
            vad.append(kind == "s")
            frames.append(b"\x01" * _FMT.frame_bytes() if kind == "s"
                          else b"\x00" * _FMT.frame_bytes())
    return frames, vad


def test_pipeline_end_to_end_two_chunks():
    frames, vad = _frames([("s", 8), (".", 12), ("s", 8), (".", 12)])
    cfg = Config(min_chunk_ms=200, silence_ms=300, pad_ms=0)
    src = FakeSource(frames, _FMT)
    tr = FakeTranscriber()
    pipe = Pipeline(src, Chunker(FakeVad(vad), _FMT,
                                 silence_ms=cfg.silence_ms,
                                 min_chunk_ms=cfg.min_chunk_ms, pad_ms=cfg.pad_ms),
                    tr, cfg)
    asyncio.run(pipe.run())

    assert len(tr.received) == 2
    assert tr.closed
    ids = [c.id for c in tr.received]
    assert len(set(ids)) == 2


def test_pipeline_skips_empty_pcm_chunks():
    # 3 speech(90ms) 被 min_chunk_ms 丢弃，不应到达 transcriber
    frames, vad = _frames([("s", 3), (".", 12)])
    cfg = Config(min_chunk_ms=200, silence_ms=300, pad_ms=0)
    src = FakeSource(frames, _FMT)
    tr = FakeTranscriber()
    pipe = Pipeline(src, Chunker(FakeVad(vad), _FMT,
                                 silence_ms=cfg.silence_ms,
                                 min_chunk_ms=cfg.min_chunk_ms, pad_ms=cfg.pad_ms),
                    tr, cfg)
    asyncio.run(pipe.run())
    assert tr.received == []
    assert tr.closed


def test_pipeline_handles_transcriber_error_without_dying():
    class BoomTranscriber:
        sample_rate = 16000
        def __init__(self): self.count = 0; self.closed = False
        async def transcribe(self, chunk):
            self.count += 1
            return TranscriptResult(chunk_id=chunk.id, text="",
                                    start_time=chunk.start_time,
                                    end_time=chunk.end_time,
                                    is_final=chunk.is_final, error="boom")
        async def close(self):
            self.closed = True

    frames, vad = _frames([("s", 8), (".", 12), ("s", 8), (".", 12)])
    cfg = Config(min_chunk_ms=200, silence_ms=300, pad_ms=0)
    src = FakeSource(frames, _FMT)
    tr = BoomTranscriber()
    pipe = Pipeline(src, Chunker(FakeVad(vad), _FMT,
                                 silence_ms=cfg.silence_ms,
                                 min_chunk_ms=cfg.min_chunk_ms, pad_ms=cfg.pad_ms),
                    tr, cfg)
    asyncio.run(pipe.run())     # 不应抛
    assert tr.count == 2        # 两个 chunk 都尝试过，错误被吞
    assert tr.closed


def test_pipeline_drops_oldest_under_backpressure():
    # 慢 transcriber + 小队列(=1) -> drop_oldest 丢掉部分 chunk，pipeline 仍正常结束
    class SlowTranscriber:
        sample_rate = 16000
        def __init__(self):
            self.received: list[str] = []
            self.closed = False
        async def transcribe(self, chunk):
            await asyncio.sleep(0.05)   # 慢：每 chunk 50ms
            self.received.append(chunk.id)
            return TranscriptResult(chunk_id=chunk.id, text="",
                                    start_time=chunk.start_time,
                                    end_time=chunk.end_time,
                                    is_final=chunk.is_final, error=None)
        async def close(self):
            self.closed = True

    # 产生 5 个 chunk：(8 speech + 12 silence) × 5
    frames, vad = [], []
    for _ in range(5):
        f, v = _frames([("s", 8), (".", 12)])
        frames += f
        vad += v
    cfg = Config(min_chunk_ms=200, silence_ms=300, pad_ms=0,
                 chunk_queue_size=1, drop_policy="drop_oldest")
    src = FakeSource(frames, _FMT)
    tr = SlowTranscriber()
    pipe = Pipeline(src, Chunker(FakeVad(vad), _FMT,
                                 silence_ms=cfg.silence_ms,
                                 min_chunk_ms=cfg.min_chunk_ms, pad_ms=cfg.pad_ms),
                    tr, cfg)
    asyncio.run(pipe.run())
    assert tr.closed
    assert 1 <= len(tr.received) < 5    # 慢消费 + 队列=1 -> 必有丢弃，但不至于全丢
