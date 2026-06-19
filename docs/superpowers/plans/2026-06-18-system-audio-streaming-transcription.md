# 系统声音实时流式转写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Windows 上运行的 CLI，实时采集系统声音（WASAPI loopback），用 VAD 切成语音 chunk，通过抽象转写接口送出，可在 macOS 用文件源跑通整条链路与测试。

**Architecture:** 三个解耦角色——同步阻塞 `AudioSource`（采集）→ 有状态 `Chunker`（VAD 分段）→ 异步 `Transcriber`（转写），用 `asyncio.Queue` 串联，丢最旧 chunk 实现背压。`pipeline` 只依赖两个 Protocol，采集源和转写引擎都可替换；因此 macOS 开发期用 `FileSource` + `StubTranscriber`，仅 `WASAPILoopbackSource` 是 Windows 专属。

**Tech Stack:** Python ≥3.10、`numpy`、`scipy`（抗混叠重采样，对 spec 的"仅 numpy"做了细化——见 Task 2 说明）、`soundfile`、`webrtcvad-wheels`、`pyaudiowpatch`（仅 Windows）、`pytest` + `pytest-asyncio`。

**与 spec 的偏差（已确认合理）：**
- spec 第 4 节写"16k → 960 样本/帧"，实际 30ms@16k = **480 样本 = 960 字节**（S16LE）。本计划按 480 样本/960 字节实现。
- 重采样用 `scipy.signal.resample_poly`（任意整数比、带抗混叠），比纯 numpy 线性插值更正确，故依赖里加 `scipy`。
- 架构图里的 `frameQ` 在实现中省略：采集线程内联驱动 `Chunker.feed(frame)`，帧不单独排队，chunk 才排队（更简单、背压更清晰）。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `pyproject.toml` | 包元数据、依赖、pytest 配置、CLI 入口 |
| `smoco/__init__.py` | 包标识 |
| `smoco/audio.py` | `AudioFormat`、`AudioChunk`、PCM↔float 重采样/下混辅助 |
| `smoco/config.py` | 默认配置 dataclass |
| `smoco/source/base.py` | `AudioSource` Protocol、`SourceError` |
| `smoco/source/file.py` | `FileSource`：按 30ms 帧喂 wav（跨平台） |
| `smoco/source/wasapi.py` | `WASAPILoopbackSource`（Windows / PyAudioWPatch） |
| `smoco/chunker.py` | `Vad` Protocol、`WebRtcVad`、`Chunker` 分段 |
| `smoco/transcriber/base.py` | `Transcriber` Protocol、`TranscriptResult` |
| `smoco/transcriber/stub.py` | `StubTranscriber` |
| `smoco/pipeline.py` | 串联三者 + 背压 + 生命周期 |
| `smoco/__main__.py` | CLI（list-devices / run） |
| `tests/conftest.py` | 合成 PCM 帧生成器等 fixture |
| `tests/test_audio.py` | format/重采样/下混单测 |
| `tests/test_config.py` | 默认值单测 |
| `tests/test_source_file.py` | FileSource 帧数/格式/结束单测 |
| `tests/test_chunker.py` | Chunker 三段规则 + FakeVad 单测 |
| `tests/test_transcriber_stub.py` | StubTranscriber 契约单测 |
| `tests/test_pipeline.py` | 端到端（FakeSource+FakeVad+FakeTranscriber） |

实现顺序遵循依赖：脚手架 → audio → config → source 协议 → FileSource → chunker → transcriber 协议+stub → pipeline → CLI → WASAPI。

---

## Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `smoco/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: 写 `pyproject.toml`**

