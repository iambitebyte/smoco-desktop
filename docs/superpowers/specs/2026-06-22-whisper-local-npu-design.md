# whisper-local-npu（NPU 版本地 Whisper 服务） — 设计文档

- **日期**：2026-06-22
- **状态**：待用户审阅
- **所属项目**：smoco
- **动机**：Intel Core Ultra 5（无独显）上，现有 `whisper-local`（faster-whisper, CPU）只用了 CPU，**NPU 闲置**。新建一个走 NPU 的本地 Whisper 服务，让现有 GUI 无感切换，降功耗、提吞吐。

## 1. 目标与背景

新建 `whisper-local-npu/`，**镜像 `whisper-local/` 的对外契约**（FastAPI、`/health` + `POST /transcribe`、原始 PCM body、同样 JSON 返回），但推理内核换成 **openvino-genai** 的 `Whisper`，`device="NPU"`，吃 INT8 OpenVINO IR 模型。

接入方式：用户**手动起** NPU 服务（双击 `start-npu-api.bat`），在 GUI 的 startup 对话框把它的 URL（默认 `http://127.0.0.1:8000`）当一个 server 选。**GUI 代码零改动**（`asr_worker.py` 只认 HTTP 契约）。

### 非目标（YAGNI）

- 不做 GUI 的引擎选择器（手动起 + 选 URL 即可；引擎选择作为后续可选小任务）。
- 不做模型自动导出/下载（用户用 `optimum-cli` 手动导一次，`--model-dir` 指）。
- 不做 partial/final 流式（Point 1，已搁置）。
- 不替代 `whisper-local`（CPU 版保留，两者并列，二选一运行）。

## 2. 需求约束

| 维度 | 决定 |
|---|---|
| 位置 | 新建同级目录 `whisper-local-npu/`（与 `whisper-local/`、`whisper-server/` 并列） |
| 引擎 | openvino-genai `Whisper`，`device="NPU"` |
| 模型 | INT8 OpenVINO IR 目录，`--model-dir` 手动指 |
| HTTP 契约 | 与 `whisper_local_api.py` 一致（`/health` + `POST /transcribe` raw PCM） |
| 端口 | 默认 8000，`--port` 可覆盖 |
| GUI 接入 | 手动起服务 + GUI startup 选 URL，零 GUI 改动 |

## 3. 设计

### 3.1 目录结构

```
whisper-local-npu/
  pyproject.toml          # openvino-genai, fastapi, uvicorn, numpy（不含 faster-whisper）
  whisper_npu_api.py      # FastAPI 服务，/health + /transcribe，openvino-genai(NPU)
  start-npu-api.bat       # 一键起（交互选 模型目录/语言/端口）
  README.md               # 前置(NPU驱动+验证)、导出INT8模型、启动、GUI接入、缓存
```

### 3.2 `whisper_npu_api.py`

**启动自检**：
```python
from openvino import Core
devices = Core().available_devices
if "NPU" not in devices:
    print("找不到 NPU。请装 Intel NPU 驱动；当前可见设备：", devices)
    sys.exit(1)
```

**加载模型**（启动时常驻，不每请求加载）：
```python
import openvino_genai
pipe = openvino_genai.Whisper(args.model_dir, device=args.device)  # device 默认 "NPU"
```

**`GET /health`** → `{"status":"ok","model":<model_dir>,"device":<device>,"mode":"local-npu"}`。

**`POST /transcribe?language=ja`**：
- body = 原始 PCM bytes（与 `whisper_local_api.py` 一致：16k mono S16LE）
- 转成 float32：`samples = np.frombuffer(await request.body(), dtype="<i2").astype(np.float32) / 32768.0`
- **甩线程**，不卡事件循环：`result = await asyncio.to_thread(pipe.transcribe, samples, language=language)`
- 组装返回 JSON（见 3.3）
- **不走临时 wav**（openvino-genai 直接吃 numpy）

**CLI 参数**：
- `--model-dir`（必填）：OpenVINO IR 目录路径
- `--language`（默认 `ja`）
- `--device`（默认 `NPU`，可改 `GPU`/`CPU` 调试）
- `--port`（默认 `8000`）
- `--host`（默认 `127.0.0.1`）
- `--interactive`：交互菜单选 模型目录（手输路径）、语言、端口——风格镜像 `whisper_local_api.py` 的 `interactive_mode`

### 3.3 HTTP 返回契约（与 `whisper_local_api.py` 对齐）

`asr_worker.py`（GUI 客户端）**只取 `text` 字段**，所以 `text` 必须有；其余字段尽量对齐：

