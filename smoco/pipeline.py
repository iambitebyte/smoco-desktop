from __future__ import annotations
import asyncio
import logging
import threading
from .audio import AudioChunk
from .chunker import Chunker
from .config import Config
from .source.base import AudioSource, SourceError
from .transcriber.base import Transcriber

log = logging.getLogger("smoco.pipeline")


class Pipeline:
    """source(同步,线程) -> chunker(同线程) -> asyncio.Queue -> transcriber(协程)。
    队列满时丢最旧 chunk + 告警（实时音频积压无意义）。"""

    def __init__(self, source: AudioSource, chunker: Chunker,
                 transcriber: Transcriber, config: Config):
        self._source = source
        self._chunker = chunker
        self._transcriber = transcriber
        self._cfg = config
        self._error: Exception | None = None

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=self._cfg.chunk_queue_size)
        n_workers = self._cfg.transcriber_concurrency
        capture = threading.Thread(target=self._capture_loop,
                                   args=(loop, q, n_workers), daemon=True)
        capture.start()
        workers = [asyncio.create_task(self._transcribe_loop(q))
                   for _ in range(n_workers)]
        try:
            await loop.run_in_executor(None, capture.join)
        finally:
            # 令采集线程退出阻塞读（对真机 WASAPI 关键）：stop() 后 read_frame 尽快返回 None
            try:
                self._source.stop()
            except Exception:  # noqa: BLE001
                log.exception("shutdown: source.stop() 失败")
            for _ in range(n_workers):
                await q.put(None)            # 各 worker 一个哨兵
            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers, return_exceptions=True),
                    timeout=self._cfg.shutdown_timeout)
            except asyncio.TimeoutError:
                log.warning("workers 未在 shutdown_timeout=%.1fs 内结束，强制取消",
                            self._cfg.shutdown_timeout)
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
            try:
                await self._transcriber.close()
            except Exception:  # noqa: BLE001
                log.exception("shutdown: transcriber.close() 失败")
            capture.join(timeout=self._cfg.shutdown_timeout)

    def _capture_loop(self, loop, q: asyncio.Queue, n_workers: int) -> None:
        self._source.start()
        try:
            while True:
                frame = self._source.read_frame()
                if frame is None:
                    # 没有帧（可能是静音期间），继续监听
                    # 但如果 source 已停止，则退出
                    if hasattr(self._source, '_stop') and self._source._stop.is_set():
                        break
                    continue
                for chunk in self._chunker.feed(frame):
                    if not chunk.pcm:        # 被 min_chunk_ms 丢弃
                        continue
                    self._put_threadsafe(q, chunk, loop)
            for chunk in self._chunker.flush():
                if chunk.pcm:
                    self._put_threadsafe(q, chunk, loop)
        except SourceError as e:
            log.error("采集错误: %s", e)
            self._error = e
        except Exception as e:  # noqa: BLE001
            log.exception("采集线程意外异常")
            self._error = e
        finally:
            try:
                self._source.stop()
            except Exception:  # noqa: BLE001
                log.exception("stop() 失败")

    def _put_threadsafe(self, q: asyncio.Queue, chunk: AudioChunk, loop) -> None:
        def _put():
            if q.full() and self._cfg.drop_policy == "drop_oldest":
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                log.warning("chunkQ 满，丢弃最旧 chunk")
                q.put_nowait(chunk)
            elif self._cfg.drop_policy == "drop_newest" and q.full():
                log.warning("chunkQ 满，丢弃最新 chunk")
            else:
                try:
                    q.put_nowait(chunk)
                except asyncio.QueueFull:
                    log.warning("chunkQ 满，丢弃以避免死锁")
        loop.call_soon_threadsafe(_put)

    async def _transcribe_loop(self, q: asyncio.Queue) -> None:
        while True:
            item = await q.get()
            if item is None:                 # 哨兵
                return
            chunk: AudioChunk = item
            try:
                result = await self._transcriber.transcribe(chunk)
            except Exception as e:  # noqa: BLE001
                log.warning("转写异常 (chunk=%s): %s", chunk.id, e)
                continue
            if result.get("error"):
                log.warning("转写失败 (chunk=%s): %s", chunk.id, result["error"])
            else:
                log.info("[%.2f-%.2f] %s", result["start_time"],
                         result["end_time"], result["text"])

    @property
    def error(self) -> Exception | None:
        return self._error
