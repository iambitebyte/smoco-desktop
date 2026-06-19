# 采集前交互式设备选择 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `smoco run --wasapi` 加上采集前的交互式设备选择——列出 WASAPI 渲染端点、用户输序号（回车=默认）选一个，选好后才开始采集；并修正 `list_devices` 错列麦克风的问题。

**Architecture:** 把可测逻辑从 I/O 里剥离成纯函数 `pick_device`（解析选择）和 `_prompt_for_device`（带可注入 `input_fn` 的重试循环）；`list_devices` 改为枚举渲染端点（`maxOutputChannels>0`）；`cmd_run` 在 `--wasapi` 分支里先解析设备 index（`--device` 直传或交互），失败返回 1，成功才构造源。采集/回调逻辑不动（`device_index` 参数已存在）。

**Tech Stack:** Python ≥3.10、argparse、pytest（含 monkeypatch）。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `smoco/source/wasapi.py` | 修正 `list_devices()`（渲染端点） |
| `smoco/__main__.py` | 新增 `pick_device`、`_prompt_for_device`、`_resolve_device`；改 `cmd_run` + 加 `--device` 参数 |
| `tests/test_device_selection.py` | `pick_device`/`_prompt_for_device`/`_resolve_device`/`cmd_run` 单测 |
| `README.md` | 追加 Windows 真机清单 7–11 |

实现顺序：纯函数 → 重试循环 → `list_devices` 修正 → CLI 串联（含 `--device`）→ README。

---

## Task 1: `pick_device` 纯函数

**Files:**
- Modify: `smoco/__main__.py`
- Test: `tests/test_device_selection.py`

- [ ] **Step 1: 写失败测试 `tests/test_device_selection.py`**

```python
import pytest
from smoco.__main__ import pick_device

DEVS = [
    {"index": 5, "name": "Speakers", "sample_rate": 48000, "channels": 2, "is_default": True},
    {"index": 9, "name": "Headphones", "sample_rate": 48000, "channels": 2, "is_default": False},
]


def test_empty_choice_returns_default_index():
    assert pick_device(DEVS, "") == 5


def test_numeric_choice_returns_device_index():
    assert pick_device(DEVS, "1") == 5
    assert pick_device(DEVS, "2") == 9


def test_whitespace_only_choice_returns_default():
    assert pick_device(DEVS, "   ") == 5


def test_out_of_range_raises():
    with pytest.raises(ValueError):
        pick_device(DEVS, "0")
    with pytest.raises(ValueError):
        pick_device(DEVS, "3")


def test_non_numeric_raises():
    with pytest.raises(ValueError):
        pick_device(DEVS, "abc")


def test_empty_devices_raises():
    with pytest.raises(ValueError):
        pick_device([], "1")


def test_no_default_and_empty_choice_raises():
    devs = [{"index": 1, "name": "x", "sample_rate": 48000, "channels": 2, "is_default": False}]
    with pytest.raises(ValueError):
        pick_device(devs, "")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_device_selection.py -q`
Expected: FAIL (`ImportError: cannot import name 'pick_device'`)。

- [ ] **Step 3: 在 `smoco/__main__.py` 加 `pick_device`**

在 `def _build_parser` 之前插入：

```python
def pick_device(devices: list[dict], choice: str) -> int:
    """把用户的菜单输入解析成底层设备 index。
    - 空白输入        -> 默认设备的 index（需存在默认设备）
    - "1".."n"        -> devices[n-1]["index"]
    - 越界/非数字/空列表/无默认 -> ValueError
    """
    if not devices:
        raise ValueError("没有可选设备")
    choice = (choice or "").strip()
    if choice == "":
        for d in devices:
            if d.get("is_default"):
                return int(d["index"])
        raise ValueError("没有默认设备，请输入序号")
    if not choice.isdigit():
        raise ValueError(f"无效输入（需数字）: {choice!r}")
    n = int(choice)
    if not (1 <= n <= len(devices)):
        raise ValueError(f"序号超出范围: {n}（可选 1..{len(devices)}）")
    return int(devices[n - 1]["index"])
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_device_selection.py -q`
Expected: `7 passed`。