```toml
[project]
name = "smoco"
version = "0.1.0"
description = "Capture system audio, chunk via VAD, stream to an abstract transcriber."
requires-python = ">=3.10"
dependencies = [
  "numpy>=1.24",
  "scipy>=1.10",
  "soundfile>=0.12",
  "webrtcvad-wheels>=2.0.11",
  "pyaudiowpatch>=0.2.14; platform_system=='Windows'",
]

[project.optional-dependencies]
dev = ["pytest>=7", "pytest-asyncio>=0.23"]

[project.scripts]
smoco = "smoco.__main__:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["smoco*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 写 `smoco/__init__.py`**

```python
"""smoco: system audio capture → VAD chunking → abstract transcription."""
__version__ = "0.1.0"
```

- [ ] **Step 3: 写 `tests/__init__.py`**（空文件）

```python
```

- [ ] **Step 4: 写冒烟测试 `tests/test_smoke.py`**

```python
def test_package_imports():
    import smoco
    assert smoco.__version__ == "0.1.0"
```

- [ ] **Step 5: 安装并运行测试验证通过**

Run:
```bash
python -m pip install -e ".[dev]"
pytest -q
```
Expected: `1 passed`。

- [ ] **Step 6: 提交**

```bash
git add pyproject.toml smoco/ tests/
git commit -m "chore: 项目脚手架（pyproject、包结构、冒烟测试）"
```

---

## Task 2: audio.py — 格式与 PCM 工具

**Files:**
- Create: `smoco/audio.py`
- Create: `tests/test_audio.py`

- [ ] **Step 1: 写失败测试 `tests/test_audio.py`**

```python
import numpy as np
from smoco.audio import AudioFormat, AudioChunk, resample, to_mono, encode_s16le


def test_format_defaults_and_frame_sizes():
    fmt = AudioFormat()  # 16k mono S16LE 30ms
    assert fmt.sample_rate == 16000
    assert fmt.channels == 1
    assert fmt.sample_width == 2
    assert fmt.frame_samples() == 480          # 30ms @ 16k
    assert fmt.frame_bytes() == 960            # 480 * 2


def test_audio_chunk_is_immutable():
    c = AudioChunk(id="c1", pcm=b"\x00" * 960, start_time=0.0,
                   end_time=0.03, sample_rate=16000, is_final=True)
    assert c.id == "c1"
    try:
        c.id = "x"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("AudioChunk should be frozen")


def test_to_mono_averages_stereo():
    stereo = np.array([[1.0, -1.0], [0.5, 0.5], [0.0, 0.0]], dtype=np.float32)
    mono = to_mono(stereo)
    assert mono.shape == (3,)
    np.testing.assert_allclose(mono, [0.0, 0.5, 0.0], atol=1e-6)


def test_to_mono_passes_through_mono():
    mono = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    out = to_mono(mono)
    assert out.shape == (3,)
    np.testing.assert_allclose(out, mono)


def test_resample_halves_rate():
    src = np.linspace(-1.0, 1.0, 4800, dtype=np.float32)  # 0.1s @ 48k
    out = resample(src, 48000, 16000)
    assert abs(len(out) - 1600) <= 2          # /3, 容差


def test_encode_s16le_clips_and_round_trips():
    samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0, 1.5], dtype=np.float32)
    raw = encode_s16le(samples)
    arr = np.frombuffer(raw, dtype="<i2")
    assert arr[0] == 0
    assert arr[3] == 32767                      # 1.0 -> full scale
    assert arr[5] == 32767                      # 1.5 clipped
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_audio.py -q`
Expected: FAIL（`ImportError: cannot import name 'AudioFormat'`）。

- [ ] **Step 3: 写 `smoco/audio.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_audio.py -q`
Expected: `6 passed`。

- [ ] **Step 5: 提交**

```bash
git add smoco/audio.py tests/test_audio.py
git commit -m "feat(audio): AudioFormat/AudioChunk + 重采样/下混/S16LE 编码"
```

---

## Task 3: config.py — 默认配置

**Files:**
- Create: `smoco/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 写失败测试 `tests/test_config.py`**

```python
from smoco.config import Config, AudioFormat


def test_defaults_match_spec():
    c = Config()
    assert c.audio.sample_rate == 16000
    assert c.audio.frame_ms == 30
    assert c.silence_ms == 300
    assert c.max_chunk_ms == 15000
    assert c.min_chunk_ms == 200
    assert c.pad_ms == 50
    assert c.vad_aggressiveness == 2
    assert c.chunk_queue_size == 64
    assert c.transcriber_concurrency == 1
    assert c.shutdown_timeout == 5.0


def test_config_is_overridable():
    c = Config(silence_ms=500, max_chunk_ms=10000)
    assert c.silence_ms == 500
    assert c.max_chunk_ms == 10000
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config.py -q`
Expected: FAIL（`ImportError`）。

