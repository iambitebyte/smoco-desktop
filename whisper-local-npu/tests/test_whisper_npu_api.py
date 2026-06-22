"""whisper_npu_api 的 HTTP 契约测试。

注入假 pipe，不依赖真实 NPU/模型，只验 /health 与 /transcribe 的契约形状。
运行（在 whisper-local-npu venv 内）：
    cd whisper-local-npu && uv run pytest tests/
"""
import sys
from pathlib import Path

# 让 tests/ 能 import 上级目录的 whisper_npu_api.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from fastapi.testclient import TestClient

import whisper_npu_api


class _FakeChunk:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class _FakeResult:
    def __init__(self, text, chunks):
        self.text = text
        self.chunks = chunks


class _FakePipe:
    def __init__(self):
        self.last_samples = None
        self.last_language = None

    def transcribe(self, samples, language=None):
        self.last_samples = samples
        self.last_language = language
        return _FakeResult("こんにちは", [_FakeChunk(0.0, 1.0, "こんにちは")])


def test_health_returns_mode_and_device():
    app = whisper_npu_api.create_app(_FakePipe(), "fake-model-dir", "NPU")
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "local-npu"
    assert body["device"] == "NPU"
    assert body["model"] == "fake-model-dir"


def test_transcribe_returns_text_and_calls_pipe_with_float32():
    pipe = _FakePipe()
    app = whisper_npu_api.create_app(pipe, "fake-model-dir", "NPU")
    client = TestClient(app)
    pcm = np.full(16000, 32767, dtype="<i2").tobytes()   # 1s 满幅
    r = client.post("/transcribe?language=ja", content=pcm,
                    headers={"Content-Type": "audio/raw"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "こんにちは"
    assert body["language"] == "ja"
    assert abs(body["duration"] - 1.0) < 1e-6
    assert body["segments"] == [{"start": 0.0, "end": 1.0, "text": "こんにちは"}]
    # pipe 被以 float32 numpy 调用（非文件路径），且已归一化到 [0,1]
    assert isinstance(pipe.last_samples, np.ndarray)
    assert pipe.last_samples.dtype == np.float32
    assert abs(float(pipe.last_samples.max()) - 1.0) < 1e-3
    assert pipe.last_language == "ja"


def test_transcribe_empty_body_returns_empty_text():
    app = whisper_npu_api.create_app(_FakePipe(), "fake-model-dir", "NPU")
    client = TestClient(app)
    r = client.post("/transcribe", content=b"")
    assert r.status_code == 200
    assert r.json()["text"] == ""