- [ ] **Step 5: 提交**

```bash
git add smoco/__main__.py tests/test_device_selection.py
git commit -m "feat(cli): pick_device 纯函数（解析设备选择）"
```

---

## Task 2: `_prompt_for_device` 重试循环

**Files:**
- Modify: `smoco/__main__.py`
- Test: `tests/test_device_selection.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_device_selection.py` 末尾追加：

```python
from smoco.__main__ import _prompt_for_device


def test_prompt_first_try_valid(capsys):
    inputs = iter(["2"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs))
    assert idx == 9
    out = capsys.readouterr().out
    assert "Headphones" in out
    assert "*" in out  # 默认设备标记


def test_prompt_retries_then_succeeds(capsys):
    inputs = iter(["abc", "99", "1"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs), max_tries=3)
    assert idx == 5


def test_prompt_exhausts_tries_returns_none(capsys):
    inputs = iter(["x", "y", "z"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs), max_tries=3)
    assert idx is None


def test_prompt_eof_returns_none(capsys):
    def boom(_p):
        raise EOFError
    idx = _prompt_for_device(DEVS, input_fn=boom)
    assert idx is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_device_selection.py -q`
Expected: FAIL（`ImportError: cannot import name '_prompt_for_device'`）。

- [ ] **Step 3: 在 `smoco/__main__.py` 加 `_prompt_for_device`**

紧跟 `pick_device` 之后插入：

```python
def _prompt_for_device(devices: list[dict], input_fn=input, max_tries: int = 3) -> int | None:
    """打印编号菜单，循环读取用户选择。成功返回设备 index，用尽重试/EOF 返回 None。"""
    print("可用的 WASAPI 输出设备：")
    for i, d in enumerate(devices, 1):
        mark = "*" if d.get("is_default") else " "
        print(f"  {mark} [{i}] {d['name']}  ({d['sample_rate']}Hz, {d['channels']}ch)")
    print("输入序号选择，回车=默认设备。")
    for _ in range(max_tries):
        try:
            line = input_fn("> ")
        except EOFError:
            return None
        try:
            return pick_device(devices, line)
        except ValueError as e:
            print(f"无效选择: {e}")
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_device_selection.py -q`
Expected: `11 passed`（7 + 4）。

- [ ] **Step 5: 提交**

```bash
git add smoco/__main__.py tests/test_device_selection.py
git commit -m "feat(cli): _prompt_for_device 交互式重试循环"
```

---

## Task 3: 修正 `list_devices` 枚举渲染端点

**Files:**
- Modify: `smoco/source/wasapi.py`

> 无 macOS 单测（`_AVAILABLE=False` 时返回 `[]`，真实枚举走 Windows 真机清单）。仅验证：导入安全 + macOS 上 `list_devices()==[]`。

- [ ] **Step 1: 替换 `list_devices` 方法**

在 `smoco/source/wasapi.py` 中，把整个 `list_devices` 静态方法替换为：

```python
    @staticmethod
    def list_devices() -> list[dict]:
        """枚举 WASAPI 渲染端点（loopback 可采集的输出设备）。
        返回 [{index, name, sample_rate, channels, is_default}, ...]。"""
        if not _AVAILABLE:
            return []
        pa = pyaudio.PyAudio()
        try:
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out = int(wasapi["defaultOutputDevice"])
            out = []
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if int(info.get("hostApi", -1)) != int(wasapi["index"]):
                    continue
                if int(info.get("maxOutputChannels", 0)) <= 0:   # 只要渲染端点
                    continue
                out.append({
                    "index": int(info["index"]),
                    "name": str(info["name"]),
                    "sample_rate": int(info["defaultSampleRate"]),
                    "channels": int(info["maxOutputChannels"]),
                    "is_default": int(info["index"]) == default_out,
                })
            return out
        finally:
            pa.terminate()
```

（其余文件内容不动。）

- [ ] **Step 2: 验证导入安全 + macOS 返回空**