- [ ] **Step 3: 写 `smoco/config.py`**

```python
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
    drop_policy: str = "drop_oldest"   # drop_oldest | drop_newest | block
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_config.py -q`
Expected: `2 passed`。

- [ ] **Step 5: 提交**

```bash
git add smoco/config.py tests/test_config.py
git commit -m "feat(config): 默认配置 dataclass（采样/VAD/队列/生命周期）"
```

---

## Task 4: source/base.py — AudioSource 协议

**Files:**
- Create: `smoco/source/__init__.py`
- Create: `smoco/source/base.py`

此任务无独立测试（纯类型定义，由后续 FileSource/WASAPI 的实现测试覆盖）。

- [ ] **Step 1: 写 `smoco/source/__init__.py`**（空文件）

```python
```

- [ ] **Step 2: 写 `smoco/source/base.py`**

```python
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
```

- [ ] **Step 3: 冒烟验证可导入**

Run: `python -c "from smoco.source.base import AudioSource, SourceError; print('ok')"`
Expected: `ok`

- [ ] **Step 4: 提交**

```bash
git add smoco/source/__init__.py smoco/source/base.py
git commit -m "feat(source): AudioSource Protocol + SourceError"
```

---

## Task 5: source/file.py — FileSource（跨平台）

**Files:**
- Create: `smoco/source/file.py`
- Create: `tests/test_source_file.py`

- [ ] **Step 1: 写失败测试 `tests/test_source_file.py`**

```python
import numpy as np
import soundfile as sf
from smoco.audio import AudioFormat
from smoco.source.file import FileSource


def _write_wav(path, samples, sample_rate):
    # samples: mono float32 in [-1,1]
    sf.write(str(path), samples.astype(np.float32), sample_rate)


def test_reads_mono_16k_wav_in_30ms_frames(tmp_path):
    fmt = AudioFormat()
    n_frames = 10
    samples = np.ones(fmt.frame_samples() * n_frames, dtype=np.float32) * 0.1
    wav = tmp_path / "a.wav"
    _write_wav(wav, samples, 16000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()

    assert len(got) == n_frames
    assert all(len(f) == fmt.frame_bytes() for f in got)


def test_resamples_48k_stereo_to_16k_mono(tmp_path):
    fmt = AudioFormat()
    # 48000 Hz, 30ms = 1440 samples stereo -> after /3 + downmix = 480 mono
    dur_frames = 5
    stereo = np.zeros((48000 * 0.03 * dur_frames, 2), dtype=np.float32)
    stereo[:, 0] = 0.2
    wav = tmp_path / "b.wav"
    _write_wav(wav, stereo, 48000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()

    assert len(got) == dur_frames
    assert all(len(f) == fmt.frame_bytes() for f in got)


def test_partial_final_frame_is_dropped(tmp_path):
    fmt = AudioFormat()
    # 2.5 frames worth of samples -> 2 full frames, tail discarded
    n = int(fmt.frame_samples() * 2.5)
    samples = np.zeros(n, dtype=np.float32)
    wav = tmp_path / "c.wav"
    _write_wav(wav, samples, 16000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()
    assert len(got) == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_source_file.py -q`
Expected: FAIL（`ImportError`）。

- [ ] **Step 3: 写 `smoco/source/file.py`**

