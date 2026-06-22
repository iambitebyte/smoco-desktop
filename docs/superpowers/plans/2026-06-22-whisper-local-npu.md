# whisper-local-npu（NPU 版本地 Whisper 服务）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `whisper-local-npu/`——一个走 Intel NPU 的本地 Whisper HTTP 服务，对外契约与 `whisper-local/whisper_local_api.py` 一致，让现有 GUI（手动起服务 + 选 URL）无感调用。

**Architecture:** 镜像 `whisper-local/`（同级独立 uv 工程）。`whisper_npu_api.py` 用 FastAPI 暴露 `/health` + `POST /transcribe`（raw PCM body），内核换成 openvino-genai 的 `Whisper`（`device="NPU"`），转写甩线程（`asyncio.to_thread`）、直接喂 float32 numpy（不走临时 wav）。重依赖（openvino/openvino-genai/fastapi/uvicorn）**懒导入**，故 `--help` 等基础校验不需要它们。HTTP 契约设计成 `create_app(pipe, ...)` 工厂，便于用假 pipe 注入做契约测试（不依赖真实 NPU）。

**Tech Stack:** Python ≥3.10、openvino-genai、FastAPI、uvicorn、numpy、uv、pytest + httpx（dev）。

**重要的环境前提（写进每个任务）：** `openvino-genai` 没有 macOS wheel，所以**本组件及其测试在 macOS 上无法实际运行**。macOS 上只能验证：文件语法（`py_compile`）、`--help`（因懒导入）、主 `pytest -q` 不被破坏。契约测试在 **whisper-local-npu 的 venv（Windows/有 openvino-genai 的环境）** 里跑，且因为注入假 pipe，**不需要真实 NPU** 就能验 HTTP 契约。真机 NPU 转写走 README 清单。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `whisper-local-npu/pyproject.toml` | uv 工程元数据 + 依赖（openvino-genai/fastapi/uvicorn/numpy；dev: pytest/httpx） |
| `whisper-local-npu/whisper_npu_api.py` | FastAPI 服务：`create_app` 工厂 + `_interactive` + `main`（NPU 自检、懒加载模型、uvicorn 启动） |
| `whisper-local-npu/start-npu-api.bat` | Windows 一键起（`uv sync` + `--interactive`） |
| `whisper-local-npu/tests/test_whisper_npu_api.py` | HTTP 契约测试（假 pipe 注入，无需 NPU） |
| `whisper-local-npu/README.md` | 前置、模型导出、启动、GUI 接入、缓存、真机清单 |

---

## Task 1: `pyproject.toml` + `whisper_npu_api.py`

**Files:**
- Create: `whisper-local-npu/pyproject.toml`
- Create: `whisper-local-npu/whisper_npu_api.py`

- [ ] **Step 1: 写 `whisper-local-npu/pyproject.toml`**

```toml
[project]
name = "whisper-local-npu"
version = "0.1.0"
description = "本地 Whisper 转写器（Windows NPU，openvino-genai）"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "openvino-genai>=2024.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "numpy>=1.24",
]

[project.scripts]
whisper-local-npu-api = "whisper_npu_api:main"

[tool.uv]
dev-dependencies = [
    "pytest>=7",
    "httpx>=0.27",
]
```

- [ ] **Step 2: 写 `whisper-local-npu/whisper_npu_api.py`**

