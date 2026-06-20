"""本地 Whisper 转写器（使用 faster-whisper）"""

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..audio import AudioChunk

log = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    log.warning("faster-whisper 未安装，本地转写不可用")


class WhisperLocalTranscriber:
    """本地 Whisper 转写器（使用 faster-whisper，CPU 模式）"""

    sample_rate = 16000

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
        if WhisperModel is None:
            raise RuntimeError("faster-whisper 未安装，请: pip install faster-whisper")

        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: WhisperModel | None = None
        self._loaded = False

    def _ensure_model(self):
        """延迟加载模型"""
        if not self._loaded:
            log.info(f"加载 Whisper 模型: {self.model_name} ({self.device}, {self.compute_type})")
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._loaded = True

    async def transcribe(self, chunk: "AudioChunk"):
        """转写音频片段

        Args:
            chunk: AudioChunk 对象

        Returns:
            TranscriptResult
        """
        from .base import TranscriptResult

        # 延迟加载模型
        self._ensure_model()

        try:
            # 保存为临时 WAV 文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                import wave
                with wave.open(f, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(chunk.sample_rate)
                    wav.writeframes(chunk.pcm)
                temp_path = f.name

            # 转写
            segments, info = self._model.transcribe(
                temp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )

            # 收集结果
            results = []
            full_text = []
            for seg in segments:
                results.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                })
                full_text.append(seg.text)

            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

            return TranscriptResult(
                chunk_id=chunk.id,
                text="".join(full_text),
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                is_final=True,
                error=None,
            )

        except Exception as e:
            log.exception("本地转写失败")
            return TranscriptResult(
                chunk_id=chunk.id,
                text="",
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                is_final=True,
                error=str(e),
            )

    async def close(self):
        """关闭转写器"""
        # faster-whisper 不需要显式关闭
        self._model = None
        self._loaded = False
