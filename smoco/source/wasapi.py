from __future__ import annotations
import logging
import threading
import queue as _q
import numpy as np
from ..audio import AudioFormat, to_mono, resample, encode_s16le
from .base import SourceError

log = logging.getLogger("smoco.source.wasapi")

try:
    import pyaudiowpatch as pyaudio
    _AVAILABLE = True
except Exception:  # noqa: BLE001
    pyaudio = None
    _AVAILABLE = False


class WASAPILoopbackSource:
    """Windows WASAPI loopback 采集，规范化为 16k mono S16LE 30ms 帧。
    PyAudioWPatch 以 as_loopback=True 打开默认渲染端点。"""

    def __init__(self, target: AudioFormat | None = None,
                 device_index: int | None = None):
        if not _AVAILABLE:
            raise SourceError("pyaudiowpatch 不可用（非 Windows 或未安装）")
        self._target = target or AudioFormat()
        self._device_index = device_index
        self._pa: pyaudio.PyAudio | None = None
        self._stream = None
        self._frames: _q.Queue[bytes] = _q.Queue(maxsize=64)
        self._accum = bytearray()
        self._leftover = bytearray()      # 跨 callback 的 sub-frame 尾巴（已编码 S16LE）
        self._stop = threading.Event()
        # 流参数，在 start() 中据实际打开的流赋值
        self._channels = 2
        self._rate_in = 48000

    @property
    def audio_format(self) -> AudioFormat:
        return self._target

    @staticmethod
    def list_devices() -> list[dict]:
        if not _AVAILABLE:
            return []
        pa = pyaudio.PyAudio()
        try:
            return [pa.get_device_info_by_index(i)
                    for i in range(pa.get_device_count())
                    if pa.get_device_info_by_index(i).get("maxInputChannels", 0) > 0]
        finally:
            pa.terminate()

    def start(self) -> None:
        self._pa = pyaudio.PyAudio()
        try:
            info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default = self._pa.get_device_info_by_index(info["defaultOutputDevice"])
            dev = self._device_index if self._device_index is not None else default["index"]
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"找不到 WASAPI 默认输出设备: {e}") from e

        # 据默认输出设备保存实际流参数（_callback 用）
        self._channels = int(default.get("maxInputChannels") or 2)
        self._rate_in = int(default["defaultSampleRate"])

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._rate_in,
                input=True,
                input_device_index=dev,
                as_loopback=True,
                frames_per_buffer=1024,
                stream_callback=self._callback,
            )
            self._stream.start_stream()
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"无法打开 loopback 流: {e}") from e

    def _callback(self, in_data, frame_count, time_info, status):  # noqa: ANN001
        if self._stop.is_set():
            return (b"", pyaudio.paComplete)
        self._accum.extend(in_data)
        bpf = self._target.frame_bytes()
        try:
            arr = np.frombuffer(bytes(self._accum), dtype="<i2").astype(np.float32) / 32768.0
            self._accum = bytearray()
            if self._channels > 1:
                arr = arr.reshape(-1, self._channels)
            mono = to_mono(arr)
            res = resample(mono, self._rate_in, self._target.sample_rate)
            encoded = encode_s16le(res)
            # 把上一轮的 sub-frame 尾巴拼到本轮输出前，整体切成整帧，余数留到下轮
            buf = bytes(self._leftover) + encoded
            self._leftover = bytearray()
            n = (len(buf) // bpf) * bpf
            for i in range(0, n, bpf):
                frame = buf[i:i + bpf]
                try:
                    self._frames.put_nowait(frame)
                except _q.Full:
                    self._frames.get_nowait()        # 丢最旧
                    self._frames.put_nowait(frame)
            self._leftover = bytearray(buf[n:])
        except Exception:  # noqa: BLE001
            log.exception("WASAPI 帧转换失败")
        return (b"", pyaudio.paContinue)

    def read_frame(self) -> bytes | None:
        if self._stop.is_set() and self._frames.empty():
            return None
        try:
            return self._frames.get(timeout=0.1)
        except _q.Empty:
            return None

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        finally:
            if self._pa is not None:
                self._pa.terminate()
                self._pa = None
