# 系统声音实时流式转写 — 设计文档

- **日期**：2026-06-18
- **状态**：待用户审阅
- **项目名（暂定）**：smoco

## 1. 目标与背景

构建一个 Windows 上运行的软件，实时采集**系统正在播放的声音**（会议里对方说话、视频、播客等），切成 chunk，通过一个**抽象的转写接口**送出去做 ASR 转写，追求低延迟出字幕。

ASR 引擎暂不绑死——先把"采集 → 切块 → 抽象转写接口"这条管线做出来，留出插口，后续接本地 Whisper 或云端 API 都只是新增一个实现文件。

### 非目标（YAGNI）

- 不做说话人分离（diarization）、不区分多人。
- 不做 GUI；先做 CLI。
- 不做录音回放界面（实时为主；持久化后续可加）。
- 不做 macOS / Linux 的真机采集实现（macOS 仅用于开发期跑 `FileSource` 和测试）。

## 2. 需求约束

| 维度 | 决定 |
|---|---|
| 音频来源 | 系统声音回环（loopback） |
| 平台 | Windows（目标）；macOS 仅开发/测试 |
| 实时性 | 实时流式，低延迟（秒级出字） |
| ASR | 抽象为接口，先带 `StubTranscriber` |
| 语言 | Python |

## 3. 总体架构

三个角色，靠有界队列解耦，互不读对方内部实现：

```
┌─────────────┐  PCM帧   ┌──────────┐  音频chunk  ┌──────────────┐  结果
│ AudioSource │──────▶│ Chunker  │──────────▶│ Transcriber  │────▶
│ (抽象)      │ frameQ │ (VAD分段)│  chunkQ    │ (抽象)       │
└─────────────┘        └──────────┘           └──────────────┘
   生产者线程              消费/生产              消费者协程
```

关键设计决策：**采集源也抽象一层**。`pipeline` 只依赖 `AudioSource` 与 `Transcriber` 两个协议，不认任何 WASAPI / Whisper 细节。因此：

- macOS 开发期可用 `FileSource`（喂 wav）+ `StubTranscriber` 把整条链路跑通、测试全绿；
- 只有真正的 `WASAPILoopbackSource` 是 Windows 专属，换真机时只换一个文件。

### 包结构

```
smoco/
  audio.py       # 共享类型：AudioFormat、AudioChunk、重采样/下混辅助
  config.py      # 采样率、VAD 阈值、最长/最短 chunk 等配置
  source/
    base.py      # AudioSource 协议 + SourceError
    wasapi.py    # WASAPILoopbackSource（Windows / PyAudioWPatch）
    file.py      # FileSource（喂 wav，跨平台，开发&测试用）
  chunker.py     # VAD + 分段逻辑，输出 AudioChunk
  transcriber/
    base.py      # Transcriber 协议 + TranscriptResult
    stub.py      # StubTranscriber（打日志 + 落 wav）
  pipeline.py    # 串起三者 + 生命周期/背压/优雅关闭
  __main__.py    # CLI：列设备、选采集源、启停
```

### 并发模型

- **采集线程**（`AudioSource` 内部）→ 向 `frameQ`（有界）推 30ms 帧；
- **chunker worker**：消费 `frameQ`，跑 VAD，向 `chunkQ`（有界）推 chunk；
- **转写协程**：异步消费 `chunkQ`，调用 `Transcriber.transcribe`，产出结果。

有界队列即背压，防止 ASR 跟不上时无限堆积。

## 4. 音频格式与切分规则

### 统一音频格式

管线内部一律 **16 kHz 单声道 16-bit PCM（S16LE）**：

- `webrtcvad` 仅认 8/16/32/48 kHz 且帧长须为 10/20/30 ms；
- 多数 ASR（尤其 Whisper）偏好 16 kHz；
- WASAPI 通常给 48 kHz float / 立体声 → 在 `source` 层重采样 + 下混到 16 kHz mono。

**帧长**：固定 **30 ms**（16 kHz → 960 样本/帧），作为 VAD 最小单位。

### VAD

默认 `webrtcvad-wheels`（纯 CPU、轻、无重依赖）。VAD 做成可替换接口（如 `Vad` 协议），未来接 Silero 时不动 chunker 主体。

### chunk 切分规则

- 帧被判为"有声" → 开始/继续累加进当前段；
- 连续静音 **≥ `silence_ms`（默认 300 ms）** → 关闭当前段，作为一个 chunk 发出；
- 段长度 **≥ `max_chunk_ms`（默认 15000 ms）** → 强制切出（保证延迟上限，防滔滔不绝不切）；
- 段长度 **< `min_chunk_ms`（默认 200 ms）** → 丢弃（过滤咔嗒/噪声脉冲）；
- 每个 chunk 可选带前后少量 padding（默认前后各 50 ms）给 ASR 留上下文；
- chunk 结构：`AudioChunk(id, pcm: bytes, start_time, end_time, sample_rate, is_final)`。

### 背压

