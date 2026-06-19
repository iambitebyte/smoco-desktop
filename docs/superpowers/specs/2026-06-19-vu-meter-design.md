# CLI 实时音量条（VU meter） — 设计文档

- **日期**：2026-06-19
- **状态**：待用户审阅
- **所属项目**：smoco
- **动机**：没有 ASR 服务时，`smoco run --wasapi` 采集后无任何可见反馈，用户无法确认「到底有没有采到声」。加一条实时音量条即可直观确认。

## 1. 目标与背景

`smoco run --meter`（配合 `--wasapi` 或 `--file`）时，在终端持续刷新一条音量条，随输入音频电平起伏。无需 ASR，纯采集侧反馈。

### 非目标（YAGNI）

- 不做频谱/FFT 可视化（只做单电平条）。
- 不做持久化电平统计/落盘。
- 不改变默认行为：不开 `--meter` 时与现在完全一致。
- 不做 GUI/TUI 框架；只用 `\r` 单行刷新。

## 2. 需求约束

| 维度 | 决定 |
|---|---|
| 触发 | `--meter` flag（opt-in） |
| 适用源 | 任意 `AudioSource`（`--wasapi` / `--file`） |
| 电平来源 | **帧级**（每个 30ms 帧的 RMS），非 chunk 级 |
| 刷新 | ~20fps（50ms），`\r` 单行重绘 |
| 日志干扰 | 开 `--meter` 时把 `smoco` logger 降到 WARNING |

## 3. 设计

### 3.1 `frame_rms`（纯函数，`smoco/audio.py`）

```python
def frame_rms(pcm: bytes, sample_width: int = 2) -> float:
    """S16LE（默认）PCM 帧的 RMS 电平，归一化到 [0,1]。
    全静音 -> 0.0；满幅（±32767）-> 1.0。空数据 -> 0.0。"""
```

实现：`np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0`，取 `sqrt(mean(x**2))`。空 bytes → 0.0。

### 3.2 `MeteringSource`（新文件 `smoco/source/metering.py`）

包一层任意 `AudioSource`，实现相同协议；`read_frame()` 委托内层、顺带更新电平：

```python
class MeteringSource:
    """装饰任意 AudioSource：透传帧，并实时更新 latest_rms / latest_peak。"""

    def __init__(self, inner: AudioSource):
        self._inner = inner
        self.latest_rms: float = 0.0
        self.latest_peak: float = 0.0

    @property
    def audio_format(self): return self._inner.audio_format

    def start(self): self._inner.start()

    def read_frame(self) -> bytes | None:
        frame = self._inner.read_frame()
        if frame:
            rms = frame_rms(frame, self._inner.audio_format.sample_width)
            self.latest_rms = rms
            self.latest_peak = max(self.latest_peak, rms)
        return frame

    def stop(self): self._inner.stop()
```

> pipeline 看到的仍是 `AudioSource`（鸭子类型），无感知。peak 不衰减（简单起见）；显示以 rms 为主。

### 3.3 `meter_bar`（纯函数，`smoco/__main__.py`）

```python
def meter_bar(rms: float, width: int = 24) -> str:
    """把 [0,1] 电平渲染成条：[████████░░░░░░░░░░░░░░░░]"""
```

用 `min(1.0, max(0.0, rms))` 钳制；填充 `width * level` 个 `█`，其余 `░`。

### 3.4 CLI 渲染协程（`smoco/__main__.py`）

`run` 子命令加 `--meter`（store_true）。`cmd_run` 中：

1. 选好源之后，若 `args.meter`：`source = MeteringSource(source)`。
2. 把渲染做成独立协程 `render_meter(source, stop_event)`：循环 `while not stop_event.is_set()`：`sys.stdout.write("\r" + meter_bar(source.latest_rms) + f" rms={source.latest_rms:.3f}")`，`flush`，`await asyncio.sleep(0.05)`。
3. 在 `pipe.run()` 之外用 `asyncio.gather` 并发跑管线和渲染；管线结束后置 `stop_event`、取消渲染协程、最后 `print()` 换行收尾。
4. 开 `--meter` 时 `logging.getLogger("smoco").setLevel(logging.WARNING)`，避免 INFO 日志刷掉音量条。

`cmd_run` 当前是 `asyncio.run(pipe.run())`；改为 `asyncio.run(_run_with_meter(pipe, source, args.meter))`，其中 `_run_with_meter` 在无 meter 时直接 `await pipe.run()`，有 meter 时 gather 管线 + 渲染。

### 3.5 并发与线程

- 采集线程写 `MeteringSource.latest_rms`（单 float 赋值）；渲染协程在主事件循环线程读它。GIL 下单 float 读写原子，最坏读到上一帧值，音量条无影响——**不加锁**。
- 渲染协程与 `pipe.run()` 在同一事件循环里 gather，管线结束即停渲染。

## 4. 错误处理

| 场景 | 行为 |
|---|---|
| 源无数据（read_frame 持续返回 None，如文件结束） | latest_rms 不更新；条停在最后值；管线结束后渲染停 |
| 空 frame | 不更新电平（read_frame 返回 None 时不更新） |
| `--meter` 与日志 | 降级到 WARNING；WARNING 及以上仍会打印（可能短暂挤掉条，可接受） |
| Ctrl-C | pipe.run 的 KeyboardInterrupt 处理照旧；渲染协程随 gather 结束被取消，收尾换行 |

## 5. 测试策略

全部 macOS 可测，无需真实设备：

- **`frame_rms`**：全零帧→0.0；满幅帧→≈1.0；已知正弦/常数帧→对应 RMS；空 bytes→0.0。
- **`meter_bar`**：0.0→全空条；1.0→满条；0.5→半条；越界（-0.1/1.5）钳制。
- **`MeteringSource`**：用 FakeSource 喂已知帧 → 断言 `latest_rms` 正确更新、`latest_peak` 单调不减；`start/stop/audio_format` 正确委托给内层；`read_frame` 透传帧字节不变；内层返回 None 时 latest_rms 不更新、返回 None。
- **渲染协程本体**（终端时序）：不单测。
- 真机 WASAPI + `--meter` 的终端刷新效果 → Windows 真机清单。

## 6. Windows 真机验证清单（追加 README）

12. `smoco run --wasapi --meter` 选设备后，音量条随系统声音起伏；
13. 不播放声音时条很低（接近空）、播放时升高，证明采集通路正常；
14. Ctrl-C 后音量条干净收尾换行，无残留。

## 7. 开放问题

- peak 衰减：当前 peak 只增不减，长时间会顶满。先不衰减（YAGNI）；若观感差再加指数衰减。