Run:
```bash
python -c "from smoco.source.wasapi import WASAPILoopbackSource; print(WASAPILoopbackSource.list_devices())"
pytest -q
```
Expected: `[]`，且全量测试通过（`25 passed`）。

- [ ] **Step 3: 提交**

```bash
git add smoco/source/wasapi.py
git commit -m "fix(source): list_devices 改为枚举 WASAPI 渲染端点（非麦克风）"
```

---

## Task 4: CLI 串联 + `--device` 参数

**Files:**
- Modify: `smoco/__main__.py`
- Test: `tests/test_device_selection.py`

- [ ] **Step 1: 追加 `_resolve_device` 与 `cmd_run` 的单测**

在 `tests/test_device_selection.py` 末尾追加：

```python
from smoco.__main__ import _resolve_device, _build_parser


class _Args:
    def __init__(self, device):
        self.device = device


def test_resolve_device_explicit_arg_skips_prompt():
    assert _resolve_device(_Args(device=7), list_devices_fn=lambda: DEVS,
                            input_fn=lambda _p: pytest.fail("不应提示")) == 7


def test_resolve_device_interactive_uses_prompt(capsys):
    idx = _resolve_device(_Args(device=None), list_devices_fn=lambda: DEVS,
                          input_fn=lambda _p: "2")
    assert idx == 9


def test_resolve_device_empty_list_returns_none(capsys):
    assert _resolve_device(_Args(device=None), list_devices_fn=lambda: []) is None


def test_resolve_device_prompt_exhausted_returns_none(capsys):
    inputs = iter(["x", "y", "z"])
    assert _resolve_device(_Args(device=None), list_devices_fn=lambda: DEVS,
                           input_fn=lambda _p: next(inputs)) is None


def test_cmd_run_wasapi_uses_selected_device(monkeypatch):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav
    captured = {}

    class FakeSource:
        list_devices = staticmethod(lambda: DEVS)

        def __init__(self, target=None, device_index=None):
            captured["device_index"] = device_index

    class FakePipeline:
        def __init__(self, *a, **k):
            self.error = None

        async def run(self):
            return None

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    monkeypatch.setattr(cli, "Pipeline", FakePipeline)
    monkeypatch.setattr("builtins.input", lambda _p: "2")

    args = _build_parser().parse_args(["run", "--wasapi"])
    assert cli.cmd_run(args) == 0
    assert captured["device_index"] == 9


def test_cmd_run_wasapi_device_flag_skips_prompt(monkeypatch):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav
    captured = {}

    class FakeSource:
        list_devices = staticmethod(lambda: DEVS)

        def __init__(self, target=None, device_index=None):
            captured["device_index"] = device_index

    class FakePipeline:
        def __init__(self, *a, **k):
            self.error = None

        async def run(self):
            return None

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    monkeypatch.setattr(cli, "Pipeline", FakePipeline)
    monkeypatch.setattr("builtins.input", lambda _p: pytest.fail("不应提示"))

    args = _build_parser().parse_args(["run", "--wasapi", "--device", "5"])
    assert cli.cmd_run(args) == 0
    assert captured["device_index"] == 5


def test_cmd_run_wasapi_no_devices_returns_1(monkeypatch, capsys):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav

    class FakeSource:
        list_devices = staticmethod(lambda: [])

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    args = _build_parser().parse_args(["run", "--wasapi"])
    assert cli.cmd_run(args) == 1
    assert "找不到" in capsys.readouterr().out
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_device_selection.py -q`
Expected: FAIL（`ImportError: cannot import name '_resolve_device'`，以及 `--device` 参数不存在）。

- [ ] **Step 3: 加 `--device` 参数**

在 `smoco/__main__.py` 的 `_build_parser` 里，`run` 子命令参数区，在 `--stub-out` 之后加：

```python
    p_run.add_argument("--device", type=int, help="直接指定 WASAPI 设备 index（跳过交互选择）")
```

- [ ] **Step 4: 加 `_resolve_device` 并重写 `cmd_run`**

