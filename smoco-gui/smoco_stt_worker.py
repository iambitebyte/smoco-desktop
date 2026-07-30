"""
Smoco 云端流式 STT API 接入（基于 Socket.IO）。

仿 asr_worker.py 的 ASRWorker/ASRController 双层结构，但内部是 socket.io 长连接
（service_type=local 走服务端 whisper-online，逐帧近实时推送）。

协议要点（2026-07-17 已源码+实测验证，见记忆 smoco-stt-api-verification）：
- 主机 https://dx-smoco-dev.sony.com.cn:443，Sony 内部 CA → 关 SSL 校验
- namespace=/speech_service, path=/api/socket.io, header Authorization: Bearer <token>
- 鉴权走 web 登录：POST /web/do_login(form email/password) → GET /web/api_info → ACCESS_TOKEN
- join/start_ws/process_ws/stop_ws 全部用 room_name（不是 sid/current_sid）
- process_ws 必须带 {room_name, pcm, sample_rate, channel_num, data_type}，pcm=int16 LE bytes
- 服务端 emit recognizing_text_live(中间)/recognized_text_live(最终)/recognize_status_live
"""

import sys
import time
import uuid
import threading
import logging
from pathlib import Path

import requests
import socketio

# 关闭 requests DEBUG 日志
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from asr_quality import is_low_energy
from asr_logger import get_asr_logger
from gui_logger import get_gui_logger
from PyQt6.QtCore import QObject, pyqtSignal

logger = get_gui_logger(__name__)

NAMESPACE = "/speech_service"
SIO_PATH = "/api/socket.io"
# GUI 短码 -> API 全称（服务端再转 en-us/zh-cn/ja-jp）
LANG_MAP = {"zh": "chinese", "ja": "japanese", "en": "english"}
# 反向：短码或全称 -> 服务端 recognized_text_live 里 language 字段用的短码（en/zh/ja）
_TO_SHORT = {"chinese": "zh", "japanese": "ja", "english": "en",
             "zh": "zh", "ja": "ja", "en": "en"}


def _srt_start_seconds(ts) -> float | None:
    """解析服务端 SRT timestamp "HH:MM:SS,mmm --> HH:MM:SS,mmm" 的起始秒数（相对会话开始）。"""
    if not ts or not isinstance(ts, str) or "-->" not in ts:
        return None
    start = ts.split("-->")[0].strip()
    try:
        if "," in start:
            hms, ms = start.rsplit(",", 1)
        else:
            hms, ms = start, "0"
        h, m, s = hms.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    except Exception:
        return None


class SmocoAuthError(Exception):
    pass


class SmocoAuth:
    """web 登录流程换取 access_token：do_login -> api_info。线程安全、带缓存。"""

    def __init__(self, host: str, email: str, password: str, verify_ssl: bool = True):
        self.host = host.rstrip("/")
        self.email = email
        self.password = password
        self.verify_ssl = verify_ssl
        if not verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings()
            except Exception:
                pass
        self._token = None
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            if self._token:
                return self._token
            return self._refresh_locked()

    def invalidate(self):
        with self._lock:
            self._token = None

    def _refresh_locked(self) -> str:
        """do_login + api_info 拿 token（持有锁时调用）。"""
        s = requests.Session()
        s.verify = self.verify_ssl
        try:
            r = s.post(
                f"{self.host}/web/do_login",
                data={"email": self.email, "password": self.password},
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=10,
            )
            if r.status_code != 200:
                raise SmocoAuthError(f"登录失败 HTTP {r.status_code}: {r.text[:120]}")
            info_r = s.get(f"{self.host}/web/api_info", timeout=10)
            if info_r.status_code != 200:
                raise SmocoAuthError(f"取 api_info 失败 HTTP {info_r.status_code}")
            info = info_r.json().get("api_info") or {}
            token = info.get("ACCESS_TOKEN")
            if not token:
                raise SmocoAuthError("api_info 里没有 ACCESS_TOKEN")
            self._token = token
            logger.info("smoco 登录成功，已拿到 access_token")
            return token
        except requests.RequestException as e:
            raise SmocoAuthError(f"登录网络错误: {e}") from e