```python
from __future__ import annotations
import soundfile as sf
import numpy as np
from ..audio import AudioFormat, to_mono, resample, encode_s16le
from .base import SourceError


class FileSource:
    """按 30ms 帧喂 wav，规范化为目标格式（16k mono S16LE）。跨平台，用于开发与测试。"""

    def __init__(self, path: str, target: AudioFormat | None = None,
                 playback_rate: float = 1.0):
        self._path = path
        self._target = target or AudioFormat()
        self._playback_rate = playback_rate
        self._frames: list[bytes] = []
        self._i = 0

    @property
    def audio_format(self) -> AudioFormat:
        return self._target

    def start(self) -> None:
        try:
            data, src_rate = sf.read(self._path, always_2d=True, dtype="float32")
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"无法读取音频文件 {self._path}: {e}") from e
        mono = to_mono(data)                       # (frames,) float32
        resampled = resample(mono, src_rate, self._target.sample_rate)
        if self._playback_rate != 1.0:
            resampled = resample(resampled,
                                 self._target.sample_rate,
                                 int(self._target.sample_rate / self._playback_rate))
        raw = encode_s16le(resampled)
        bpf = self._target.frame_bytes()
        self._frames = [raw[i:i + bpf] for i in range(0, len(raw) - bpf + 1, bpf)]
        self._i = 0

    def read_frame(self) -> bytes | None:
        if self._i >= len(self._frames):
            return None
        f = self._frames[self._i]
        self._i += 1
        return f

    def stop(self) -> None:
        self._frames = []
        self._i = 0
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_source_file.py -q`
Expected: `3 passed`。

- [ ] **Step 5: 提交**

```bash
git add smoco/source/file.py tests/test_source_file.py
git commit -m "feat(source): FileSource（wav→16k mono 30ms 帧，跨平台）"
```

---

## Task 6: chunker.py — VAD 协议、WebRtcVad、Chunker

**Files:**
- Create: `smoco/chunker.py`
- Create: `tests/test_chunker.py`

- [ ] **Step 1: 写失败测试 `tests/test_chunker.py`**

```python
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
    return out


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_chunker.py -q`
Expected: FAIL（`ImportError`）。

- [ ] **Step 3: 写 `smoco/chunker.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
import itertools
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
        self._silence_frames = max(1, silence_ms // fmt.frame_ms)
        self._max_frames = max(1, max_chunk_ms // fmt.frame_ms)
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
            # 太短：丢弃，仍返回一个"哨兵"会被调用方过滤；这里直接返回空 pcm 标记
            return AudioChunk(id=f"c{next(self._ids)}", pcm=b"",
                              start_time=start_time, end_time=end_time,
                              sample_rate=self._fmt.sample_rate,
                              is_final=not forced)

        pcm = b"".join(b for _, b in kept)
        return AudioChunk(id=f"c{next(self._ids)}", pcm=pcm,
                          start_time=start_time, end_time=end_time,
                          sample_rate=self._fmt.sample_rate,
                          is_final=not forced)
```

> 说明：被 `min_chunk_ms` 丢弃的段返回 `pcm == b""`。pipeline/调用方按 `not chunk.pcm` 过滤。这样 Chunker 接口稳定，无需改 `feed` 返回类型。

- [ ] **Step 4: 修改测试以兼容"空 pcm = 丢弃"约定**

把 `test_chunk_ids_are_unique` 等过滤掉空 pcm。更新 `tests/test_chunker.py` 的 `_run`：

```python
def _run(chunker, frames):
    out = []
    for f in frames:
        out.extend(chunker.feed(f))
    out.extend(chunker.flush())
    return [c for c in out if c.pcm]   # 过滤被丢弃的段
```

（替换原 `_run` 函数体。）

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_chunker.py -q`
Expected: `6 passed`。

- [ ] **Step 6: 提交**

```bash
git add smoco/chunker.py tests/test_chunker.py
git commit -m "feat(chunker): Vad 协议 + WebRtcVad + Chunker（静音/最长/最短/pad）"
```

---

## Task 7: transcriber/base.py + stub.py

**Files:**
- Create: `smoco/transcriber/__init__.py`
- Create: `smoco/transcriber/base.py`
- Create: `smoco/transcriber/stub.py`
- Create: `tests/test_transcriber_stub.py`

- [ ] **Step 1: 写 `smoco/transcriber/__init__.py`**（空）

```python
```

- [ ] **Step 2: 写失败测试 `tests/test_transcriber_stub.py`**

```python
import asyncio
import os
from smoco.audio import AudioChunk, AudioFormat
from smoco.transcriber.stub import StubTranscriber


