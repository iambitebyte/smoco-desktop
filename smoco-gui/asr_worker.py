"""
ASR 转录 Worker - 异步 HTTP 请求
"""

import sys
import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication

# 关闭 requests DEBUG 日志
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# 添加父目录到 Python 路径
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))

from asr_chunker import AudioChunker
from asr_logger import get_asr_logger


class ASRWorker(QObject):
    """ASR 转录 Worker - 线程池处理 HTTP 请求"""

    transcript_ready = pyqtSignal(str, float, int)  # 信号：新转录文本 + 开始时间 + entry_id
    error_occurred = pyqtSignal(str)   # 信号：错误信息

    def __init__(self, api_url: str, language: str = "ja",
                 silence_ms: int = 600, max_chunk_ms: int = 15000,
                 min_chunk_ms: int = 500, pad_ms: int = 100):
        super().__init__()
        self.api_url = api_url.rstrip("/")
        self.language = language
        self._running = False
        # HTTP 线程池 - 并发处理多个请求
        self._executor = ThreadPoolExecutor(max_workers=2)
        # VAD 分块器
        self._chunker = AudioChunker(
            sample_rate=16000,
            frame_ms=30,
            silence_ms=silence_ms,
            max_chunk_ms=max_chunk_ms,
            min_chunk_ms=min_chunk_ms,
            pad_ms=pad_ms
        )

    def start(self):
        """启动转录"""
        self._running = True

    def stop(self):
        """停止转录"""
        self._running = False
        # 刷新剩余音频
        for chunk in self._chunker.flush():
            if chunk:
                self._submit_async(chunk)
        # 等待所有请求完成
        self._executor.shutdown(wait=False)

    def submit_audio(self, frame: bytes):
        """提交音频帧（非阻塞）"""
        if not self._running:
            return

        # 分块器返回完成的块
        for chunk_data in self._chunker.feed(frame):
            if chunk_data:
                self._submit_async(chunk_data)

    def _submit_async(self, chunk_data: tuple[bytes, float]):
        """异步提交 HTTP 请求"""
        self._executor.submit(self._transcribe, chunk_data)

    def _transcribe(self, chunk_data: tuple[bytes, float]):
        """发送音频进行转录（在线程池中运行）"""
        audio_data, start_time = chunk_data
        if not audio_data:
            return

        chunk_size = len(audio_data)
        request_start = time.time()

        try:
            url = f"{self.api_url}/transcribe"
            params = {"language": self.language}
            headers = {
                "Content-Type": "audio/raw",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            print(f"[ASR] POST {url}")
            print(f"[ASR] Params: {params}")
            print(f"[ASR] Headers: {headers}")
            print(f"[ASR] Audio size: {len(audio_data)} bytes")

            response = requests.post(
                url,
                params=params,
                data=audio_data,
                headers=headers,
                timeout=10.0
            )

            print(f"[ASR] Response: {response.status_code}")

            processing_time = time.time() - request_start

            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()
                if text:
                    # 记录日志并获取 entry_id
                    entry_id = get_asr_logger().log_request(
                        chunk_size=chunk_size,
                        api_url=self.api_url,
                        language=self.language,
                        processing_time=processing_time,
                        response_text=text
                    )
                    self.transcript_ready.emit(text, start_time, entry_id)
            else:
                self.error_occurred.emit(f"API 错误: {response.status_code}")

        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"请求失败: {e}")
        except Exception as e:
            self.error_occurred.emit(f"转录异常: {e}")


class ASRController:
    """ASR 控制器"""

    def __init__(self):
        self._thread: QThread | None = None
        self._worker: ASRWorker | None = None
        self._api_url = ""
        self._language = "ja"
        # VAD 参数
        self._vad_params = {
            "silence_ms": 600,
            "max_chunk_ms": 15000,
            "min_chunk_ms": 500,
            "pad_ms": 100,
        }

    def set_config(self, api_url: str, language: str = "ja"):
        """设置配置"""
        self._api_url = api_url
        self._language = language

    def set_vad_params(self, silence_ms: int = 600, max_chunk_ms: int = 15000,
                      min_chunk_ms: int = 500, pad_ms: int = 100):
        """设置 VAD 参数"""
        self._vad_params = {
            "silence_ms": silence_ms,
            "max_chunk_ms": max_chunk_ms,
            "min_chunk_ms": min_chunk_ms,
            "pad_ms": pad_ms,
        }

    def start(self, transcript_callback, error_callback):
        """启动转录"""
        self.stop()

        # 开始日志会话
        get_asr_logger().start_session()

        self._thread = QThread()
        self._worker = ASRWorker(self._api_url, self._language, **self._vad_params)
        self._worker.moveToThread(self._thread)

        self._worker.transcript_ready.connect(transcript_callback)
        self._worker.error_occurred.connect(error_callback)
        self._thread.started.connect(self._worker.start)

        self._thread.start()

    def stop(self):
        """停止转录"""
        if self._worker:
            self._worker.stop()
            self._worker = None

        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        # 结束日志会话
        get_asr_logger().end_session()

    def submit_audio(self, frame: bytes):
        """提交音频帧"""
        if self._worker:
            self._worker.submit_audio(frame)
