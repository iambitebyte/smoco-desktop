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