```json
{
  "text": "全文",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "language": "ja",
  "duration": 5.0
}
```

字段来源说明（诚实交代引擎差异）：
- `text`：`result.text`（主字段，GUI 用）
- `segments`：由 `result.chunks` 映射（`start/end/text`）
- `language`：用强制传入的 `language` 参数（openvino-genai 不像 faster-whisper 那样返回检测概率）
- `duration`：由音频样本数算 `len(samples)/16000`
- `language_probability`：**本引擎不提供，省略**（GUI 不用）

> 这点要在实现时验证 `openvino_genai.Whisper` 返回对象的确切属性名（`text`/`chunks`/`chunks[i].start|end|text`），以实测为准；若属性名不同，按实际调整映射，但 `text` 必须正确。

### 3.4 模型获取（README 给命令，用户手动导一次）

```bash
pip install optimum[openvino]
optimum-cli export openvino --model openai/whisper-small --weight-format int8 whisper-small-ov
```

- 原始模型从 HuggingFace 拉（`openai/whisper-small` 等）；国内建议 `HF_ENDPOINT=https://hf-mirror.com`
- 体积：small ≈ 466MB，medium ≈ 1.5G；可换 `whisper-large-v3-turbo` / `distil-large-v3` 再导
- INT8 是 NPU 友好格式（Series 1 NPU 上 FP16 常跑不动）
- **首次运行** openvino-genai 会为 NPU 编译模型（几十秒~几分钟），README 提示可设 `OV_CACHE_DIR` 加速后续启动

### 3.5 GUI 接入（零改动）

1. 双击 `start-npu-api.bat` 起 NPU 服务（监听 127.0.0.1:8000）
2. GUI startup 对话框里把 `http://127.0.0.1:8000` 当一个 server 选
3. `asr_worker.py` 走同一个 `/transcribe` 契约，无感切换

### 3.6 错误处理

| 场景 | 行为 |
|---|---|
| `Core().available_devices` 无 `NPU` | 启动即打印可见设备 + 明确错误，退出 |
| `openvino-genai` 未安装 | import 时提示 `uv sync`，退出 |
| `--model-dir` 路径无效/不是 IR 目录 | 启动加载时异常 → 打印明确错误退出 |
| 转写异常 | `log.exception` + HTTP 500 `{detail}`（与 `whisper_local_api.py` 一致） |
| body 为空/非 PCM | 转写返回空 text 或 400（按现有习惯，空 text 即可） |

## 4. 测试策略

**诚实交代**：openvino-genai 在 macOS 上未必装得上、NPU 更是没有。能自动测的只有**契约形状**：

- `tests/test_whisper_npu_api.py`（开头 **`pytest.importorskip("openvino_genai")`** + **`pytest.importorskip("fastapi")`**——任一装不上即跳过，绝不破坏主测试套件）：
  - 用 monkeypatch 把 `openvino_genai.Whisper` 换成返回假结果（`.text` / `.chunks`）的假类；
  - 用 FastAPI `TestClient` 打 `GET /health` → 断言字段；
  - `POST /transcribe` 传构造的 raw PCM bytes → 断言返回 JSON 含 `text`、`segments` 结构正确、且假模型的 `transcribe` 被以 numpy float32 调用（不是文件路径）。
- **真机 NPU 转写正确性 + 速度/功耗** → README Windows 清单手动验。

> 因 openvino-genai 依赖重且可能装不上，CI/本地可能整文件 skip。这是可接受的——本任务本质是 Windows/NPU 端组件，契约形状测是"能在非 NPU 环境守的底线"。

## 5. Windows 真机验证清单（追加 README 专章）

1. `python -c "from openvino import Core; print(Core().available_devices)"` 能看到 `NPU`；
2. `optimum-cli export ... --weight-format int8` 能导出 IR 目录；
3. `uv run python whisper_npu_api.py --model-dir <dir> --language ja` 启动后 `GET /health` 返回 200；
4. 首次启动的 NPU 编译耗时在预期内（或设了 `OV_CACHE_DIR` 后二次启动变快）；
5. GUI 选 `http://127.0.0.1:8000` 后，播放日语音频能转出正确日文；
6. 与 `whisper-local`（CPU）对比：转写质量相当、功耗/发热明显更低（NPU 强项），吞吐是否更高看代数。

## 6. 开放问题

- openvino-genai `Whisper` 返回对象的确切属性名以实测为准（见 3.3 备注）；若与设计假设不同，按实际调整 segments 映射。
- 是否日后补一个 GUI 引擎选择器（一键拉起 NPU 服务）——作为后续可选任务，不在本 spec。