- `frameQ` / `chunkQ` 有界（默认各 ~1 s 容量）；
- 队列满 → **丢弃最旧帧 + 打 `WARNING`**（实时音频积压无意义），绝不阻塞采集线程；
- 丢弃策略可配置：`drop_oldest`（默认）/ `block` / `drop_newest`。

## 5. 核心抽象接口

### `AudioSource`（同步阻塞）

```python
class AudioSource(Protocol):
    @property
    def audio_format(self) -> AudioFormat: ...   # 16 kHz mono S16LE
    def start(self) -> None: ...                 # 打开设备/文件，启动采集线程
    def read_frame(self) -> bytes | None: ...    # 阻塞读一个 30 ms 帧；None = 结束
    def stop(self) -> None: ...                  # 关闭设备，释放资源
```

- `WASAPILoopbackSource`：PyAudioWPatch 打开默认 loopback 设备，内部线程把 WASAPI 缓冲重采样下混为 16 kHz mono 30 ms 帧入队，`read_frame` 出队。
- `FileSource`：按 30 ms 步长喂 wav（可调播放倍率），读完返回 `None`。macOS 开发/测试依赖它。

### `Transcriber`（异步）

```python
class TranscriptResult(TypedDict):
    chunk_id: str
    text: str
    start_time: float
    end_time: float
    is_final: bool
    error: str | None

class Transcriber(Protocol):
    sample_rate: int                             # 期望输入采样率（= 16000）
    async def transcribe(self, chunk: AudioChunk) -> TranscriptResult: ...
    async def close(self) -> None: ...
```

- 异步：将来接云端 API 一定要 I/O 并发；
- `StubTranscriber`：`await asyncio.sleep(0)` 立即返回 `{"text": "", "is_final": True, ...}`，并把 chunk 落成 wav 供肉眼检查切分；
- `is_final` 为将来"实时部分结果 + 句末最终结果"留口子，stub 一律 `True`。

## 6. 错误处理

原则：**别让单个故障毒死整条管线**。

| 场景 | 行为 |
|---|---|
| 采集设备掉线/被占用 | `AudioSource` 抛 `SourceError` → pipeline 停采集、排空队列、向上报错；CLI 可重连 |
| 单个 chunk 转写失败 | `Transcriber` 在 `TranscriptResult.error` 带错误，**只跳过该 chunk**，继续后续 |
| 队列满（ASR 跟不上） | 丢最旧帧 + `WARNING`（默认）；可配 `block`/`drop_newest` |
| Ctrl-C / 关闭 | 收信号 → 停采集 → 带超时（默认 5 s）排空队列 → `transcriber.close()` → 干净退出 |
| 重采样/下混异常 | 视为坏帧丢弃 + 计数告警，不中断 |

所有错误走 `logging`，结构化字段（chunk_id、时间戳、设备名）。

## 7. 测试策略

测试**不依赖真实音频设备**——全部走 `FileSource` 或合成 PCM，CI 无需声卡，且在 macOS 上可全绿。

- **单元**
  - `chunker`：合成 PCM（交替有声/静音段）喂入，断言切出 chunk 数量、边界、`max_chunk_ms` 强制切、`< min_chunk_ms` 被丢；
  - `audio.py`：48 k→16 k 重采样、立体声→单声道数值正确性；
  - 背压：消费端故意 sleep，验证丢最旧帧、告警、采集不阻塞。
- **Transcriber 契约**：`FakeTranscriber` 返回固定文案，验证 pipeline 调用契约。
- **集成**：`FileSource` + 真 `chunker` + `StubTranscriber`/`FakeTranscriber`，端到端跑一段 wav，断言 chunk 序列 + 结果。**macOS 上可全绿。**
- **Windows 真机手动验证**（CI 跑不了，按下文清单执行）。

### Windows 真机验证清单

1. `python -m smoco list-devices` 能列出 loopback 设备并选中默认渲染端点；
2. 播放任一系统音频（如 YouTube 视频），CLI 启动后能持续采集；
3. `StubTranscriber` 落盘的 wav 能听到声音、且按静音切成多段；
4. 停止播放时不再产生新 chunk（VAD 正确判定静音）；
5. Ctrl-C 后进程在 5 s 内干净退出，无僵尸线程/设备占用残留；
6. 拔掉/切换默认输出设备时给出明确错误而非崩溃。

## 8. 依赖（初步）

- `pyaudiowpatch`（WASAPI loopback，Windows）
- `webrtcvad-wheels`（VAD）
- `numpy`（重采样/下混数值运算）
- `soundfile` 或标准库 `wave`（FileSource 读 wav、StubTranscriber 落 wav）
- 开发：`pytest`、`pytest-asyncio`

> 运行时 WASAPI 依赖只在 Windows 装；macOS 开发环境可装 `pyaudiowpatch` 之外的其余依赖即可跑 `FileSource` 与测试。

## 9. 开放问题 / 后续

- 接哪个真实 ASR（本地 faster-whisper / 云端 API）——后续单独一轮设计，复用 `Transcriber` 接口。
- 实时部分结果（流式 ASR 的 partial/final）策略——`is_final` 已留口子。
- 持久化（音频/转写落盘或入库）——非目标，后续按需加。