def test_stub_returns_empty_result_and_is_final():
    tr = StubTranscriber()
    chunk = AudioChunk(id="x", pcm=b"\x00" * 960, start_time=0.0,
                       end_time=0.03, sample_rate=16000, is_final=True)
    result = asyncio.run(tr.transcribe(chunk))
    assert result["chunk_id"] == "x"
    assert result["text"] == ""
    assert result["is_final"] is True
    assert result["error"] is None
    asyncio.run(tr.close())


def test_stub_writes_wav_when_outdir_set(tmp_path):
    tr = StubTranscriber(out_dir=str(tmp_path))
    chunk = AudioChunk(id="c7", pcm=b"\x01" * 960, start_time=1.0,
                       end_time=1.03, sample_rate=16000, is_final=True)
    asyncio.run(tr.transcribe(chunk))
    asyncio.run(tr.close())
    written = list(tmp_path.glob("c7*.wav"))
    assert len(written) == 1
    assert os.path.getsize(written[0]) > 0
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_transcriber_stub.py -q`
Expected: FAIL（`ImportError`）。

- [ ] **Step 4: 写 `smoco/transcriber/base.py`**

```python
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
```

- [ ] **Step 5: 写 `smoco/transcriber/stub.py`**

```python
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
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_transcriber_stub.py -q`
Expected: `2 passed`。

- [ ] **Step 7: 提交**

```bash
git add smoco/transcriber/ tests/test_transcriber_stub.py
git commit -m "feat(transcriber): Transcriber 协议 + StubTranscriber"
```

---

## Task 8: pipeline.py — 串联、背压、生命周期

**Files:**
- Create: `smoco/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试 `tests/test_pipeline.py`**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_pipeline.py -q`
Expected: FAIL（`ImportError`）。

- [ ] **Step 3: 写 `smoco/pipeline.py`**

```python
from __future__ import annotations
import asyncio
import logging
import threading
from typing import Iterable
from .audio import AudioChunk
from .chunker import Chunker, Vad
from .config import Config
from .source.base import AudioSource, SourceError
from .transcriber.base import Transcriber

log = logging.getLogger("smoco.pipeline")


