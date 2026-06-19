"""远程 Whisper 转写器（通过 HTTP API）"""

import logging
from typing import Any
import aiohttp
import numpy as np

from .base import Transcriber, TranscriptResult

log = logging.getLogger(__name__)


class WhisperRemoteTranscriber(Transcriber):
    """通过 HTTP API 调用远程 Whisper 模型"""

    sample_rate = 16000  # Whisper 固定采样率

    def __init__(
        self,
        api_url: str = "http://your-server:8000",
        language: str = "ja",
        timeout: float = 30.0,
    ):
        """
        Args:
            api_url: Whisper API 服务地址
            language: 语言代码（ja=日语, zh=中文, en=英语）
            timeout: 请求超时（秒）
        """
        self.api_url = api_url.rstrip("/")
        self.language = language
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def transcribe(self, chunk) -> TranscriptResult:
        """转写音频片段

        Args:
            chunk: AudioChunk 对象

        Returns:
            TranscriptResult
        """
        await self._ensure_session()

        try:
            # chunk.pcm 是 S16LE bytes，直接发送
            url = f"{self.api_url}/transcribe"
            params = {"language": self.language}

            async with self._session.post(
                url,
                params=params,
                data=chunk.pcm,
                headers={"Content-Type": "audio/raw"},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    log.error(f"API 错误: {resp.status} - {error_text}")
                    return TranscriptResult(
                        chunk_id=chunk.id,
                        text="",
                        start_time=chunk.start_time,
                        end_time=chunk.end_time,
                        is_final=True,
                        error=f"API 错误: {resp.status}",
                    )

                result = await resp.json()
                return TranscriptResult(
                    chunk_id=chunk.id,
                    text=result.get("text", ""),
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    is_final=True,
                    error=None,
                )

        except aiohttp.ClientError as e:
            log.error(f"请求失败: {e}")
            return TranscriptResult(
                chunk_id=chunk.id,
                text="",
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                is_final=True,
                error=f"请求失败: {e}",
            )
        except Exception as e:
            log.exception("转写异常")
            return TranscriptResult(
                chunk_id=chunk.id,
                text="",
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                is_final=True,
                error=str(e),
            )

    async def close(self):
        """关闭连接"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