```python
#!/usr/bin/env python3
"""
Whisper 本地 NPU API 服务器（openvino-genai, device=NPU）。

对外契约与 whisper-local/whisper_local_api.py 一致：
  GET  /health
  POST /transcribe?language=ja   body = 原始 PCM（16k mono S16LE）

重依赖（openvino / openvino-genai / fastapi / uvicorn）在 main() 里懒导入，
故 --help 等基础校验不依赖它们。
"""
import argparse
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

LANGUAGES = {
    1: ("ja", "日语"),
    2: ("zh", "中文"),
    3: ("en", "英语"),
    4: ("ko", "韩语"),
    5: ("fr", "法语"),
    6: ("de", "德语"),
    7: ("es", "西班牙语"),
}


def _get_choice(prompt: str, options: dict, default: int):
    while True:
        try:
            choice = input(prompt).strip()
            if not choice:
                return options[default]
            num = int(choice)
            if num in options:
                return options[num]
            print(f"无效选择，请输入 1-{len(options)}")
        except ValueError:
            print("请输入数字")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            sys.exit(0)


def _interactive():
    print("\n" + "=" * 50)
    print("  Whisper 本地 NPU API 服务器配置")
    print("=" * 50)
    print("\n选择默认语言：")
    for num, (code, name) in LANGUAGES.items():
        print(f"  [{num}] {name} ({code})")
    print("=" * 50)
    lang_code, _ = _get_choice("请选择默认语言 (1-7，回车默认 1): ", LANGUAGES, default=1)
    model_dir = input("请输入 OpenVINO IR 模型目录路径: ").strip()
    while not model_dir:
        print("模型目录不能为空")
        model_dir = input("请输入 OpenVINO IR 模型目录路径: ").strip()
    while True:
        port_input = input("请输入端口 (回车默认 8000): ").strip()
        if not port_input:
            port = 8000
            break
        try:
            port = int(port_input)
            if 1 <= port <= 65535:
                break
            print("端口范围 1-65535")
        except ValueError:
            print("请输入数字")
    return model_dir, lang_code, port


def create_app(pipe, model_dir: str, device: str):
    """构建 FastAPI app。pipe 是已加载的 openvino_genai.Whisper（或测试用假对象）。"""
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import numpy as np

    app = FastAPI(title="Whisper Local NPU API")

    @app.get("/health")
    async def health():
        return {"status": "ok", "model": model_dir, "device": device, "mode": "local-npu"}

    @app.post("/transcribe")
    async def transcribe(request: Request, language: str = "ja"):
        if pipe is None:
            raise HTTPException(status_code=503, detail="模型未加载")
        try:
            audio_data = await request.body()
            if not audio_data:
                return JSONResponse({
                    "text": "", "segments": [], "language": language, "duration": 0.0,
                })
            samples = np.frombuffer(audio_data, dtype="<i2").astype(np.float32) / 32768.0
            # 转写是同步重活，甩线程不卡事件循环
            result = await asyncio.to_thread(pipe.transcribe, samples, language=language)
            segments = []
            for ch in getattr(result, "chunks", []) or []:
                segments.append({
                    "start": float(getattr(ch, "start", 0.0)),
                    "end": float(getattr(ch, "end", 0.0)),
                    "text": getattr(ch, "text", ""),
                })
            duration = float(len(samples) / 16000.0)
            return JSONResponse({
                "text": getattr(result, "text", ""),
                "segments": segments,
                "language": language,
                "duration": duration,
            })
        except Exception as e:
            log.exception("转写失败")
            raise HTTPException(status_code=500, detail=str(e))

    return app


def main():
    p = argparse.ArgumentParser(description="Whisper 本地 NPU API 服务器（openvino-genai）")
    p.add_argument("--interactive", action="store_true", help="交互式选择配置")
    p.add_argument("--model-dir", type=str, help="OpenVINO IR 模型目录路径")
    p.add_argument("--language", type=str, default="ja", help="默认语言代码 (ja/zh/en/...)")
    p.add_argument("--device", type=str, default="NPU", help="OpenVINO 设备 (NPU/GPU/CPU，默认 NPU)")
    p.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    p.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    args = p.parse_args()

    if args.interactive:
        model_dir, language, port = _interactive()
        host, device = args.host, args.device
    else:
        if not args.model_dir:
            p.error("--model-dir 必填（或使用 --interactive）")
        model_dir, language, port = args.model_dir, args.language, args.port
        host, device = args.host, args.device

    # 懒导入重依赖
    try:
        from openvino import Core
    except ImportError:
        print("缺少依赖：请在 whisper-local-npu/ 下 `uv sync`（需 openvino、openvino-genai）")
        sys.exit(1)

    devices = Core().available_devices
    if device not in devices:
        print(f"找不到设备 '{device}'。当前可见设备：{devices}")
        sys.exit(1)

    try:
        import openvino_genai
    except ImportError:
        print("缺少依赖：openvino-genai 未安装，请 `uv sync`")
        sys.exit(1)

    log.info(f"加载模型: {model_dir} (device={device})")
    log.info("首次运行会为 NPU 编译模型，可能耗时较长；可设 OV_CACHE_DIR 加速后续启动")
    pipe = openvino_genai.Whisper(model_dir, device=device)
    log.info("模型加载完成")

    import uvicorn
    app = create_app(pipe, model_dir, device)
    log.info(f"启动 API 服务: http://{host}:{port}  (GET /health, POST /transcribe)")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: macOS 上验证语法 + `--help`（懒导入，不需要 openvino）**

Run:
```bash
python -m py_compile whisper-local-npu/whisper_npu_api.py
python whisper-local-npu/whisper_npu_api.py --help
```
Expected: py_compile 无输出（成功）；`--help` 打印参数列表（`--interactive/--model-dir/--language/--device/--host/--port`），退出码 0。

- [ ] **Step 4: 确认主测试套件不受影响**

Run: `pytest -q`
Expected: 与新增前一致（新文件未被任何测试导入）。

- [ ] **Step 5: 提交**

```bash
git add whisper-local-npu/pyproject.toml whisper-local-npu/whisper_npu_api.py
git commit -m "feat(whisper-local-npu): NPU 版 Whisper API 服务骨架（openvino-genai）"
```

---

## Task 2: HTTP 契约测试（假 pipe 注入，无需 NPU）

**Files:**
- Create: `whisper-local-npu/tests/test_whisper_npu_api.py`

> 此测试在 **whisper-local-npu 的 venv** 内运行（`cd whisper-local-npu && uv run pytest tests/`），需要 fastapi/httpx/numpy（已是该工程依赖）。因注入假 pipe，**不需要真实 NPU/模型**，只验 HTTP 契约。macOS 上 openvino-genai 装不上 → 无法建此 venv → 本测试在 macOS 不执行（仅 `py_compile` 验语法）。

- [ ] **Step 1: 写 `whisper-local-npu/tests/test_whisper_npu_api.py`**

```python
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
```

- [ ] **Step 2: macOS 上验语法（无法运行测试本身）**

Run: `python -m py_compile whisper-local-npu/tests/test_whisper_npu_api.py`
Expected: 无输出（成功）。

- [ ] **Step 3: 确认主测试套件不受影响**

Run: `pytest -q`
Expected: 与之前一致（此测试在 whisper-local-npu/ 下，不在主 testpaths 内，不会被根 pytest 收集）。

- [ ] **Step 4: 提交**

```bash
git add whisper-local-npu/tests/test_whisper_npu_api.py
git commit -m "test(whisper-local-npu): /health 与 /transcribe HTTP 契约测试（假 pipe）"
```

> 真机运行（Windows / 有 openvino-genai 的 venv）：
> ```bash
> cd whisper-local-npu
> uv sync
> uv run pytest tests/
> ```
> 预期：3 passed。

---

## Task 3: `start-npu-api.bat`（Windows 一键起）

**Files:**
- Create: `whisper-local-npu/start-npu-api.bat`

- [ ] **Step 1: 写 `whisper-local-npu/start-npu-api.bat`**

```bat
@echo off
REM Whisper 本地 NPU API 服务器启动脚本

