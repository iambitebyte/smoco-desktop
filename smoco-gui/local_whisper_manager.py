"""
本地 Whisper 服务管理器 - 子进程管理
"""

import sys
import subprocess
import os
import socket
import time
import requests
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from paths import get_smoco_root
from i18n import i18n
from gui_logger import get_gui_logger

# 使用支持打包环境的根目录
_smoco_root = get_smoco_root()

# 获取日志记录器
logger = get_gui_logger(__name__)

# 支持的模型：key=逻辑名（写入配置），value 含磁盘目录名 + i18n 文案 key + 是否推荐
MODELS = {
    "small-ov": {
        "dir": "whisper-small-ov",
        "label_key": "local_model_small_label",
        "desc_key": "local_model_small_desc",
        "recommended": True,
    },
    "large-v3-turbo-ov": {
        "dir": "whisper-large-v3-turbo-ov",
        "label_key": "local_model_turbo_label",
        "desc_key": "local_model_turbo_desc",
        "recommended": False,
    },
}

# 默认模型（低占用，适合大多数设备）
DEFAULT_MODEL = "small-ov"


def get_model_dir(model_key: str) -> str:
    """根据模型逻辑名返回磁盘目录名（即 --model-dir 使用的相对路径）"""
    info = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    return info["dir"]


class LocalWhisperStarter(QThread):
    """本地 Whisper 启动线程 - 不阻塞 UI"""

    progress = pyqtSignal(str, str)  # (status, message)
    finished = pyqtSignal(bool)       # (success)

    def __init__(self, manager):
        super().__init__()
        self._manager = manager

    def run(self):
        """执行启动"""
        try:
            # 检查端口是否可用
            if not self._manager._is_port_available():
                error_msg = f"端口 {self._manager._config.get('port', 8000)} 已被占用，请先停止其他服务或更改端口"
                logger.error(error_msg)
                self._manager.error_occurred.emit(error_msg)
                self.finished.emit(False)
                return

            self._manager._start_process()
            # 等待服务就绪
            if self._manager._wait_for_service():
                self.finished.emit(True)
            else:
                self.finished.emit(False)
        except Exception as e:
            error_msg = f"启动失败: {e}"
            logger.error(error_msg)
            self._manager.error_occurred.emit(error_msg)
            self.finished.emit(False)


