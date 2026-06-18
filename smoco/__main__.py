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