cd /d "%~dp0"

echo 正在同步依赖...
call uv sync

echo.
echo 启动 Whisper 本地 NPU API 服务器（交互式配置）...
echo 提示：首次会为 NPU 编译模型，可能耗时较长。
echo.
call uv run python whisper_npu_api.py --interactive

pause
```

- [ ] **Step 2: 提交**

```bash
git add whisper-local-npu/start-npu-api.bat
git commit -m "feat(whisper-local-npu): start-npu-api.bat 一键启动脚本"
```

> macOS 无法运行 .bat；仅作为产物提交，真机双击即用。

---

## Task 4: `README.md`

**Files:**
- Create: `whisper-local-npu/README.md`

- [ ] **Step 1: 写 `whisper-local-npu/README.md`**

````markdown
# Whisper 本地 NPU 转写器

在 Intel Core Ultra（带 NPU）的 Windows 上，用 **openvino-genai** 跑 Whisper，推理走 **NPU**。
对外 HTTP 契约与 `whisper-local/`（CPU 版）一致，smoco / GUI 可无感切换。

## 前置条件

1. **Intel NPU 驱动**已安装（设备管理器可见 "Intel(R) AI Boost" 类设备）。
2. 验证 NPU 可见：
   ```bash
   uv run python -c "from openvino import Core; print(Core().available_devices)"
   ```
   输出里要有 `NPU`。

## 安装

```bash
cd whisper-local-npu
uv sync
```

## 准备 INT8 模型（导出一次）

NPU 需要 OpenVINO IR（INT8）格式模型。用 Optimum 从 HuggingFace 导出：

```bash
pip install optimum[openvino]
optimum-cli export openvino --model openai/whisper-small --weight-format int8 whisper-small-ov
```

- 原始模型从 HuggingFace 拉（国内可用镜像：`set HF_ENDPOINT=https://hf-mirror.com`）
- 体积：small ≈ 466MB，medium ≈ 1.5G；可换 `openai/whisper-large-v3-turbo` / `distil-large-v3` 再导（更快更准）
- INT8 是 NPU 友好格式（Series 1 NPU 上 FP16 常跑不动）

## 启动

**方式 1：双击 `start-npu-api.bat`**（交互式选 语言/模型目录/端口）

**方式 2：命令行**
```bash
uv run python whisper_npu_api.py --model-dir whisper-small-ov --language ja --port 8000
```

