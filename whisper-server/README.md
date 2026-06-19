# Whisper API 服务器

为 smoco-desktop 提供 Whisper 转写 API 服务。

## 环境要求

- Python 3.10+
- CUDA GPU（推荐）
- Whisper 模型文件

## 安装

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install openai-whisper fastapi uvicorn
```

## 运行

### 使用本地模型文件

```bash
CUDA_VISIBLE_DEVICES=2 python whisper_api_server.py \
    --model-path ~/models/custom/whisper/medium.pt \
    --host 0.0.0.0 \
    --port 8000
```

### 使用内置模型（自动下载）

```bash
CUDA_VISIBLE_DEVICES=2 python whisper_api_server.py \
    --model-name medium \
    --port 8000
```

### 后台运行

```bash
nohup python whisper_api_server.py --model-path ~/models/custom/whisper/medium.pt > server.log 2>&1 &
```

## API 端点

### POST /transcribe

转写音频。

**请求：**
```
POST /transcribe?language=ja
Content-Type: audio/raw

<二进制音频数据，16kHz mono S16LE>
```

**响应：**
```json
{
  "text": "转写结果",
  "language": "ja",
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "片段1"},
    {"start": 2.5, "end": 5.0, "text": "片段2"}
  ]
}
```

### GET /health

健康检查。

**响应：**
```json
{"status": "ok", "model": "模型路径"}
```

## 模型选择

| 模型 | 大小 | 速度 | 准确率 |
|------|------|------|--------|
| tiny | ~73M | 最快 | 较低 |
| medium | ~3.6M | 中等 | 中等 |
| large-v3 | ~2.9G | 较慢 | 最高 |

## 与 smoco-desktop 集成

在 Windows 上运行：

```cmd
uv run smoco run --wasapi --meter --whisper-url http://server-ip:8000 --whisper-lang ja
```

## 故障排查

### 模型加载失败

检查模型文件是否存在：
```bash
ls -lh ~/models/custom/whisper/
```

### CUDA 错误

检查 GPU 可用性：
```bash
nvidia-smi
echo $CUDA_VISIBLE_DEVICES
```

### 端口占用

检查端口是否被占用：
```bash
lsof -i :8000
```