class LocalWhisperManager(QObject):
    """本地 Whisper 服务管理器"""

    status_changed = pyqtSignal(str, str)  # (status, message) - 状态变化
    error_occurred = pyqtSignal(str)  # 错误信息
    output_received = pyqtSignal(str)  # 输出日志

    def __init__(self):
        super().__init__()
        self._process = None
        self._config = {
            "model": "small-ov",
            "port": 8000,
            "enabled": False,
            "device": "auto",  # auto, GPU, CPU
        }
        self._api_url = ""
        self._monitor_thread = None
        self._starter_thread = None
        self._is_stopping = False  # 标记是否正在主动停止

    @property
    def is_running(self) -> bool:
        """是否正在运行（检查进程和端口）"""
        if self._process and self._process.poll() is None:
            # 进程存在，检查端口是否监听
            if self._check_port():
                return True
        return False

    @property
    def api_url(self) -> str:
        """获取 API URL"""
        return self._api_url

    def _check_port(self) -> bool:
        """检查端口是否被监听"""
        port = self._config.get("port", 8000)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                return result == 0
        except:
            return False

    def _is_port_available(self) -> bool:
        """检查端口是否可用（未被占用）"""
        port = self._config.get("port", 8000)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    # 端口被占用，尝试终止占用进程
                    print(f"端口 {port} 被占用，尝试清理...")
                    self._kill_port_process(port)
                    # 等待一下，再检查
                    import time
                    time.sleep(0.5)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
                        s2.settimeout(1)
                        result2 = s2.connect_ex(("127.0.0.1", port))
                        return result2 != 0
                return True  # 端口未被占用
        except:
            return True

    def _kill_port_process(self, port: int):
        """终止占用指定端口的进程"""
        try:
            if sys.platform == "win32":
                # Windows: 使用 netstat 和 taskkill
                import subprocess
                result = subprocess.run(
                    ["netstat", "-ano", "|", "findstr", f":{port}"],
                    shell=True,
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.splitlines():
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                print(f"终止进程 PID: {pid}")
                                subprocess.run(["taskkill", "/F", "/PID", pid],
                                             shell=True, capture_output=True)
                            except:
                                pass
        except Exception as e:
            print(f"清理端口进程时出错: {e}")

    def check_running(self) -> bool:
        """检查服务是否实际运行"""
        return self.is_running


    def get_device_to_use(self) -> str:
        """获取要使用的设备：默认 AUTO（由 whisper-npu-api.exe 检测 GPU>NPU>CPU），用户可在 UI 手动指定 GPU/CPU"""
        device_config = self._config.get("device", "auto")
        if not device_config or device_config.lower() == "auto":
            return "AUTO"
        return device_config.upper()

    def set_config(self, model: str, port: int, device: str = "auto", enabled: bool = False):
        """设置配置"""
        self._config = {
            "model": model,
            "port": port,
            "device": device,
            "enabled": enabled,
        }
        self._api_url = f"http://127.0.0.1:{port}"

    def get_config(self) -> dict:
        """获取配置"""
        return self._config.copy()

    def start(self):
        """启动服务（异步）"""
        if self._starter_thread and self._starter_thread.isRunning():
            return  # 已经在启动中

        # 检查是否有旧的进程需要清理
        if self._process and self._process.poll() is not None:
            # 进程已结束，清理
            self._process = None

        if self.is_running:
            self.status_changed.emit("running", i18n.t("local_already_running"))
            return

        # 在后台线程中启动
        self._starter_thread = LocalWhisperStarter(self)
        self._starter_thread.progress.connect(self.status_changed.emit)
        self._starter_thread.finished.connect(self._on_start_finished)
        self._starter_thread.start()

    def _on_start_finished(self, success: bool):
        """启动完成"""
        self._starter_thread = None
        if not success and not self._is_stopping:
            # 启动失败且不是主动停止
            pass

    def _start_process(self):
        """实际启动进程（在后台线程中调用）"""
        self._is_stopping = False

        logger.debug(f"开始启动 Local Whisper 服务，项目根目录: {_smoco_root}")

        # 定位 whisper API 可执行文件
        # 打包环境：whisper-local-npu/whisper-npu-api/whisper-npu-api.exe 与 SmocoDesktop.exe 同级
        # 开发环境：仍走 .venv/Scripts/python.exe + whisper_npu_api.py（保持开发体验）
        if getattr(sys, 'frozen', False):
            # 打包环境：使用 exe 所在目录
            app_dir = Path(sys.executable).parent
            api_dir = app_dir / "whisper-local-npu"
            api_exe = api_dir / "whisper-npu-api" / "whisper-npu-api.exe"
        else:
            # 开发环境：使用项目根目录下的 whisper-local-npu
            api_dir = _smoco_root / "whisper-local-npu"
            api_exe = api_dir / ".venv" / "Scripts" / "python.exe"
            api_file_dev = api_dir / "whisper_npu_api.py"

        logger.debug(f"检查 API 可执行文件: {api_exe}")

        if not api_exe.exists():
            error_msg = f"API 可执行文件不存在: {api_exe}"
            logger.error(error_msg)
            if getattr(sys, 'frozen', False):
                hint = (
                    f"Local Whisper NPU 可执行文件未找到。\n\n"
                    f"应用分发可能损坏，请重新下载或安装。\n"
                    f"期望位置: {api_exe}"
                )
                raise Exception(hint)
            else:
                raise Exception(f"{api_exe} 不存在，请先在 whisper-local-npu 目录运行 'uv sync'")

        logger.info(f"找到 API 可执行文件: {api_exe}")

        self.status_changed.emit("starting", i18n.t("local_starting"))

        # 检测要使用的设备
        device_to_use = self.get_device_to_use()
        logger.info(f"检测到的设备: {device_to_use}")

        # 设置环境变量（解决编码问题）
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }

        # 解析所选模型的磁盘目录并校验存在（--model-dir 相对 cwd=api_dir）
        model_dir = get_model_dir(self._config.get("model", DEFAULT_MODEL))
        model_path = api_dir / model_dir
        if not model_path.exists():
            error_msg = f"{i18n.t('local_model_missing')} ({model_dir})"
            logger.error(error_msg)
            raise Exception(error_msg)
        logger.info(f"使用模型目录: {model_dir}")

        # 构造启动命令
        if getattr(sys, 'frozen', False):
            # 打包环境：直接 spawn whisper-npu-api.exe
            cmd = [
                str(api_exe),
                "--model-dir", model_dir,
                "--language", "ja",
                "--port", str(self._config["port"]),
                "--device", device_to_use,
            ]
        else:
            # 开发环境：python.exe + whisper_npu_api.py
            cmd = [
                str(api_exe), str(api_file_dev),
                "--model-dir", model_dir,
                "--language", "ja",
                "--port", str(self._config["port"]),
                "--device", device_to_use,
            ]

        logger.info(f"启动进程: {' '.join(cmd)}")

        # 启动子进程（使用字节模式以更好处理编码）
        # 设置创建标志以隐藏控制台窗口并防止 CTRL+C 信号
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,  # 使用字节模式
            bufsize=1,  # 行缓冲
            cwd=str(api_dir),
            env=env,
            creationflags=creation_flags,
        )

        # 启动监控线程
        self._monitor_thread = LocalWhisperMonitor(self._process)
        self._monitor_thread.output_received.connect(self._on_output)
        self._monitor_thread.process_ended.connect(self._on_process_ended)
        self._monitor_thread.start()

    def _wait_for_service(self) -> bool:
        """等待服务就绪（在后台线程中调用）"""
        max_wait = 120  # 最多等待 120 秒（下载模型可能需要时间）
        start_time = time.time()
        check_interval = 1  # 每秒检查一次

        while time.time() - start_time < max_wait:
            if self._is_stopping:
                return False  # 被中断

            if self._process and self._process.poll() is not None:
                # 进程已退出
                return False

            try:
                response = requests.get(f"{self._api_url}/health", timeout=1)
                if response.status_code == 200:
                    result = response.json()
                    model = result.get("model", "unknown")
                    # 只显示模型文件名
                    if "/" in model or "\\" in model:
                        model = model.split("/")[-1].split("\\")[-1]
                    self.status_changed.emit("running", f"{i18n.t('local_running')} ({model})")
                    return True
            except:
                pass

            time.sleep(check_interval)

        # 超时
        error_msg = i18n.t("local_start_timeout")
        logger.error(error_msg)
        self.error_occurred.emit(error_msg)
        return False

    def stop(self):
        """停止服务"""
        self._is_stopping = True

        if self._process:
            try:
                process_id = self._process.pid
                logger.info(f"正在停止 Local Whisper 进程 (PID: {process_id})...")

                # Windows: 使用 taskkill 强制终止进程树
                if sys.platform == "win32":
                    import subprocess
                    try:
                        # 终止进程及其所有子进程
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process_id)],
                            capture_output=True,
                            timeout=5
                        )
                        logger.info(f"已通过 taskkill 终止进程树 (PID: {process_id})")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"taskkill 超时 (PID: {process_id})")
                    except Exception as e:
                        logger.error(f"taskkill 失败: {e}")
                else:
                    # Unix-like: 先尝试优雅关闭
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # 强制终止
                        self._process.kill()
                        self._process.wait(timeout=2)

                # 清理进程引用
                self._process = None
                logger.info("Local Whisper 进程已停止")

            except Exception as e:
                logger.error(f"停止 Local Whisper 进程时出错: {e}")
                # 确保清理
                self._process = None

        if self._monitor_thread:
            try:
                self._monitor_thread.quit()
                self._monitor_thread.wait(timeout=1000)
                self._monitor_thread = None
            except Exception as e:
                logger.warning(f"清理监控线程时出错: {e}")

        self.status_changed.emit("stopped", i18n.t("local_stopped"))

        # 额外清理：确保端口被释放
        if self._check_port():
            logger.warning(f"端口 {self._config.get('port', 8000)} 仍被占用，尝试清理...")
            self._kill_port_process(self._config.get('port', 8000))

    def _on_output(self, line: str):
        """处理输出"""
        logger.info(f"[Local Whisper] {line}")
        self.output_received.emit(line)  # 发出输出信号

        # 检测下载进度
        if "Downloading" in line or "download" in line.lower():
            self.status_changed.emit("downloading", line)

    def _on_process_ended(self, exit_code: int):
        """进程结束"""
        # 如果正在主动停止，不报错
        if self._is_stopping:
            self.status_changed.emit("stopped", i18n.t("local_stopped"))
        elif exit_code != 0:
            # 只有非主动停止且非零退出码才报错
            error_msg = f"进程异常退出 (exit code: {exit_code})"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        else:
            self.status_changed.emit("stopped", i18n.t("local_stopped"))
        self._process = None


class LocalWhisperMonitor(QThread):
    """本地 Whisper 进程监控线程"""

    output_received = pyqtSignal(str)  # 输出行
    process_ended = pyqtSignal(int)    # 进程结束 (exit_code)

    def __init__(self, process: subprocess.Popen):
        super().__init__()
        self._process = process

    def run(self):
        """监控进程输出"""
        while True:
            line_bytes = self._process.stdout.readline()
            if not line_bytes:
                # 进程结束
                try:
                    self._process.wait()
                    self.process_ended.emit(self._process.returncode)
                except:
                    self.process_ended.emit(-1)
                break

            # 手动解码，使用 errors='ignore' 或 'surrogateescape' 处理编码问题
            try:
                line = line_bytes.decode('utf-8').strip()
            except UnicodeDecodeError:
                # 如果 UTF-8 解码失败，尝试使用系统默认编码
                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except:
                    line = str(line_bytes).strip()

            self.output_received.emit(line)


# 全局实例
_local_whisper_manager = None


def get_local_whisper_manager() -> LocalWhisperManager:
    """获取全局实例"""
    global _local_whisper_manager
    if _local_whisper_manager is None:
        _local_whisper_manager = LocalWhisperManager()
    return _local_whisper_manager