参数：
- `--model-dir`：OpenVINO IR 模型目录（必填，或用 `--interactive`）
- `--language`：默认 `ja`（ja/zh/en/ko/fr/de/es）
- `--device`：默认 `NPU`（可改 `GPU`/`CPU` 调试）
- `--port`：默认 `8000`
- `--host`：默认 `127.0.0.1`
- `--interactive`：交互式配置

### 首次启动会编译模型

openvino-genai 首次用某模型+设备时会为 NPU 编译（几十秒~几分钟）。可设缓存加速后续启动：
```bash
set OV_CACHE_DIR=.ov-cache
```

## API

- `GET /health` → `{"status":"ok","model":...,"device":"NPU","mode":"local-npu"}`
- `POST /transcribe?language=ja`：body = 原始 PCM（16k mono S16LE）→
  ```json
  {"text":"...","segments":[{"start":0.0,"end":1.0,"text":"..."}],"language":"ja","duration":5.0}
  ```

## 与 GUI 集成（零改动）

1. 双击 `start-npu-api.bat` 起服务（默认 `http://127.0.0.1:8000`）
2. 在 smoco GUI 的 startup 对话框里把 `http://127.0.0.1:8000` 当一个 server 选
3. `asr_worker.py` 走同一个 `/transcribe` 契约，无感切换到 NPU

## 与 `whisper-local`（CPU 版）对比

| | whisper-local | whisper-local-npu |
|---|---|---|
| 引擎 | faster-whisper | openvino-genai |
| 算力 | CPU | NPU（低功耗强项） |
| 模型 | 原始 Whisper 名 | OpenVINO IR INT8 目录 |
| 契约 | 相同 | 相同 |

## Windows 真机验证清单

1. `Core().available_devices` 能看到 `NPU`；
2. `optimum-cli export ... --weight-format int8` 能导出 IR 目录；
3. `uv run pytest tests/` 三个契约测试通过；
4. `uv run python whisper_npu_api.py --model-dir <dir> --language ja` 启动后 `GET /health` 返回 200；
5. 首次 NPU 编译在预期内（或设了 `OV_CACHE_DIR` 后二次启动明显变快）；
6. GUI 选 `http://127.0.0.1:8000` 后，播放日语音频能转出正确日文；
7. 与 `whisper-local`（CPU）对比：质量相当、功耗/发热明显更低；吞吐是否更高看 Ultra 代数（Series 1 ~11TOPS，Series 2 更高）。
````

- [ ] **Step 2: 提交**

```bash
git add whisper-local-npu/README.md
git commit -m "docs(whisper-local-npu): README（前置/模型导出/启动/GUI接入/真机清单）"
```

- [ ] **Step 3: 最终核对**

Run:
```bash
python -m py_compile whisper-local-npu/whisper_npu_api.py whisper-local-npu/tests/test_whisper_npu_api.py
ls -la whisper-local-npu/
pytest -q
```
Expected: py_compile 无输出；`whisper-local-npu/` 含 `pyproject.toml / whisper_npu_api.py / start-npu-api.bat / tests/ / README.md`；主 `pytest -q` 无失败。

---

## Self-Review（plan 完成后自查记录）

- **Spec 覆盖**：镜像 `whisper-local/` 同级目录（Task 1）✓；openvino-genai + `device=NPU`（Task 1 main）✓；`/health` + `POST /transcribe` raw PCM + 同 JSON（Task 1 create_app）✓；甩线程 + numpy 不走临时 wav（Task 1）✓；`--model-dir` 手动指、默认端口 8000（Task 1 main）✓；GUI 零改动接入（Task 4 README）✓；错误处理（NPU 不在→退出、依赖缺→提示、转写异常→500、空 body→空 text）（Task 1）✓；测试策略（假 pipe 契约测试 + importorskip 等价为"仅 NPU 工程内运行"，macOS 仅 py_compile）（Task 2）✓；模型获取 optimum 导出 INT8（Task 4 README）✓；Windows 清单（Task 4）✓。
- **占位符**：无 TBD/TODO；每步含完整代码与确切命令，并明确标注 macOS-可验 vs 真机-可验。
- **类型一致**：`create_app(pipe, model_dir, device)` 在 Task 1 定义、Task 2 测试中签名一致；`pipe.transcribe(samples, language=)` 调用契约一致；返回 JSON 字段（text/segments/language/duration）在 create_app 与测试断言间一致（`language_probability` 按设计省略，测试不断言它）。
- **已知环境限制（已诚实写进每个任务）**：openvino-genai 无 macOS wheel → 组件与契约测试在 macOS 不可运行；macOS 仅 `py_compile` + `--help` + 主套件不破坏；契约测试在 whisper-local-npu venv（Windows/有依赖环境）运行且不需真实 NPU；真机 NPU 转写走 README 清单。
