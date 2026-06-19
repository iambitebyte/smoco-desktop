# Whisper 远程转写集成

## 概述

通过 HTTP API 调用远程 Whisper 模型进行转写，支持多语言实时语音识别。

## 组件

### 1. WhisperRemoteTranscriber（客户端）

位置：`smoco/transcriber/whisper_remote.py`

**功能：**
- 通过 HTTP API 发送音频块到 Whisper 服务器
- 接收转写结果并返回标准格式

**接口：**
```python
class WhisperRemoteTranscriber(Transcriber):
    def __init__(self, api_url: str, language: str = "ja", timeout: float = 30.0)
    async def transcribe(self, chunk: AudioChunk) -> TranscriptResult
    async def close(self)
```

### 2. Whisper API 服务器（服务端）

位置：`whisper-server/whisper_api_server.py`

**功能：**
- 接收 raw PCM 音频（16kHz mono S16LE）
- 调用 Whisper 模型转写
- 返回 JSON 格式结果

**API 端点：**
- `POST /transcribe?language=ja`：转写音频
- `GET /health`：健康检查

**请求格式：**
```
POST /transcribe?language=ja
Content-Type: audio/raw

<16kHz mono S16LE 音频数据>
```

**响应格式：**
```json
{
  "text": "转写结果",
  "language": "ja",
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "片段1"}
  ]
}
```

## 数据流

```
Windows 采集 → AudioChunk (S16LE bytes)
           → HTTP POST (raw body)
           → Whisper 服务器
           → 转写 (Whisper model)
           → JSON 响应
           → TranscriptResult
           → 显示文本
```

## 语言支持

Whisper 支持 99 种语言，常用：
- `ja`：日语
- `zh`：中文
- `en`：英语
- `ko`：韩语
- `fr`：法语
- `de`：德语
- `es`：西班牙语

## 性能考虑

- **网络延迟**：建议 Whisper 服务器与客户端在同一局域网
- **模型大小**：medium 模型约 3.6M，large-v3 约 2.9G
- **GPU 要求**：推荐使用 GPU 加速（CUDA）
- **并发**：可部署多个实例负载均衡

## 配置

客户端配置：
```bash
--whisper-url http://server:8000  # API 地址
--whisper-lang ja                  # 语言代码
```

服务器配置：
```bash
--model-name medium                 # 或 --model-path
--device cuda                       # 或 cpu
--port 8000                         # 监听端口
```
