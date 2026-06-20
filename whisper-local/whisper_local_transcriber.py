#!/usr/bin/env python3
"""
本地 Whisper 转写器（使用 faster-whisper）

在 Windows 上运行，支持 CPU 模式。

依赖：
    uv sync

运行：
    uv run python whisper_local_transcriber.py
    或直接双击 start.bat
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

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

# 支持的模型列表
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


class LocalWhisperTranscriber:
    """本地 Whisper 转写器（faster-whisper）"""

    def __init__(
        self,
        model_name: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "ja",
    ):
        """
        Args:
            model_name: 模型名称（medium, large-v3-turbo, distil-large-v3 等）
            device: 设备（cpu 或 cuda）
            compute_type: 计算类型（int8, float16, float32）
            language: 默认语言（ja=日语, zh=中文, en=英语）
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model: WhisperModel | None = None

    def load(self):
        """加载模型"""
        log.info(f"加载模型: {self.model_name}")
        log.info(f"设备: {self.device}, 计算类型: {self.compute_type}")

        self.model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
            download_root=None,  # 使用默认缓存路径
        )
        log.info("模型加载完成")

    def transcribe_file(self, audio_path: str, language: str = None):
        """转写音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言代码（None=自动检测）

        Returns:
            转写结果 {"text": str, "segments": [...], "language": str}
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        lang = language or self.language

        segments, info = self.model.transcribe(
            audio_path,
            language=lang if lang else None,
            beam_size=5,
            vad_filter=True,
        )

        results = []
        full_text = []
        for seg in segments:
            results.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            })
            full_text.append(seg.text)

        return {
            "text": "".join(full_text),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": results,
        }


def print_menu():
    """显示选择菜单"""
    print("\n" + "=" * 50)
    print("  Whisper 本地转写器")
    print("=" * 50)

    print("\n选择模型：")
    for num, (model, desc) in MODELS.items():
        print(f"  [{num}] {desc}")

    print("\n选择语言：")
    for num, (code, name) in LANGUAGES.items():
        print(f"  [{num}] {name} ({code})")

    print("=" * 50)


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


def main_interactive():
    """交互式模式"""
    print_menu()

    # 选择模型
    model_name, _ = get_choice(
        "请选择模型 (1-7，回车默认 4): ",
        MODELS,
        default=4
    )

    # 选择语言
    lang_code, _ = get_choice(
        "请选择语言 (1-7，回车默认 1): ",
        LANGUAGES,
        default=1
    )

    print(f"\n配置：模型={model_name}, 语言={lang_code}")
    print("正在加载模型（首次会自动下载）...")

    # 创建并加载转写器
    transcriber = LocalWhisperTranscriber(
        model_name=model_name,
        device="cpu",
        compute_type="int8",
        language=lang_code,
    )

    transcriber.load()

    print("\n模型已就绪！")
    print("\n现在你可以：")
    print("  1. 转写音频文件")
    print("  2. 退出")

    while True:
        choice = input("\n请选择 (1-2): ").strip()
        if choice == "1":
            audio_path = input("请输入音频文件路径: ").strip()
            path = Path(audio_path).expanduser()
            if not path.exists():
                print(f"文件不存在: {audio_path}")
                continue

            print(f"正在转写: {path}")
            result = transcriber.transcribe_file(str(path))

            print(f"\n检测到语言: {result['language']} (概率: {result['language_probability']:.2f})")
            print(f"音频时长: {result['duration']:.2f} 秒")
            print("-" * 40)

            for seg in result["segments"]:
                print(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")
        elif choice == "2":
            print("再见！")
            break
        else:
            print("无效选择")


def main_cmdline(args):
    """命令行模式"""
    transcriber = LocalWhisperTranscriber(
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
    )

    transcriber.load()

    if args.audio_file:
        audio_path = Path(args.audio_file).expanduser()
        if not audio_path.exists():
            log.error(f"音频文件不存在: {audio_path}")
            sys.exit(1)

        log.info(f"转写音频: {audio_path}")
        result = transcriber.transcribe_file(str(audio_path))

        log.info(f"检测到语言: {result['language']} (概率: {result['language_probability']:.2f})")
        log.info(f"音频时长: {result['duration']:.2f} 秒")
        log.info("-" * 40)

        for seg in result["segments"]:
            log.info(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")
    else:
        # 没有音频文件时，进入交互模式
        main_interactive()


def main():
    p = argparse.ArgumentParser(description="本地 Whisper 转写器")
    p.add_argument(
        "--model",
        type=str,
        default="medium",
        help="模型名称（默认: medium）"
    )
    p.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="计算设备（默认: cpu）"
    )
    p.add_argument(
        "--compute-type",
        type=str,
        default="int8",
        choices=["int8", "float16", "float32"],
        help="计算类型（默认: int8，CPU 推荐）"
    )
    p.add_argument(
        "--language",
        type=str,
        default="ja",
        help="语言代码（ja=日语, zh=中文, en=英语）"
    )
    p.add_argument(
        "--audio-file",
        type=str,
        help="要转写的音频文件（命令行模式）"
    )

    args = p.parse_args()

    # 如果有音频文件参数，用命令行模式
    # 否则，用交互式模式
    if args.audio_file:
        main_cmdline(args)
    else:
        main_interactive()


if __name__ == "__main__":
    main()