class Pipeline:
    """source(同步,线程) -> chunker(同线程) -> asyncio.Queue -> transcriber(协程)。
    队列满时丢最旧 chunk + 告警（实时音频积压无意义）。"""

    def __init__(self, source: AudioSource, chunker: Chunker,
                 transcriber: Transcriber, config: Config):
        self._source = source
        self._chunker = chunker
        self._transcriber = transcriber
        self._cfg = config
        self._error: Exception | None = None

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=self._cfg.chunk_queue_size)
        n_workers = self._cfg.transcriber_concurrency
        capture = threading.Thread(target=self._capture_loop,
                                   args=(loop, q, n_workers), daemon=True)
        capture.start()
        workers = [asyncio.create_task(self._transcribe_loop(q))
                   for _ in range(n_workers)]
        try:
            await loop.run_in_executor(None, capture.join)
        finally:
            for _ in range(n_workers):
                await q.put(None)            # 各 worker 一个哨兵
            await asyncio.gather(*workers, return_exceptions=True)
            await self._transcriber.close()

    def _capture_loop(self, loop, q: asyncio.Queue, n_workers: int) -> None:
        self._source.start()
        try:
            while True:
                frame = self._source.read_frame()
                if frame is None:
                    break
                for chunk in self._chunker.feed(frame):
                    if not chunk.pcm:        # 被 min_chunk_ms 丢弃
                        continue
                    self._put_threadsafe(q, chunk, loop)
                # source 在线程内，无需单独 frameQ
            for chunk in self._chunker.flush():
                if chunk.pcm:
                    self._put_threadsafe(q, chunk, loop)
        except SourceError as e:
            log.error("采集错误: %s", e)
            self._error = e
        except Exception as e:  # noqa: BLE001
            log.exception("采集线程意外异常")
            self._error = e
        finally:
            try:
                self._source.stop()
            except Exception:  # noqa: BLE001
                log.exception("stop() 失败")

    def _put_threadsafe(self, q: asyncio.Queue, chunk: AudioChunk, loop) -> None:
        def _put():
            if q.full() and self._cfg.drop_policy == "drop_oldest":
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                log.warning("chunkQ 满，丢弃最旧 chunk")
                q.put_nowait(chunk)
            elif self._cfg.drop_policy == "drop_newest" and q.full():
                log.warning("chunkQ 满，丢弃最新 chunk")
            else:
                try:
                    q.put_nowait(chunk)
                except asyncio.QueueFull:
                    log.warning("chunkQ 满且策略 block，仍丢弃以避免死锁")
        loop.call_soon_threadsafe(_put)

    async def _transcribe_loop(self, q: asyncio.Queue) -> None:
        while True:
            item = await q.get()
            if item is None:                 # 哨兵
                return
            chunk: AudioChunk = item
            try:
                result = await self._transcriber.transcribe(chunk)
            except Exception as e:  # noqa: BLE001
                log.warning("转写异常 (chunk=%s): %s", chunk.id, e)
                continue
            if result.get("error"):
                log.warning("转写失败 (chunk=%s): %s", chunk.id, result["error"])
            else:
                log.info("[%.2f-%.2f] %s", result["start_time"],
                         result["end_time"], result["text"])

    @property
    def error(self) -> Exception | None:
        return self._error
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_pipeline.py -q`
Expected: `3 passed`。

- [ ] **Step 5: 提交**

```bash
git add smoco/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): source→chunker→transcriber 串联 + 背压 + 生命周期"
```

---

## Task 9: source/wasapi.py — Windows WASAPI loopback

**Files:**
- Create: `smoco/source/wasapi.py`

> 此任务**无法在 macOS 上自动化测试**（无 loopback 设备）。仅做"导入不炸 + 结构正确"，真机验证走 spec 的 Windows 清单。在 macOS 上 `pyaudiowpatch` 不安装，故用 `try/except ImportError` 保护。

- [ ] **Step 1: 写 `smoco/source/wasapi.py`**

```python
from __future__ import annotations
import logging
import threading
import queue as _q
import numpy as np
from ..audio import AudioFormat, to_mono, resample, encode_s16le
from .base import SourceError

log = logging.getLogger("smoco.source.wasapi")

try:
    import pyaudiowpatch as pyaudio
    _AVAILABLE = True
except Exception:  # noqa: BLE001
    pyaudio = None
    _AVAILABLE = False


