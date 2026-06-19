from __future__ import annotations
import argparse
import asyncio
import logging
import sys
from .audio import AudioFormat
from .chunker import Chunker, WebRtcVad
from .config import Config
from .pipeline import Pipeline
from .source.file import FileSource
from .source.metering import MeteringSource
from .transcriber.stub import StubTranscriber


def meter_bar(rms: float, width: int = 24) -> str:
    """把 [0,1] 电平渲染成条：[████████░░░░░░░░░░░░░░░░]"""
    level = max(0.0, min(1.0, rms))
    filled = int(round(level * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


async def _render_meter(source) -> None:
    """持续刷新音量条，直到被取消。"""
    while True:
        rms = source.latest_rms
        sys.stdout.write("\r" + meter_bar(rms) + f" rms={rms:.3f}  ")
        sys.stdout.flush()
        await asyncio.sleep(0.05)


async def _run_with_meter(pipe, source, meter: bool) -> None:
    """meter=False 时直接跑管线；True 时并发跑渲染，管线结束后收尾换行。"""
    if not meter:
        await pipe.run()
        return
    task = asyncio.create_task(_render_meter(source))
    try:
        await pipe.run()
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        sys.stdout.write("\n")
        sys.stdout.flush()


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


def _resolve_device(args, list_devices_fn, input_fn=None) -> int | None:
    """决定 --wasapi 用哪个设备 index。失败（无设备/重试用尽）返回 None。"""
    if input_fn is None:
        import builtins
        input_fn = builtins.input
    if args.device is not None:
        return args.device
    devices = list_devices_fn()
    if not devices:
        print("找不到 WASAPI 渲染设备（用 list-devices 查看详情）")
        return None
    return _prompt_for_device(devices, input_fn)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smoco",
                                description="采集系统声音 → VAD 切块 → 转写")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行管线")
    p_run.add_argument("--file", help="用文件源（跨平台，开发/测试用）")
    p_run.add_argument("--wasapi", action="store_true",
                       help="用 Windows WASAPI loopback 源")
    p_run.add_argument("--stub-out", help="StubTranscriber 落 wav 目录")
    p_run.add_argument("--device", type=int, help="直接指定 WASAPI 设备 index（跳过交互选择）")
    p_run.add_argument("--meter", action="store_true", help="显示实时音量条（确认采集通路）")
    p_run.add_argument("--debug", action="store_true", help="启用调试日志")
    p_run.add_argument("--whisper-url", help="Whisper API 服务地址（如 http://server:8000）")
    p_run.add_argument("--whisper-lang", default="ja", help="Whisper 语言代码（ja=日语, zh=中文）")

    sub.add_parser("list-devices", help="列出 WASAPI loopback 设备（Windows）")
    return p


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
    if args.meter:
        source = MeteringSource(source)
        logging.getLogger("smoco").setLevel(logging.WARNING)
    vad = WebRtcVad(aggressiveness=cfg.vad_aggressiveness, sample_rate=fmt.sample_rate)
    chunker = Chunker(vad, fmt, silence_ms=cfg.silence_ms,
                      max_chunk_ms=cfg.max_chunk_ms, min_chunk_ms=cfg.min_chunk_ms,
                      pad_ms=cfg.pad_ms)

    # 选择转写器
    if args.whisper_url:
        from .transcriber.whisper_remote import WhisperRemoteTranscriber
        transcriber = WhisperRemoteTranscriber(
            api_url=args.whisper_url,
            language=args.whisper_lang,
        )
    else:
        transcriber = StubTranscriber(out_dir=args.stub_out)

    pipe = Pipeline(source, chunker, transcriber, cfg)
    try:
        asyncio.run(_run_with_meter(pipe, source, args.meter))
    except KeyboardInterrupt:
        logging.getLogger("smoco").info("已中断")
        return 0
    if pipe.error is not None:
        logging.getLogger("smoco").error("采集源错误: %s", pipe.error)
        return 1
    return 0


def cmd_list_devices() -> int:
    from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
    if not _AVAILABLE:
        print("WASAPI 不可用（需 Windows + pyaudiowpatch）")
        return 1
    for d in WASAPILoopbackSource.list_devices():
        print(d)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    # 根据 --debug 设置日志级别
    level = logging.DEBUG if getattr(args, 'debug', False) else logging.INFO
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "list-devices":
        return cmd_list_devices()
    return 1


if __name__ == "__main__":
    sys.exit(main())
