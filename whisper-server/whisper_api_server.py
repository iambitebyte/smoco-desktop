#!/usr/bin/env python3
"""
Whisper 转写 API 服务

提供 HTTP API 供 smoco-desktop 调用。

依赖：
    pip install openai-whisper fastapi uvicorn

运行：
    CUDA_VISIBLE_DEVICES=2 python whisper_api_server.py --model-path ~/models/custom/whisper/medium.pt

API 端点：
    POST /transcribe
        Content-Type: audio/wav 或 audio/raw
        参数: ?language=ja
        返回: JSON {"text": "...", "segments": [...]}
    GET /health
        返回: {"status": "ok", "model": "..."}
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("请安装依赖: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import whisper
except ImportError:
    print("请安装依赖: pip install openai-whisper")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

app = FastAPI(title="Whisper Transcription API")
model: whisper.Whisper | None = None
model_config = {}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "model": model_config.get("path")}


@app.post("/transcribe")
async def transcribe(
    request: Request,
    language: str = "ja",
    prompt: str = "",
):
    """转写音频

    Args:
        request: FastAPI Request（包含 raw body）
        language: 语言代码（ja=日语, zh=中文, en=英语）
        prompt: 可选的提示文本，用于引导模型输出风格
    """
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    try:
        # 读取音频数据（raw body）
        audio_data = await request.body()

        # 保存为临时 WAV 文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            import wave
            with wave.open(f, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(16000)
                wav.writeframes(audio_data)
            temp_path = f.name

        # 转写
        result = model.transcribe(
            temp_path,
            language=language if language else None,
            fp16=True,  # GPU 加速
            prompt=prompt if prompt else None,
        )

        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)

        # 返回结果
        segments = []
        for seg in result["segments"]:
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })

        return JSONResponse({
            "text": result["text"],
            "language": result.get("language", language),
            "segments": segments,
        })

    except Exception as e:
        log.exception("转写失败")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    p = argparse.ArgumentParser(description="Whisper 转写 API 服务")
    p.add_argument(
        "--model-path",
        type=str,
        default="~/models/custom/whisper/medium.pt",
        help="Whisper 模型路径（.pt 文件）"
    )
    p.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="模型名称（tiny/medium/large-v3 等），与 model-path 二选一"
    )
    p.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址"
    )
    p.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口"
    )
    p.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="计算设备（cuda/cpu）"
    )

    args = p.parse_args()

    # 确定模型
    if args.model_name:
        model_path = args.model_name
        log.info(f"使用内置模型: {model_path}")
    else:
        model_path = Path(args.model_path).expanduser()
        if not model_path.exists():
            log.error(f"模型文件不存在: {model_path}")
            sys.exit(1)
        model_path = str(model_path)
        log.info(f"加载模型: {model_path}")

    global model, model_config
    model_config = {"path": model_path}

    log.info(f"设备: {args.device}")

    # 加载模型
    import torch
    device = args.device
    model = whisper.load_model(model_path, device=device)

    log.info(f"启动 API 服务: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