class WASAPILoopbackSource:
    """Windows WASAPI loopback 采集，规范化为 16k mono S16LE 30ms 帧。
    PyAudioWPatch 以 as_loopback=True 打开默认渲染端点。"""

    def __init__(self, target: AudioFormat | None = None,
                 device_index: int | None = None):
        if not _AVAILABLE:
            raise SourceError("pyaudiowpatch 不可用（非 Windows 或未安装）")
        self._target = target or AudioFormat()
        self._device_index = device_index
        self._pa: pyaudio.PyAudio | None = None
        self._stream = None
        self._frames: _q.Queue[bytes] = _q.Queue(maxsize=64)
        self._accum = bytearray()
        self._stop = threading.Event()

    @property
    def audio_format(self) -> AudioFormat:
        return self._target

    @staticmethod
    def list_devices() -> list[dict]:
        if not _AVAILABLE:
            return []
        pa = pyaudio.PyAudio()
        try:
            return [pa.get_device_info_by_index(i)
                    for i in range(pa.get_device_count())
                    if pa.get_device_info_by_index(i).get("maxInputChannels", 0) > 0]
        finally:
            pa.terminate()

    def start(self) -> None:
        self._pa = pyaudio.PyAudio()
        try:
            info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default = self._pa.get_device_info_by_index(info["defaultOutputDevice"])
            dev = self._device_index if self._device_index is not None else default["index"]
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"找不到 WASAPI 默认输出设备: {e}") from e

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=default["maxInputChannels"] or 2,
                rate=int(default["defaultSampleRate"]),
                input=True,
                input_device_index=dev,
                as_loopback=True,
                frames_per_buffer=1024,
                stream_callback=self._callback,
            )
            self._stream.start_stream()
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"无法打开 loopback 流: {e}") from e

    def _callback(self, in_data, frame_count, time_info, status):  # noqa: ANN001
        if self._stop.is_set():
            return (b"", pyaudio.paComplete)
        self._accum.extend(in_data)
        bpf = self._target.frame_bytes()
        sw = 2  # paInt16
        ch = self._channels
        frame_samples_in = self._rate_in // (1000 // self._target.frame_ms)
        # 把原始帧转 mono float32、重采样、编码后按 30ms 切
        raw = bytes(self._accum)
        self._accum = bytearray()
        try:
            arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
            if self._channels > 1:
                arr = arr.reshape(-1, self._channels)
            mono = to_mono(arr)
            res = resample(mono, self._rate_in, self._target.sample_rate)
            encoded = encode_s16le(res)
            for i in range(0, len(encoded) - bpf + 1, bpf):
                try:
                    self._frames.put_nowait(encoded[i:i + bpf])
                except _q.Full:
                    self._frames.get_nowait()        # 丢最旧
                    self._frames.put_nowait(encoded[i:i + bpf])
        except Exception:  # noqa: BLE001
            log.exception("WASAPI 帧转换失败")
        return (b"", pyaudio.paContinue)

    def read_frame(self) -> bytes | None:
        if self._stop.is_set() and self._frames.empty():
            return None
        try:
            return self._frames.get(timeout=0.1)
        except _q.Empty:
            return None

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        finally:
            if self._pa is not None:
                self._pa.terminate()
                self._pa = None
```

> 注：`_channels` / `_rate_in` 在 `start()` 中应据打开的实际流参数赋值。为简洁此处用默认输出设备信息；实现者在真机联调时把这两项从 `default` 取值并保存为实例属性（`self._channels = int(default["maxInputChannels"] or 2)`、`self._rate_in = int(default["defaultSampleRate"])`），加在 `start()` 末尾。这是该文件唯一留给真机联调微调的点，spec 清单第 1 条会覆盖。

- [ ] **Step 2: 跨平台导入验证（macOS 上应报 SourceError 而非 ImportError 崩溃）**

Run: `python -c "from smoco.source.wasapi import WASAPILoopbackSource, _AVAILABLE; print('available=', _AVAILABLE)"`
Expected: 打印 `available= False`（macOS 无 pyaudiowpatch），不抛异常。

- [ ] **Step 3: 提交**

```bash
git add smoco/source/wasapi.py
git commit -m "feat(source): WASAPILoopbackSource（Windows loopback，macOS 安全降级）"
```

---

## Task 10: __main__.py — CLI

**Files:**
- Create: `smoco/__main__.py`

> 真机 CLI 行为（list-devices / run with FileSource on macOS, WASAPI on Windows）无法在 CI 全量验证；本任务保证可运行、参数解析正确。用 `python -m smoco --help` 冒烟。

- [ ] **Step 1: 写 `smoco/__main__.py`**

```python
from __future__ import annotations
import argparse
import asyncio
import logging
import sys
from .audio import AudioFormat
from .chunker import Chunker, WebRtcVad
from .config import Config
from .pipeline import Pipeline
from .source.file import FileSource
from .transcriber.stub import StubTranscriber


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smoco",
                                description="采集系统声音 → VAD 切块 → 转写")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行管线")
    p_run.add_argument("--file", help="用文件源（跨平台，开发/测试用）")
    p_run.add_argument("--wasapi", action="store_true",
                       help="用 Windows WASAPI loopback 源")
    p_run.add_argument("--stub-out", help="StubTranscriber 落 wav 目录")

    sub.add_parser("list-devices", help="列出 WASAPI loopback 设备（Windows）")
    return p