class SmocoSttWorker(QObject):
    """Smoco 流式 STT Worker。socket.io 长连接 + 自带后台线程收结果。"""

    transcript_ready = pyqtSignal(str, float, int)  # 最终文本, start_time, entry_id
    interim_ready = pyqtSignal(str, float)          # 中间增量文本, start_time
    status_changed = pyqtSignal(str)                # 状态消息（如 recognize_completed）
    error_occurred = pyqtSignal(str)

    def __init__(self, host: str, email: str, password: str,
                 language: str = "ja", service_type: str = "local",
                 use_punctuator: bool = True, verify_ssl: bool = True):
        super().__init__()
        self._auth = SmocoAuth(host, email, password, verify_ssl=verify_ssl)
        self._verify_ssl = verify_ssl
        self._language = language            # GUI 短码 zh/ja/en
        self._service_type = service_type
        self._use_punctuator = use_punctuator
        self._room_name: str | None = None
        self._running = False
        self._connected = False
        self._sio: socketio.Client | None = None
        self._entry_seq = 0
        self._done_event = threading.Event()  # 收到 recognize_completed/cancel 时置位
        self._t0 = time.time()                # 会话起始（timestamp 解析失败时兜底）

    def set_config(self, host: str, email: str, password: str,
                   language: str = "ja", service_type: str = "local",
                   use_punctuator: bool = True, verify_ssl: bool = True):
        self._auth = SmocoAuth(host, email, password, verify_ssl=verify_ssl)
        self._verify_ssl = verify_ssl
        self._language = language
        self._service_type = service_type
        self._use_punctuator = use_punctuator

    def _api_language(self) -> str:
        return LANG_MAP.get(self._language, "japanese")

    def _elapsed(self, timestamp) -> float:
        """从服务端 SRT timestamp 取起始秒；解析失败则用会话已过秒数兜底。"""
        secs = _srt_start_seconds(timestamp)
        if secs is None:
            secs = time.time() - self._t0
        return secs

    def start(self):
        """连接 socket.io 并开始识别（在线程中运行，避免阻塞 UI）。"""
        self._running = True
        self._connected = False
        self._done_event = threading.Event()
        self._t0 = time.time()
        # 在后台线程做 login + connect，避免阻塞调用线程
        t = threading.Thread(target=self._start_async, daemon=True)
        t.start()

    def _start_async(self):
        try:
            token = self._auth.get_token()
        except SmocoAuthError as e:
            self.error_occurred.emit(str(e))
            self._running = False
            return

        try:
            self._sio = socketio.Client(
                reconnection=True,
                ssl_verify=self._verify_ssl,
                logger=False,
                engineio_logger=False,
            )
            self._register_events()
            self._sio.connect(
                self._auth.host,
                namespaces=[NAMESPACE],
                socketio_path=SIO_PATH,
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as e:
            logger.error(f"smoco socket.io 连接失败: {e}")
            self.error_occurred.emit(f"连接 smoco STT 失败: {e}")
            self._running = False
            return

        self._room_name = str(uuid.uuid4())
        self._sio.emit("join", {"room_name": self._room_name}, namespace=NAMESPACE)
        # 服务端 pure-ASR 路径（target_languages=[]）不 emit recognized_text_live 最终结果，
        # 必须走 translation 路径（target 非空）才能拿到源语言 final。这里传一个与源语言不同的
        # 目标强制走 translation 路径，API 的翻译结果忽略，只取源语言 ASR 文本（见 _on_final 过滤）。
        src = self._api_language()
        dummy_target = "chinese" if src != "chinese" else "english"
        start_payload = {
            "room_name": self._room_name,
            "task_name": "smoco-desktop",
            "user_id": "smoco-desktop",
            "service_type": self._service_type,
            "source_language": src,
            "target_languages": [dummy_target],
            "use_punctuator": self._use_punctuator,
        }
        logger.info(f"smoco start_ws room={self._room_name} lang={src}")
        self._sio.emit("speech_translation_live_start_ws", start_payload, namespace=NAMESPACE)
        self._connected = True

    def _register_events(self):
        sio = self._sio

        @sio.on("connect", namespace=NAMESPACE)
        def _on_connect():
            logger.info("smoco socket.io connected")
            self._connected = True
            # 重连（非首次连接）需要重新 join + start_ws 恢复识别会话
            if self._running and self._room_name and self._sio is not None:
                logger.warning("smoco 检测到重连，正在恢复识别会话...")
                # 生成新 room，避免与旧会话冲突
                self._room_name = str(uuid.uuid4())
                try:
                    self._sio.emit("join", {"room_name": self._room_name}, namespace=NAMESPACE)
                    src = self._api_language()
                    dummy_target = "chinese" if src != "chinese" else "english"
                    self._sio.emit(
                        "speech_translation_live_start_ws",
                        {
                            "room_name": self._room_name,
                            "task_name": "smoco-desktop",
                            "user_id": "smoco-desktop",
                            "service_type": self._service_type,
                            "source_language": src,
                            "target_languages": [dummy_target],
                            "use_punctuator": self._use_punctuator,
                        },
                        namespace=NAMESPACE,
                    )
                    logger.info(f"smoco 重连完成，新 room={self._room_name}")
                    self.status_changed.emit("reconnected")
                except Exception as e:
                    logger.error(f"smoco 重连后恢复会话失败: {e}")
                    self.error_occurred.emit(f"重连失败: {e}")

        @sio.on("disconnect", namespace=NAMESPACE)
        def _on_disconnect():
            logger.warning("smoco socket.io disconnected（网络波动？）")
            self._connected = False
            if self._running:
                self.status_changed.emit("disconnected")

        @sio.on("connect_error", namespace=NAMESPACE)
        def _on_conn_err(data):
            logger.error(f"smoco connect_error: {data}")
            self.error_occurred.emit(f"连接错误: {data}")

        @sio.on("recognize_status_live", namespace=NAMESPACE)
        def _on_status(data):
            status = data.get("status", "") if isinstance(data, dict) else str(data)
            logger.info(f"smoco status: {status}")
            self.status_changed.emit(status)
            # 服务端处理完（或取消）→ 置位，让 stop() 的优雅关闭继续断开
            if "recognize_completed" in status or "cancel" in status:
                self._done_event.set()

        @sio.on("recognizing_text_live", namespace=NAMESPACE)
        def _on_interim(data):
            if not isinstance(data, dict):
                return
            text = (data.get("text") or "").strip()
            if text:
                self.interim_ready.emit(text, self._elapsed(data.get("timestamp")))

        @sio.on("recognized_text_live", namespace=NAMESPACE)
        def _on_final(data):
            if not isinstance(data, dict):
                return
            text = (data.get("text") or "").strip()
            # 只取源语言的结果，忽略翻译结果（本版不显示 API 翻译）。
            # 服务端 language 返回短码（en/zh/ja）；self._language 可能是短码或全称，统一转短码比较。
            lang = (data.get("language") or "").lower()
            src_short = _TO_SHORT.get(self._language.lower(), self._language.lower())
            if not text or (lang and not lang.startswith(src_short)):
                return
            # 写 ASR 日志（与 Whisper 路径一致：供历史页 + LLM 翻译 session_dir），返回 entry_id
            try:
                entry_id = get_asr_logger().log_request(
                    chunk_size=0,
                    api_url=self._auth.host,
                    language=self._api_language(),
                    processing_time=0.0,
                    response_text=text,
                )
            except Exception as e:
                logger.warning(f"smoco 写 ASR 日志失败: {e}")
                entry_id = 0
            self.transcript_ready.emit(text, self._elapsed(data.get("timestamp")), entry_id)

        @sio.on("*", namespace=NAMESPACE)
        def _catchall(event, *args):
            logger.debug(f"smoco 事件 {event}: {str(args)[:120]}")

    def submit_audio(self, frame: bytes):
        """提交一帧音频（16k/mono/S16LE bytes）。在 socket.io 连接前/未运行时丢弃。"""
        if not self._running or not self._connected or not self._sio or not self._room_name:
            return
        # 能量门限：近静音帧不上传，省流量（引擎无关，复用 asr_quality）
        try:
            low, _dbfs = is_low_energy(frame)
            if low:
                return
        except Exception:
            pass
        try:
            self._sio.emit(
                "speech_translation_live_process_ws",
                {"room_name": self._room_name, "pcm": frame,
                 "sample_rate": 16000, "channel_num": 1, "data_type": "Int16Array"},
                namespace=NAMESPACE,
            )
        except Exception as e:
            logger.warning(f"smoco process_ws 发送失败: {e}")

    def stop(self):
        """停止识别并断开连接（后台优雅关闭：发 stop_ws → 等最终结果 flush → 断开）。"""
        self._running = False
        self._connected = False
        sio = self._sio
        self._sio = None  # 立即解绑，submit_audio 不再发送
        room = self._room_name
        self._room_name = None
        if sio is None:
            return

        def _shutdown():
            try:
                if room:
                    sio.emit(
                        "speech_translation_live_stop_ws",
                        {"room_name": room, "all_srt": {}, "all_text": {},
                         "task_name": "smoco-desktop", "source_language": self._api_language()},
                        namespace=NAMESPACE,
                    )
            except Exception as e:
                logger.warning(f"smoco stop_ws 发送失败: {e}")
            # 等服务端 flush 最终结果（收到 recognize_completed/cancel 或超时 5s）
            self._done_event.wait(timeout=5.0)
            try:
                sio.disconnect()
            except Exception:
                pass

        threading.Thread(target=_shutdown, daemon=True).start()


class SmocoSttController:
    """Smoco STT 控制器——接口形状对齐 ASRController，方便主窗口分流。"""

    def __init__(self):
        self._worker: SmocoSttWorker | None = None
        self._config = {
            "host": "https://dx-smoco-dev.sony.com.cn",
            "email": "",
            "password": "",
            "language": "ja",
            "service_type": "local",
            "use_punctuator": True,
            "verify_ssl": False,  # dev 主机为 Sony 内部 CA
        }

    def set_config(self, host: str, email: str, password: str,
                   language: str = "ja", service_type: str = "local",
                   use_punctuator: bool = True, verify_ssl: bool = False):
        self._config.update({
            "host": host, "email": email, "password": password,
            "language": language, "service_type": service_type,
            "use_punctuator": use_punctuator, "verify_ssl": verify_ssl,
        })

    def start(self, transcript_callback, interim_callback, error_callback,
              status_callback=None):
        """启动 STT。回调：最终文本/中间文本/错误/状态。"""
        self.stop()
        cfg = self._config
        if not cfg["email"] or not cfg["password"]:
            error_callback("未配置 smoco 账号（email/password），请在设置里填写")
            return
        get_asr_logger().start_session()
        self._worker = SmocoSttWorker(
            host=cfg["host"], email=cfg["email"], password=cfg["password"],
            language=cfg["language"], service_type=cfg["service_type"],
            use_punctuator=cfg["use_punctuator"], verify_ssl=cfg["verify_ssl"],
        )
        self._worker.transcript_ready.connect(transcript_callback)
        self._worker.interim_ready.connect(interim_callback)
        self._worker.error_occurred.connect(error_callback)
        if status_callback:
            self._worker.status_changed.connect(status_callback)
        self._worker.start()

    def submit_audio(self, frame: bytes):
        if self._worker:
            self._worker.submit_audio(frame)

    def stop(self):
        if self._worker:
            self._worker.stop()
            self._worker = None
        get_asr_logger().end_session()
