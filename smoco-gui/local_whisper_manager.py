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

# 添加父目录到 Python 路径
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))

from i18n import i18n

# 支持的模型
MODELS = {
    "small": "Small (推荐，较快且准确率好)",
}


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
                self._manager.error_occurred.emit(f"端口 {self._manager._config.get('port', 8000)} 已被占用，请先停止其他服务或更改端口")
                self.finished.emit(False)
                return

            self._manager._start_process()
            # 等待服务就绪
            if self._manager._wait_for_service():
                self.finished.emit(True)
            else:
                self.finished.emit(False)
        except Exception as e:
            self._manager.error_occurred.emit(f"启动失败: {e}")
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
            "model": "small",
            "port": 8000,
            "enabled": False,
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

    def set_config(self, model: str, port: int, enabled: bool = False):
        """设置配置"""
        self._config = {
            "model": model,
            "port": port,
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

        # 检查 API 文件
        api_file = _smoco_root / "whisper-local" / "whisper_local_api.py"
        if not api_file.exists():
            raise Exception(f"API 文件不存在: {api_file}")

        # 查找 whisper-local 的 Python 解释器
        whisper_local_venv = _smoco_root / "whisper-local" / ".venv"
        if whisper_local_venv.exists():
            # Windows: .venv\Scripts\python.exe
            # Linux/Mac: .venv/bin/python
            if sys.platform == "win32":
                python_exe = whisper_local_venv / "Scripts" / "python.exe"
            else:
                python_exe = whisper_local_venv / "bin" / "python"

            if not python_exe.exists():
                raise Exception(f"Python 解释器不存在: {python_exe}")
        else:
            raise Exception("whisper-local/.venv 不存在，请先在 whisper-local 目录运行 'uv sync'")

        self.status_changed.emit("starting", i18n.t("local_starting"))

        # 设置环境变量（解决编码问题）
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }

        # 启动子进程（使用字节模式以更好处理编码）
        self._process = subprocess.Popen(
            [str(python_exe), str(api_file),
             "--model", self._config["model"],
             "--port", str(self._config["port"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,  # 使用字节模式
            bufsize=1,  # 行缓冲
            cwd=str(_smoco_root / "whisper-local"),
            env=env,
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
        self.error_occurred.emit(i18n.t("local_start_timeout"))
        return False

    def stop(self):
        """停止服务"""
        self._is_stopping = True

        if self._process:
            try:
                # 先尝试优雅关闭
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    self._process.kill()
                    self._process.wait(timeout=2)
            except:
                pass
            finally:
                self._process = None

        if self._monitor_thread:
            self._monitor_thread.quit()
            self._monitor_thread.wait(timeout=1000)
            self._monitor_thread = None

        self.status_changed.emit("stopped", i18n.t("local_stopped"))

    def _on_output(self, line: str):
        """处理输出"""
        print(f"[Local Whisper] {line}")
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
            self.error_occurred.emit(f"进程异常退出 (exit code: {exit_code})")
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
