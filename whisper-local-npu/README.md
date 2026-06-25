# Whisper 本地 OpenVINO 转写器

在 Intel Core Ultra（带 NPU/GPU）的 Windows 上，用 **openvino-genai** 跑 Whisper，推理可走 **NPU/GPU/CPU**。
对外 HTTP 契约与 `whisper-local/`（faster-whisper CPU 版）一致，smoco / GUI 可无感切换。

## 前置条件

1. **Intel 驱动**已安装：
   - NPU：设备管理器可见 "Intel(R) AI Boost" 类设备
   - GPU：Intel Arc 显卡驱动
2. 验证设备可见：
   ```bash
   uv run python -c "from openvino import Core; print(Core().available_devices)"
   ```
   输出里要有 `NPU` 或 `GPU` 或 `CPU`。

## 安装

```bash
cd whisper-local-npu
uv sync
```

## 准备 INT8 模型（导出一次）

NPU/GPU 需要 OpenVINO IR（INT8）格式模型。用 Optimum 从 HuggingFace 导出：

```bash
pip install optimum[openvino]
optimum-cli export openvino --model openai/whisper-small --weight-format int8 whisper-small-ov
```

- 原始模型从 HuggingFace 拉（国内可用镜像：`set HF_ENDPOINT=https://hf-mirror.com`）
- 体积：small ≈ 466MB，medium ≈ 1.5G；可换 `openai/whisper-large-v3-turbo` / `distil-large-v3` 再导（更快更准）
- INT8 是 NPU/GPU 友好格式（Series 1 NPU 上 FP16 常跑不动）

## 启动

**方式 1：双击 `start-npu-api.bat`**（交互式选 语言/模型目录/端口/设备）

**方式 2：命令行**
```bash
# 使用 NPU（默认）
uv run python whisper_npu_api.py --model-dir whisper-small-ov --language ja --port 8000

# 使用 GPU
uv run python whisper_npu_api.py --model-dir whisper-small-ov --language ja --port 8000 --device GPU

# 使用 CPU（调试用）
uv run python whisper_npu_api.py --model-dir whisper-small-ov --language ja --port 8000 --device CPU
```

参数：
- `--model-dir`：OpenVINO IR 模型目录（必填，或用 `--interactive`）
- `--language`：默认 `ja`（ja/zh/en/ko/fr/de/es）
- `--device`：默认 `NPU`，可指定 `GPU`/`CPU`（**大小写不敏感**，支持 gpu/GPU/Gpu 等写法）
- `--port`：默认 `8000`
- `--host`：默认 `127.0.0.1`
- `--interactive`：交互式配置

### 设备选择建议
- **NPU**：功耗最低，适合笔记本电脑，推理速度中等
- **GPU**：性能最好，适合 Intel Arc 显卡，推理速度快
- **CPU**：通用兼容性好，用于调试或无 NPU/GPU 的机器

### 首次启动会编译模型

openvino-genai 首次用某模型+设备时会为相应设备编译（几十秒~几分钟）。可设缓存加速后续启动：
```bash
set OV_CACHE_DIR=.ov-cache
```

不同设备会各自编译一次，使用缓存后第二次启动明显变快。

## API

- `GET /health` → `{"status":"ok","model":...,"device":"NPU|GPU|CPU","mode":"local-npu"}`
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
| 算力 | CPU | NPU/GPU/CPU（可选） |
| 模型 | 原始 Whisper 名 | OpenVINO IR INT8 目录 |
| 契约 | 相同 | 相同 |
| 功耗 | 较高 | NPU 最低/GPU 中等 |
| 性能 | 中等 | GPU 最高/NPU 中等 |

## Windows 真机验证清单

1. `Core().available_devices` 能看到 `NPU` 或 `GPU`；
2. `optimum-cli export ... --weight-format int8` 能导出 IR 目录；
3. `uv run pytest tests/` 三个契约测试通过；
4. `uv run python whisper_npu_api.py --model-dir <dir> --language ja --device NPU/GPU/CPU` 启动后 `GET /health` 返回 200；
5. 首次设备编译在预期内（或设了 `OV_CACHE_DIR` 后二次启动明显变快）；
6. GUI 选 `http://127.0.0.1:8000` 后，播放日语音频能转出正确日文；
7. 与 `whisper-local`（CPU）对比：质量相当、功耗明显更低（NPU）/性能更高（GPU）。

### 设备性能参考
- **NPU（Intel AI Boost）**：Series 1 ~11TOPS，Series 2 更高，功耗最低
- **GPU（Intel Arc）**：推理速度最快，适合有独显的机器
- **CPU**：通用兼容，性能中等，功耗较高
