#!/usr/bin/env python3
"""
Whisper 本地 API 服务器（CPU 模式）

提供 HTTP API 供 smoco-desktop 调用。

依赖：
    uv sync

运行：
    uv run python whisper_local_api.py
    或交互式：uv run python whisper_local_api.py --interactive
"""

import argparse
import asyncio
import logging
import sys
import tempfile
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("请安装依赖: uv sync")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("请安装依赖: uv sync")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

app = FastAPI(title="Whisper Local API")
model: WhisperModel | None = None
model_config = {}

# 支持的模型
MODELS = {
    1: ("tiny", "Tiny (最快，准确率较低)"),
    2: ("base", "Base (较快，准确率一般)"),
    3: ("small", "Small (较快，准确率较好)"),
    4: ("medium", "Medium (推荐，平衡速度和准确率)"),
    5: ("large-v3-turbo", "Large-v3-turbo (快速且准确)"),
    6: ("distil-large-v3", "Distil-large-v3 (蒸馏版本，更快)"),
    7: ("large-v3", "Large-v3 (最准确，较慢)"),
}

# 支持的语言
LANGUAGES = {
    1: ("ja", "日语"),
    2: ("zh", "中文"),
    3: ("en", "英语"),
    4: ("ko", "韩语"),
    5: ("fr", "法语"),
    6: ("de", "德语"),
    7: ("es", "西班牙语"),
}


def get_choice(prompt: str, options: dict, default: int):
    """获取用户选择"""
    while True:
        try:
            choice = input(prompt).strip()
            if not choice:
                return options[default]
            num = int(choice)
            if num in options:
                return options[num]
            print(f"无效选择，请输入 1-{len(options)}")
        except ValueError:
            print("请输入数字")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            sys.exit(0)


def interactive_mode():
    """交互式模式选择配置"""
    print("\n" + "=" * 50)
    print("  Whisper 本地 API 服务器配置")
    print("=" * 50)

    print("\n选择模型：")
    for num, (model, desc) in MODELS.items():
        print(f"  [{num}] {desc}")

    print("\n选择语言：")
    for num, (code, name) in LANGUAGES.items():
        print(f"  [{num}] {name} ({code})")

    print("=" * 50)

    # 选择模型
    model_name, _ = get_choice(
        "请选择模型 (1-7，回车默认 4): ",
        MODELS,
        default=4
    )

    # 选择语言
    lang_code, _ = get_choice(
        "请选择默认语言 (1-7，回车默认 1): ",
        LANGUAGES,
        default=1
    )

    # 选择端口
    while True:
        port_input = input("请输入端口 (回车默认 8000): ").strip()
        if not port_input:
            port = 8000
            break
        try:
            port = int(port_input)
            if 1 <= port <= 65535:
                break
            print("端口范围 1-65535")
        except ValueError:
            print("请输入数字")

    print(f"\n配置：模型={model_name}, 语言={lang_code}, 端口={port}")
    print("正在加载模型（首次会自动下载）...")

    return model_name, lang_code, port


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "model": model_config.get("path"), "mode": "local-cpu"}


@app.post("/transcribe")
async def transcribe(request: Request, language: str = "ja"):
    """转写音频"""
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
        segments, info = model.transcribe(
            temp_path,
            language=language if language else None,
            beam_size=5,
            vad_filter=True,
        )

        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)

        # 返回结果
        results = []
        full_text = []
        for seg in segments:
            results.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            })
            full_text.append(seg.text)

        return JSONResponse({
            "text": "".join(full_text),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": results,
        })

    except Exception as e:
        log.exception("转写失败")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    p = argparse.ArgumentParser(description="Whisper 本地 API 服务器")
    p.add_argument(
        "--interactive",
        action="store_true",
        help="交互式选择配置"
    )
    p.add_argument(
        "--model",
        type=str,
        default="medium",
        help="模型名称"
    )
    p.add_argument(
        "--language",
        type=str,
        default="ja",
        help="默认语言"
    )
    p.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="监听地址"
    )
    p.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口"
    )

    args = p.parse_args()

    global model, model_config

    # 确定配置
    if args.interactive:
        model_name, language, port = interactive_mode()
        host = args.host
    else:
        model_name = args.model
        language = args.language
        port = args.port
        host = args.host

    # 加载模型
    log.info(f"加载模型: {model_name}")
    log.info(f"设备: CPU, 计算类型: int8")

    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=None,
    )

    model_config = {"path": model_name, "language": language}

    log.info("模型加载完成")
    log.info(f"启动 API 服务: http://{host}:{port}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
