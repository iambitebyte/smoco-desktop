# smoco

采集**系统声音**（loopback）→ VAD 切块 → 通过抽象转写接口送出 ASR 的实时流式管线。

- 目标平台：**Windows**（WASAPI loopback）。
- 开发/测试：macOS 上用 `FileSource`（喂 wav）+ `StubTranscriber` 跑通整条链路与全部单测；只有 `WASAPILoopbackSource` 是 Windows 专属。
- ASR 引擎抽象为 `Transcriber` 接口，先带 `StubTranscriber`；后续接本地 Whisper / 云端 API 只需新增一个实现。

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

采集系统声音（默认输出设备）并转写：

```bash
smoco run --wasapi --stub-out ./chunks
```

列出 WASAPI loopback 设备：

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
6. 拔掉/切换默认输出设备时给出明确错误而非崩溃。
7. `smoco run --wasapi` 能列出渲染端点、默认设备标注正确；
8. 输入序号后采集的是**所选设备**的声音（可把 Teams 输出指到该设备验证）；
9. 回车默认采集的是系统默认输出设备；
10. `--device N` 与交互选择结果一致；
11. 越界/非数字输入给出清晰提示并可重试。

## 架构

```
AudioSource(同步,线程) → Chunker(VAD分段) → asyncio.Queue → Transcriber(异步)
```

`AudioSource` 与 `Transcriber` 均为可替换协议；`pipeline.py` 只依赖这两个协议。详见 `docs/superpowers/specs/` 与 `docs/superpowers/plans/`。
