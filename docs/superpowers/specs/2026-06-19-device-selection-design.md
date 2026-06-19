# 采集前交互式设备选择 — 设计文档

- **日期**：2026-06-19
- **状态**：待用户审阅
- **所属项目**：smoco（系统声音实时流式转写管线）
- **基线**：master 分支已合并的 11 任务实现（`feat/audio-transcription`）

## 1. 目标与背景

当前 `smoco run --wasapi` 直接采集 Windows **默认输出设备**（`defaultOutputDevice`）的 loopback，用户无法选择具体设备。用户希望：**采集开始前先列出可选设备，交互式选一个，选好后再开始采集**——典型场景是 Teams 把输出指到某个非默认设备（如耳机）时，能选到那一路。

### 附带修复

当前 `WASAPILoopbackSource.list_devices()` 枚举的是**输入设备**（`maxInputChannels > 0`，即麦克风），对 loopback 场景是错的（上轮终审 deferred 的 issue #7）。本次一并修正为枚举 WASAPI **渲染端点**（`maxOutputChannels > 0`）。

### 非目标（YAGNI）

- 不做「同时采集多个设备」。
- 不做设备热插拔后自动重选/重连（超出范围）。
- 不改 macOS 开发路径（`--file`）。
- 不做 TUI/GUI；保持 CLI + 文本编号菜单。

## 2. 需求约束

| 维度 | 决定 |
|---|---|
| 触发 | `smoco run --wasapi` 且未指定 `--device` 时，进入交互选择 |
| 选择方式 | 列出渲染设备编号，用户输数字；**回车 = 默认设备** |
| 跳过提示 | 可选 `--device N` 直接指定（脚本场景） |
| 默认设备 | `defaultOutputDevice`，列表中标注 |
| 列出对象 | WASAPI 渲染端点（`maxOutputChannels > 0`） |

## 3. 设计

### 3.1 `list_devices()` 修正（`smoco/source/wasapi.py`）

枚举 WASAPI 渲染端点，每项带 `index / name / sample_rate / channels / is_default`：

```python
@staticmethod
def list_devices() -> list[dict]:
    if not _AVAILABLE:
        return []
    pa = pyaudio.PyAudio()
    try:
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_out = wasapi["defaultOutputDevice"]
        out = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("hostApi") != wasapi["index"]:
                continue
            if info.get("maxOutputChannels", 0) <= 0:   # 只要渲染端点
                continue
            out.append({
                "index": int(info["index"]),
                "name": info["name"],
                "sample_rate": int(info["defaultSampleRate"]),
                "channels": int(info["maxOutputChannels"]),
                "is_default": int(info["index"]) == int(default_out),
            })
        return out
    finally:
        pa.terminate()
```

> 只在 Windows 可运行；macOS 上 `_AVAILABLE=False` 返回 `[]`，需走真机验证。

### 3.2 纯函数 `pick_device`（`smoco/source/wasapi.py` 或 CLI 模块）

把「解析用户输入 → 设备 index」从 I/O 里剥离，使其可单测：

```python
def pick_device(devices: list[dict], choice: str) -> int:
    """根据用户输入选择设备 index。
    - choice 为空（回车）        -> 默认设备 index
    - choice 是列表中某序号(1..n) -> 该设备 index
    - 越界 / 非数字 / 无默认设备  -> 抛 ValueError
    """
```

序号是**菜单展示序号**（1..n），不是底层 `index`。`devices` 至少要有一项；若没有默认设备（理论上不会），回车也抛 `ValueError`。

### 3.3 CLI 交互壳（`smoco/__main__.py`）

`run --wasapi` 流程改为：

1. 若给了 `--device N`：直接用 `N`，跳过交互。
2. 否则：调 `WASAPILoopbackSource.list_devices()`。
   - 空列表 → 打印「找不到 WASAPI 渲染设备」并 `return 1`。
   - 非空 → 打印编号列表（`*` 标默认），提示「输入序号，回车=默认」，最多 3 次重试：
     - `input()` 读一行 → `pick_device(devices, line)` 解析。
     - 成功 → 用得到的 `index` 构造源；`ValueError` → 提示并重试。
     - 3 次都失败 → 报错退出（`return 1`）。
3. 用选定 `device_index` 构造 `WASAPILoopbackSource(target=fmt, device_index=index)`。
4. 其余管线（Chunker / Transcriber / Pipeline）不变。

`run` 子命令新增 `--device` 参数（int，可选）。

### 3.4 错误处理

| 场景 | 行为 |
|---|---|
| `list_devices()` 返回空（非 Windows 或无设备） | 打印提示，`return 1` |
| 用户输入非数字 / 越界 | 提示「无效选择」，重试（≤3 次） |
| 重试用尽 | 报错，`return 1` |
| `--device N` 指定的设备打开失败 | 由 `WASAPILoopbackSource.start()` 抛 `SourceError`，pipeline 捕获存 `pipe.error`，CLI 返回 1（沿用上轮已实现的错误退出） |

### 3.5 不变的部分

`WASAPILoopbackSource.__init__` 已有 `device_index` 参数，`start()` 已支持 `self._device_index`——**无需改采集/回调逻辑**，只改 CLI 如何构造它，以及 `list_devices` 的枚举口径。

## 4. 测试策略

测试**不依赖真实音频设备**，全部在 macOS 上跑：

- **`pick_device` 纯函数单测**（核心）：
  - 回车 → 默认设备 index；
  - 合法数字 `1..n` → 对应设备 index；
  - 越界（0、n+1）→ `ValueError`；
  - 非数字（"abc"）→ `ValueError`；
  - 空设备列表 → `ValueError`。
- **CLI 选择循环**：用 monkeypatch 把 `input()` 替换成预设序列、把 `list_devices` 替换成固定假数据，断言最终构造源时传入的 `device_index` 正确、重试/退出码正确。
- **`--device N` 路径**：不触发交互，直接用 N。
- `list_devices` 真实枚举 + 真实 `input()` 交互 → Windows 真机清单。

## 5. Windows 真机验证清单（追加到 README）

7. `smoco run --wasapi` 能列出渲染端点、默认设备标注正确；
8. 输入序号后采集的是**所选设备**的声音（可把 Teams 输出指到该设备验证）；
9. 回车默认采集的是系统默认输出设备；
10. `--device N` 与交互选择结果一致；
11. 越界/非数字输入给出清晰提示并可重试。

## 6. 开放问题

- 设备名在某些 Windows 版本/驱动下可能重复或冗长，是否需要去重/截断展示——留到真机看实际列表再定，当前原样展示。
