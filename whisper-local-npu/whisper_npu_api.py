#!/usr/bin/env python3
"""
Whisper 本地 NPU API 服务器（openvino-genai, device=NPU）。

对外契约与 whisper-local/whisper_local_api.py 一致：
  GET  /health
  POST /transcribe?language=ja   body = 原始 PCM（16k mono S16LE）

重依赖（openvino / openvino-genai / fastapi / uvicorn）在 main() 里懒导入，
故 --help 等基础校验不依赖它们。
"""
import argparse
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

LANGUAGES = {
    1: ("ja", "日语"),
    2: ("zh", "中文"),
    3: ("en", "英语"),
    4: ("ko", "韩语"),
    5: ("fr", "法语"),
    6: ("de", "德语"),
    7: ("es", "西班牙语"),
}


def _get_choice(prompt: str, options: dict, default: int):
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


def _interactive():
    print("\n" + "=" * 50)
    print("  Whisper 本地 NPU API 服务器配置")
    print("=" * 50)
    print("\n选择默认语言：")
    for num, (code, name) in LANGUAGES.items():
        print(f"  [{num}] {name} ({code})")
    print("=" * 50)
    lang_code, _ = _get_choice("请选择默认语言 (1-7，回车默认 1): ", LANGUAGES, default=1)
    model_dir = input("请输入 OpenVINO IR 模型目录路径: ").strip()
    while not model_dir:
        print("模型目录不能为空")
        model_dir = input("请输入 OpenVINO IR 模型目录路径: ").strip()
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
    return model_dir, lang_code, port


def create_app(pipe, model_dir: str, device: str):
    """构建 FastAPI app。pipe 是已加载的 openvino_genai.Whisper（或测试用假对象）。"""
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import numpy as np

    app = FastAPI(title="Whisper Local NPU API")

    @app.get("/health")
    async def health():
        return {"status": "ok", "model": model_dir, "device": device, "mode": "local-npu"}

    @app.post("/transcribe")
    async def transcribe(request: Request, language: str = "ja"):
        if pipe is None:
            raise HTTPException(status_code=503, detail="模型未加载")
        try:
            audio_data = await request.body()
            if not audio_data:
                return JSONResponse({
                    "text": "", "segments": [], "language": language, "duration": 0.0,
                })
            samples = np.frombuffer(audio_data, dtype="<i2").astype(np.float32) / 32768.0
            # 转写是同步重活，甩线程不卡事件循环
            result = await asyncio.to_thread(pipe.transcribe, samples, language=language)
            segments = []
            for ch in getattr(result, "chunks", []) or []:
                segments.append({
                    "start": float(getattr(ch, "start", 0.0)),
                    "end": float(getattr(ch, "end", 0.0)),
                    "text": getattr(ch, "text", ""),
                })
            duration = float(len(samples) / 16000.0)
            return JSONResponse({
                "text": getattr(result, "text", ""),
                "segments": segments,
                "language": language,
                "duration": duration,
            })
        except Exception as e:
            log.exception("转写失败")
            raise HTTPException(status_code=500, detail=str(e))

    return app


def main():
    p = argparse.ArgumentParser(description="Whisper 本地 NPU API 服务器（openvino-genai）")
    p.add_argument("--interactive", action="store_true", help="交互式选择配置")
    p.add_argument("--model-dir", type=str, help="OpenVINO IR 模型目录路径")
    p.add_argument("--language", type=str, default="ja", help="默认语言代码 (ja/zh/en/...)")
    p.add_argument("--device", type=str, default="NPU", help="OpenVINO 设备 (NPU/GPU/CPU，默认 NPU)")
    p.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    p.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    args = p.parse_args()

    if args.interactive:
        model_dir, language, port = _interactive()
        host, device = args.host, args.device
    else:
        if not args.model_dir:
            p.error("--model-dir 必填（或使用 --interactive）")
        model_dir, language, port = args.model_dir, args.language, args.port
        host, device = args.host, args.device

    # 懒导入重依赖
    try:
        from openvino import Core
    except ImportError:
        print("缺少依赖：请在 whisper-local-npu/ 下 `uv sync`（须 openvino、openvino-genai）")
        sys.exit(1)

    devices = Core().available_devices
    if device not in devices:
        print(f"找不到设备 '{device}'。当前可见设备：{devices}")
        sys.exit(1)

    try:
        import openvino_genai
    except ImportError:
        print("缺少依赖：openvino-genai 未安装，请 `uv sync`")
        sys.exit(1)

    log.info(f"加载模型: {model_dir} (device={device})")
    log.info("首次运行会为 NPU 编译模型，可能耗时较长；可设 OV_CACHE_DIR 加速后续启动")
    pipe = openvino_genai.Whisper(model_dir, device=device)
    log.info("模型加载完成")

    import uvicorn
    app = create_app(pipe, model_dir, device)
    log.info(f"启动 API 服务: http://{host}:{port}  (GET /health, POST /transcribe)")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
