from smoco.audio import AudioFormat
from smoco.chunker import Chunker, FakeVad


_FMT = AudioFormat()


def _frames(plan):
    """plan: [(kind, count), ...] kind in {'s','.'}; 返回 (frames, vad_bools)。"""
    frames, vad = [], []
    for kind, count in plan:
        for _ in range(count):
            vad.append(kind == "s")
            frames.append(b"\x01" * _FMT.frame_bytes() if kind == "s"
                          else b"\x00" * _FMT.frame_bytes())
    return frames, vad


def _run(chunker, frames):
    out = []
    for f in frames:
        out.extend(chunker.feed(f))
    out.extend(chunker.flush())
    return [c for c in out if c.pcm]   # 过滤被丢弃的段


def test_two_utterances_split_by_silence():
    # 8 speech + 12 silence(360ms>300) + 8 speech + 12 silence
    frames, vad = _frames([("s", 8), (".", 12), ("s", 8), (".", 12)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300, min_chunk_ms=200, pad_ms=50)
    chunks = _run(ch, frames)
    assert len(chunks) == 2
    assert all(c.is_final for c in chunks)
    # 每个 chunk >= 8*30ms=240ms
    for c in chunks:
        assert c.end_time - c.start_time >= 0.24 - 1e-6


def test_short_segment_below_min_is_dropped():
    # 3 speech(90ms<200) + 12 silence -> 丢弃
    frames, vad = _frames([("s", 3), (".", 12)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300, min_chunk_ms=200, pad_ms=50)
    assert _run(ch, frames) == []


def test_max_chunk_forces_split_mid_speech():
    # 持续语音 20 帧(600ms)，max_chunk_ms=150(=5帧) -> 强制切成多段，非 final
    frames, vad = _frames([("s", 20)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300,
                 max_chunk_ms=150, min_chunk_ms=0, pad_ms=0)
    chunks = _run(ch, frames)
    assert len(chunks) >= 3
    assert all(not c.is_final for c in chunks)   # 强制切，非自然结束


def test_flush_emits_open_segment():
    # 8 speech 然后直接 flush（无结尾静音）
    frames, vad = _frames([("s", 8)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300, min_chunk_ms=200, pad_ms=0)
    chunks = _run(ch, frames)
    assert len(chunks) == 1
    assert chunks[0].is_final is False            # flush 闭合，非自然静音结束


def test_pad_trims_trailing_silence():
    # 8 speech + 12 silence；pad_ms=30(1帧) -> 段尾只保留 1 帧静音
    frames, vad = _frames([("s", 8), (".", 12)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300, min_chunk_ms=200, pad_ms=30)
    chunks = _run(ch, frames)
    assert len(chunks) == 1
    # start 0, 语音止于 8*30ms=0.24, +pad 0.03 -> end ~0.27
    assert abs(chunks[0].end_time - 0.27) < 1e-6


def test_chunk_ids_are_unique():
    frames, vad = _frames([("s", 8), (".", 12), ("s", 8), (".", 12)])
    ch = Chunker(FakeVad(vad), _FMT, silence_ms=300, min_chunk_ms=200, pad_ms=0)
    chunks = _run(ch, frames)
    assert len({c.id for c in chunks}) == len(chunks)


def test_webrtcvad_runs_on_real_frames():
    # webrtcvad 是硬运行时依赖；这里只断言它能跑通、返回布尔，
    # 不强依赖具体判定结果（不同 webrtcvad 版本/平台可能不同）。
    import numpy as np
    from smoco.chunker import WebRtcVad

    vad = WebRtcVad(aggressiveness=2, sample_rate=16000)
    n = _FMT.frame_samples()                       # 480
    silence = np.zeros(n, dtype="<i2").tobytes()
    rng = np.random.RandomState(0)
    speech = (rng.uniform(-0.8, 0.8, n) * 32767).astype("<i2").tobytes()
    assert isinstance(vad.is_speech(silence), bool)
    assert isinstance(vad.is_speech(speech), bool)
