# smoco

采集**系统声音**（loopback）→ VAD 切块 → 通过抽象转写接口送出 ASR 的实时流式管线。

- 目标平台：**Windows**（WASAPI loopback）。
- 开发/测试：macOS 上用 `FileSource`（喂 wav）+ `StubTranscriber` 跑通整条链路与全部单测；只有 `WASAPILoopbackSource` 是 Windows 专属。
- ASR 引擎抽象为 `Transcriber` 接口，支持：
  - `StubTranscriber`：本地落盘 wav（开发/测试用）
  - `WhisperRemoteTranscriber`：调用远程 Whisper API 服务

## 功能

- **实时采集**：Windows WASAPI loopback 采集系统声音
- **VAD 切块**：WebRTC VAD 检测静音，智能分段
- **远程转写**：调用 GPU 服务器的 Whisper 模型转写
- **多语言**：支持日语、中文、英语等 99 种语言
- **实时音量条**：`--meter` 显示音量律动

## 安装

```bash
python -m pip install -e ".[dev]"
```

`pyaudiowpatch` 仅在 Windows 安装（platform marker）；macOS 上会自动跳过。

## macOS 开发 / 测试

跑全部单测（无需声卡、无需 Windows）：

```bash
pytest -q
```

用文件源端到端跑一遍管线，把切出的 chunk 落成 wav 供肉眼检查：

```bash
python -c "import numpy as np, soundfile as sf; sf.write('/tmp/t.wav', (np.random.RandomState(0).uniform(-0.3,0.3,16000*2)).astype('float32'), 16000)"
python -m smoco run --file /tmp/t.wav --stub-out /tmp/smoco-stub
ls /tmp/smoco-stub
```

## Windows 用法

### 采集系统声音（本地落盘）

```bash
smoco run --wasapi --stub-out ./chunks
```

### 实时转写

#### 方式 1：远程 Whisper API

```bash
uv run smoco run --wasapi --meter --whisper-url http://your-server:8000 --whisper-lang ja
```

#### 方式 2：本地 Whisper（进程内 CPU）

```bash
# 安装本地 Whisper 支持
uv sync --extra whisper

# 运行（模型加载在进程内）
uv run smoco run --wasapi --meter --whisper-local --whisper-model medium --whisper-lang ja
```

#### 方式 3：本地 Whisper API 服务（推荐）

```bash
# 终端 1：启动本地 API 服务器
cd whisper-local
uv sync
uv run python whisper_local_api.py --interactive

# 终端 2：运行 smoco
uv run smoco run --wasapi --meter --whisper-local-api --whisper-lang ja
```

**参数说明：**
- `--wasapi`：使用 WASAPI loopback 采集
- `--meter`：显示实时音量条
- `--whisper-url`：远程 Whisper API 地址
- `--whisper-local`：进程内本地 Whisper
- `--whisper-local-api`：本地 Whisper API 服务
- `--whisper-model`：本地模型（medium, large-v3-turbo, distil-large-v3 等）
- `--whisper-lang`：语言代码（ja=日语, zh=中文, en=英语）
- `--debug`：显示调试日志

### 列出 WASAPI 设备

```bash
smoco list-devices
```

## Windows 真机验证清单

CI 跑不了真实设备，请在 Windows 机器上按以下清单手动验证：

1. `python -m smoco list-devices` 能列出 loopback 设备并选中默认渲染端点；
2. 播放任一系统音频（如 YouTube 视频），CLI 启动后能持续采集；
3. `StubTranscriber` 落盘的 wav 能听到声音、且按静音切成多段；
4. 停止播放时不再产生新 chunk（VAD 正确判定静音）；
5. Ctrl-C 后进程在 5 s 内干净退出，无僵尸线程/设备占用残留；
6. `smoco run --wasapi --meter` 选设备后，音量条随系统声音起伏；
7. 播放日语音频时，Whisper 转写能正确输出日语文本；
8. Ctrl-C 后音量条干净收尾换行，无残留。

## Whisper API 服务器

`whisper-server/` 目录包含 GPU 服务器上的 Whisper API 服务。

### 安装

```bash
cd whisper-server
uv sync
```

### 运行

```bash
# 使用 medium 模型
CUDA_VISIBLE_DEVICES=2 python whisper_api_server.py --model-name medium --port 8000

# 或使用本地模型文件
CUDA_VISIBLE_DEVICES=2 python whisper_api_server.py --model-path ~/models/whisper/medium.pt --port 8000
```

详见 `whisper-server/README.md`。

## Whisper 本地转写

`whisper-local/` 目录包含 Windows 本地 Whisper 转写器（CPU 模式）。

### 安装

```bash
cd whisper-local
python -m venv .venv
.venv\Scripts\activate
pip install faster-whisper
```

### 运行

```bash
# 交互式选择模型
start.bat

# 或命令行
python whisper_local_transcriber.py --model medium --language ja
```

**支持的模型：**
- `medium`：平衡速度和准确率（推荐）
- `large-v3-turbo`：快速且准确
- `distil-large-v3`：蒸馏版本，更快
- `tiny`, `base`, `small`：更小的模型

详见 `whisper-local/README.md`。

## 架构

```
Windows (远程转写): WASAPILoopbackSource → Chunker(VAD) → Queue → WhisperRemoteTranscriber → HTTP → GPU服务器
Windows (本地转写): WASAPILoopbackSource → Chunker(VAD) → Queue → WhisperLocalTranscriber → CPU
macOS   (开发测试):   FileSource → Chunker(VAD) → Queue → StubTranscriber → 落盘wav
```

**组件：**
- `AudioSource`：音频采集（WASAPILoopbackSource / FileSource）
- `Chunker`：WebRTC VAD 检测静音，智能分段
- `Transcriber`：转写接口
  - `StubTranscriber`：开发测试，落盘 wav
  - `WhisperRemoteTranscriber`：远程 GPU 服务器
  - `WhisperLocalTranscriber`：本地 CPU 转写
- `Pipeline`：协调整条链路

`AudioSource` 与 `Transcriber` 均为可替换协议；`pipeline.py` 只依赖这两个协议。详见 `docs/superpowers/specs/` 与 `docs/superpowers/plans/`。