在 `_prompt_for_device` 之后加 `_resolve_device`：

```python
def _resolve_device(args, list_devices_fn, input_fn=input) -> int | None:
    """决定 --wasapi 用哪个设备 index。失败（无设备/重试用尽）返回 None。"""
    if args.device is not None:
        return args.device
    devices = list_devices_fn()
    if not devices:
        print("找不到 WASAPI 渲染设备（用 list-devices 查看详情）")
        return None
    return _prompt_for_device(devices, input_fn)
```

把现有的 `_make_source` 和 `cmd_run` 两个函数整体替换为：

```python
def cmd_run(args) -> int:
    fmt = AudioFormat()
    cfg = Config()
    if args.wasapi:
        from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
        if not _AVAILABLE:
            print("WASAPI 源不可用（需 Windows + pyaudiowpatch）")
            return 1
        device_index = _resolve_device(args, WASAPILoopbackSource.list_devices)
        if device_index is None:
            return 1
        source = WASAPILoopbackSource(target=fmt, device_index=device_index)
    elif args.file:
        source = FileSource(args.file, target=fmt)
    else:
        print("请指定 --file 或 --wasapi")
        return 1
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
    if pipe.error is not None:
        logging.getLogger("smoco").error("采集源错误: %s", pipe.error)
        return 1
    return 0
```

> 注意：原 `_make_source` 函数被删除（其逻辑并入 `cmd_run`）。`cmd_run` 现在显式返回退出码，不再用 `raise SystemExit`。

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_device_selection.py -q`
Expected: `18 passed`（11 + 7）。

Run: `pytest -q`
Expected: 全量通过（`25 + 18 = 43 passed`，其中 25 是既有测试、18 是本特性新增；实际数以运行结果为准，无失败即可）。

- [ ] **Step 6: 冒烟验证 `--help`**

Run: `python -m smoco run --help`
Expected: 列出 `--file`、`--wasapi`、`--stub-out`、`--device`，退出码 0。

- [ ] **Step 7: 提交**

```bash
git add smoco/__main__.py tests/test_device_selection.py
git commit -m "feat(cli): --wasapi 采集前交互式设备选择 + --device 参数"
```

---

## Task 5: README 追加真机清单

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 在 README 的「Windows 真机验证清单」末尾追加 5 条**

在现有第 6 条之后追加：

```markdown
7. `smoco run --wasapi` 能列出渲染端点、默认设备标注正确；
8. 输入序号后采集的是**所选设备**的声音（可把 Teams 输出指到该设备验证）；
9. 回车默认采集的是系统默认输出设备；
10. `--device N` 与交互选择结果一致；
11. 越界/非数字输入给出清晰提示并可重试。
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: README 追加设备选择真机验证清单"
```

- [ ] **Step 3: 全量回归**

Run: `pytest -q`
Expected: 全部通过，无失败。

---

## Self-Review（plan 完成后自查记录）

- **Spec 覆盖**：`list_devices` 改渲染端点（Task 3）✓；`pick_device` 纯函数（Task 1）✓；`_prompt_for_device` 重试（Task 2）✓；CLI 交互壳 + `--device`（Task 4）✓；错误处理（无设备→return1、越界重试、用尽 return None→1）（Task 2/4）✓；测试策略（纯函数 + 注入 input_fn + monkeypatch cmd_run，macOS 全绿）（Task 1/2/4）✓；Windows 清单（Task 5）✓。
- **占位符**：无 TBD/TODO；每步含完整代码与确切命令。
- **类型一致**：`pick_device(devices, choice)->int`、`_prompt_for_device(devices, input_fn, max_tries)->int|None`、`_resolve_device(args, list_devices_fn, input_fn)->int|None` 在各 Task 间签名一致；`list_devices` 返回的 dict 字段（index/name/sample_rate/channels/is_default）在 `pick_device`/`_prompt_for_device`/测试 fixture `DEVS` 间一致；`WASAPILoopbackSource(target=, device_index=)` 与既有构造函数签名一致。