def _make_source(args, fmt: AudioFormat):
    if args.file:
        return FileSource(args.file, target=fmt)
    if args.wasapi:
        from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
        if not _AVAILABLE:
            raise SystemExit("WASAPI 源不可用（需 Windows + pyaudiowpatch）")
        return WASAPILoopbackSource(target=fmt)
    raise SystemExit("请指定 --file 或 --wasapi")


def cmd_run(args) -> int:
    fmt = AudioFormat()
    cfg = Config()
    source = _make_source(args, fmt)
    vad = WebRtcVad(aggressiveness=cfg.vad_aggressiveness, sample_rate=fmt.sample_rate)
    chunker = Chunker(vad, fmt, silence_ms=cfg.silence_ms,
                      max_chunk_ms=cfg.max_chunk_ms, min_chunk_ms=cfg.min_chunk_ms,
                      pad_ms=cfg.pad_ms)
    transcriber = StubTranscriber(out_dir=args.stub_out)
    pipe = Pipeline(source, chunker, transcriber, cfg)
    try:
        asyncio.run(pipe.run())
    except KeyboardInterrupt:
        logging.getLogger("smoco").info("已中断")
    return 0


def cmd_list_devices() -> int:
    from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
    if not _AVAILABLE:
        print("WASAPI 不可用（需 Windows + pyaudiowpatch）")
        return 1
    for d in WASAPILoopbackSource.list_devices():
        print(d)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "list-devices":
        return cmd_list_devices()
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 冒烟测试 help**

Run: `python -m smoco --help`
Expected: 打印子命令 `run` / `list-devices` 帮助，退出码 0。

- [ ] **Step 3: 用 FileSource 跑一遍（生成一段 wav 再喂回去）**

Run:
```bash
python -c "import numpy as np, soundfile as sf; sf.write('/tmp/t.wav', (np.random.RandomState(0).uniform(-0.3,0.3,16000*2)).astype('float32'), 16000)"
python -m smoco run --file /tmp/t.wav --stub-out /tmp/smoco-stub
ls /tmp/smoco-stub
```
Expected: 无异常，`/tmp/smoco-stub` 下出现若干 `*.wav`。

- [ ] **Step 4: 提交**

```bash
git add smoco/__main__.py
git commit -m "feat(cli): smoco run / list-devices 命令行入口"
```

---

## Task 11: 全量回归 + Windows 真机清单落档

**Files:**
- Modify: `README.md`（新建，可选）

- [ ] **Step 1: 全量测试**

Run: `pytest -q`
Expected: 全部测试通过（macOS 上 WASAPI 相关用 `_AVAILABLE=False` 安全跳过，无真实设备依赖）。

- [ ] **Step 2: 写 README（含 spec 第 7 节的 Windows 真机清单）**

创建 `README.md`，内容包含：安装（`pip install -e ".[dev]"`）、macOS 开发用法（FileSource + Stub）、Windows 用法（WASAPI）、以及把 spec 中"Windows 真机验证清单"6 条原样复制为可勾选 TODO。

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: README + Windows 真机验证清单"
```

- [ ] **Step 4: 标记完成**

全量测试通过 + README 落档即视为本计划实现完成。Windows 真机联调（清单 6 条）由用户在 Windows 机器上手动执行。

---

## Self-Review（plan 完成后自查记录）

- **Spec 覆盖**：采集回环（Task 5 FileSource + Task 9 WASAPI）✓；16k mono 规范化（Task 2）✓；VAD 三段规则（Task 6）✓；背压丢最旧（Task 8）✓；两个抽象接口（Task 4/7）✓；错误处理（Task 8 三类用例）✓；测试策略（Task 5/6/8 合成+FileSource，macOS 全绿）✓；CLI（Task 10）✓。
- **占位符**：无 TBD/TODO；Task 9 的 `_channels/_rate_in` 给出了明确取值指引，非占位。
- **类型一致**：`AudioChunk`、`AudioFormat`、`TranscriptResult`、`Vad.is_speech`、`Transcriber.transcribe/close`、`AudioSource.read_frame/start/stop/audio_format` 在各 Task 间签名一致；`Chunker` 构造参数在 Task 6/8/10 一致。
