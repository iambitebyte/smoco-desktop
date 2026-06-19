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
from .transcriber.stub import StubTranscriber


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


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smoco",
                                description="采集系统声音 → VAD 切块 → 转写")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行管线")
    p_run.add_argument("--file", help="用文件源（跨平台，开发/测试用）")
    p_run.add_argument("--wasapi", action="store_true",
                       help="用 Windows WASAPI loopback 源")
    p_run.add_argument("--stub-out", help="StubTranscriber 落 wav 目录")

    sub.add_parser("list-devices", help="列出 WASAPI loopback 设备（Windows）")
    return p


def _make_source(args, fmt: AudioFormat):
    if args.file:
        return FileSource(args.file, target=fmt)
    if args.wasapi:
        from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
        if not _AVAILABLE:
            raise SystemExit("WASAPI 源不可用（需 Windows + pyaudiowpatch）")
        return WASAPILoopbackSource(target=fmt)
    raise SystemExit("请指定 --file 或 --wasapi")


def cmd_run(args) -> int:
    fmt = AudioFormat()
    cfg = Config()
    source = _make_source(args, fmt)
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


def cmd_list_devices() -> int:
    from .source.wasapi import WASAPILoopbackSource, _AVAILABLE
    if not _AVAILABLE:
        print("WASAPI 不可用（需 Windows + pyaudiowpatch）")
        return 1
    for d in WASAPILoopbackSource.list_devices():
        print(d)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "list-devices":
        return cmd_list_devices()
    return 1


if __name__ == "__main__":
    sys.exit(main())
