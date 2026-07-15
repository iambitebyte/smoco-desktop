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
        """枚举 WASAPI 渲染端点（loopback 可采集的输出设备）。
        返回 [{index, name, sample_rate, channels, is_default}, ...]。"""
        if not _AVAILABLE:
            return []
        pa = pyaudio.PyAudio()
        try:
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            if not wasapi:
                return []
            default_out_index = int(wasapi["defaultOutputDevice"])
            # 先拿到默认渲染设备名
            try:
                default_out_info = pa.get_device_info_by_index(default_out_index)
                default_out_name = str(default_out_info["name"])
            except Exception:
                default_out_name = None

            out = []
            # 直接遍历 loopback 设备
            for lb in pa.get_loopback_device_info_generator():
                # loopback 名字格式：原名 [Loopback] 或原名 - Loopback
                lb_name = str(lb["name"])
                # 提取原始设备名（去掉 [Loopback] 或 - Loopback 后缀）
                if "[Loopback]" in lb_name:
                    original_name = lb_name.replace("[Loopback]", "").strip()
                elif " - Loopback" in lb_name or "- Loopback" in lb_name:
                    original_name = lb_name.split("Loopback")[0].strip().rstrip(" -")
                else:
                    original_name = lb_name

                out.append({
                    "index": int(lb["index"]),
                    "name": original_name,
                    "sample_rate": int(lb["defaultSampleRate"]),
                    "channels": int(lb["maxInputChannels"]),
                    "is_default": (default_out_name is not None and
                                   original_name == default_out_name),
                })
            return out
        finally:
            pa.terminate()

    def start(self) -> None:
        log.debug("WASAPILoopbackSource.start: 开始")
        self._pa = pyaudio.PyAudio()
        dev, dev_info = self._resolve_device()

        # 保存实际流参数（_callback 用）
        self._channels = int(dev_info.get("maxInputChannels") or 2)
        self._rate_in = int(dev_info["defaultSampleRate"])

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._rate_in,
                input=True,
                input_device_index=dev,
                frames_per_buffer=1024,
                stream_callback=self._callback,
            )
            self._stream.start_stream()
            log.info("WASAPI 流已启动")
        except Exception as e:  # noqa: BLE001
            raise SourceError(f"无法打开音频流: {e}") from e

    def _resolve_device(self) -> tuple[int, dict]:
        """解析要打开的设备，返回 (dev_index, dev_info)。
        子类覆盖此方法以切换 loopback / 麦克风输入。"""
        if self._device_index is not None:
            # 用户指定的 index（来自 list_devices，已经是 loopback index）
            dev = self._device_index
            log.debug(f"使用用户指定的设备 index: {dev}")
            return dev, self._pa.get_device_info_by_index(dev)

        # 没指定时，找默认渲染设备的 loopback 版本
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_info = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            default_out_name = str(default_out_info["name"])
        except Exception as e:
            raise SourceError(f"无法获取默认输出设备: {e}") from e

        for loopback in self._pa.get_loopback_device_info_generator():
            lb_name = str(loopback["name"])
            # 提取原始设备名（去掉 [Loopback] 或 - Loopback 后缀）
            if "[Loopback]" in lb_name:
                original_name = lb_name.replace("[Loopback]", "").strip()
            elif " - Loopback" in lb_name or "- Loopback" in lb_name:
                original_name = lb_name.split("Loopback")[0].strip().rstrip(" -")
            else:
                original_name = lb_name
            if original_name == default_out_name:
                return int(loopback["index"]), loopback
        raise SourceError(f"找不到默认设备的 loopback: {default_out_name}")

    def _callback(self, in_data, frame_count, time_info, status):  # noqa: ANN001
        if self._stop.is_set():
            return (b"", pyaudio.paComplete)
        # log.debug(f"callback: 收到 {len(in_data)} 字节, frame_count={frame_count}, status={status}")
        self._accum.extend(in_data)
        bpf = self._target.frame_bytes()
        try:
            arr = np.frombuffer(bytes(self._accum), dtype="<i2").astype(np.float32) / 32768.0
            if self._channels > 1:
                arr = arr.reshape(-1, self._channels)
            self._accum = bytearray()
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
        """读取一帧。只在显式停止且队列空时返回 None。"""
        if self._stop.is_set() and self._frames.empty():
            return None
        try:
            return self._frames.get(timeout=0.1)
        except _q.Empty:
            return None

    def stop(self) -> None:
        self._stop.set()
        stream, self._stream = self._stream, None
        pa, self._pa = self._pa, None
        try:
            if stream is not None:
                stream.stop_stream()
                stream.close()
        except Exception:  # noqa: BLE001
            log.exception("WASAPI stop_stream/close 失败")
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:  # noqa: BLE001
                    log.exception("WASAPI terminate 失败")


class MicInputSource(WASAPILoopbackSource):
    """Windows WASAPI 输入端点（麦克风）采集。

    继承 WASAPILoopbackSource 以复用流打开 / 规范化（resample→16k mono→30ms 帧）
    / 读取 / 停止逻辑，仅覆盖 list_devices()（枚举输入设备）与 _resolve_device()
    （默认设备走 defaultInputDevice）。打开方式同为 pa.open(input=True)。"""

    @staticmethod
    def list_devices() -> list[dict]:
        """枚举 WASAPI 输入端点（麦克风，排除 loopback）。
        返回 [{index, name, sample_rate, channels, is_default}, ...]。"""
        if not _AVAILABLE:
            return []
        pa = pyaudio.PyAudio()
        try:
            try:
                wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            except Exception:  # noqa: BLE001
                return []
            if not wasapi:
                return []
            wasapi_index = int(wasapi["index"])
            default_in_index = int(wasapi["defaultInputDevice"])

            out = []
            for i in range(int(pa.get_device_count())):
                info = pa.get_device_info_by_index(i)
                if int(info.get("hostApi", -1)) != wasapi_index:
                    continue
                if int(info.get("maxInputChannels", 0)) <= 0:
                    continue
                if info.get("isLoopbackDevice"):
                    continue
                out.append({
                    "index": int(info["index"]),
                    "name": str(info["name"]).strip(),
                    "sample_rate": int(info["defaultSampleRate"]),
                    "channels": int(info["maxInputChannels"]),
                    "is_default": int(info["index"]) == default_in_index,
                })
            return out
        finally:
            pa.terminate()

    def _resolve_device(self) -> tuple[int, dict]:
        if self._device_index is not None:
            dev = self._device_index
            log.debug(f"使用用户指定的麦克风 index: {dev}")
            return dev, self._pa.get_device_info_by_index(dev)

        # 没指定时，用默认输入设备（麦克风）
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_in_index = int(wasapi_info["defaultInputDevice"])
            dev_info = self._pa.get_device_info_by_index(default_in_index)
            return default_in_index, dev_info
        except Exception as e:
            raise SourceError(f"无法获取默认输入设备: {e}") from e
