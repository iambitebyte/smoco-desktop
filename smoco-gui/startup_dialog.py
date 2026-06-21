"""
ASR 启动对话框 - 服务器选择 + 健康检查 + 语言选择
"""

import sys
import requests
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from local_whisper_manager import get_local_whisper_manager


class HealthCheckWorker(QThread):
    """健康检查 Worker"""

    finished = pyqtSignal(bool, str)  # (成功, 消息)

    def __init__(self, api_url: str):
        super().__init__()
        self.api_url = api_url.rstrip("/")

    def run(self):
        """执行健康检查"""
        try:
            health_url = f"{self.api_url}/health"

            # 尝试两种不同的请求头
            headers1 = {
                "User-Agent": "python-requests/2.31.0",
            }
            headers2 = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
            }

            print(f"[Health Check] Requesting: {health_url}")

            # 先尝试简单的 User-Agent
            response = requests.get(health_url, headers=headers1, timeout=5.0)
            print(f"[Health Check] Response (simple UA): {response.status_code} - {response.text[:100]}")

            # 如果失败，尝试浏览器 UA
            if response.status_code != 200:
                response = requests.get(health_url, headers=headers2, timeout=5.0)
                print(f"[Health Check] Response (browser UA): {response.status_code} - {response.text[:100]}")

            if response.status_code == 200:
                result = response.json()
                model = result.get("model", "unknown")
                mode = result.get("mode", "unknown")
                # 只显示模型文件名（最后一个路径部分）
                if "/" in model or "\\" in model:
                    model = model.split("/")[-1].split("\\")[-1]
                message = f"{i18n.t('service_normal')} ({model}, {mode})"
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, f"{i18n.t('service_error')} {response.status_code}")
        except requests.exceptions.Timeout:
            self.finished.emit(False, i18n.t("service_timeout"))
        except requests.exceptions.ConnectionError:
            self.finished.emit(False, i18n.t("service_connection_error"))
        except Exception as e:
            self.finished.emit(False, f"{i18n.t('service_check_failed')}: {e}")


class ASRStartupDialog(QDialog):
    """ASR 启动对话框"""

    def __init__(self, servers: list, last_server: str = "", llm_config_ok: bool = False, parent=None):
        super().__init__(parent)

        self.setWindowTitle(i18n.t("startup_title"))
        self.setMinimumWidth(450)
        self.servers = servers
        self.last_server = last_server
        self.selected_server = None
        self.selected_language = "ja"
        self.health_ok = False
        self.llm_config_ok = llm_config_ok

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 服务器选择
        server_label = QLabel(i18n.t("select_whisper_server") + ":")
        layout.addWidget(server_label)

        self.server_combo = QComboBox()

        # 添加远程服务器
        for server in servers:
            url = server.get("url", "")
            name = server.get("name", "")
            if name:
                display = f"{name} - {url}"
            else:
                display = url
            self.server_combo.addItem(display, url)

        # 添加本地 Whisper 服务（如果在运行）
        local_manager = get_local_whisper_manager()
        if local_manager.is_running:
            local_url = local_manager.api_url
            local_name = i18n.t("local_server_name")
            display = f"{local_name} - {local_url}"
            # 插入到列表开头
            self.server_combo.insertItem(0, display, local_url)

        # 选中上次使用的服务器
        if last_server:
            for i in range(self.server_combo.count()):
                if self.server_combo.itemData(i) == last_server:
                    self.server_combo.setCurrentIndex(i)
                    break

        self.server_combo.currentIndexChanged.connect(self._on_server_changed)
        layout.addWidget(self.server_combo)

        # 当前服务器 URL 显示
        url_display_label = QLabel(i18n.t("current_server") + ":")
        layout.addWidget(url_display_label)

        self.url_display = QLabel()
        self.url_display.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.url_display)

        # 健康状态
        self.status_label = QLabel(i18n.t("service_status") + ": " + i18n.t("checking"))
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                background-color: #e0e0e0;
            }
        """)
        layout.addWidget(self.status_label)

        # 语言选择
        lang_label = QLabel(i18n.t("select_language") + ":")
        layout.addWidget(lang_label)

        lang_layout = QHBoxLayout()
        self.lang_group = QButtonGroup()

        self.radio_ja = QRadioButton(i18n.t("japanese"))
        self.radio_ja.setChecked(True)
        self.lang_group.addButton(self.radio_ja, 1)
        lang_layout.addWidget(self.radio_ja)

        self.radio_en = QRadioButton(i18n.t("english"))
        self.lang_group.addButton(self.radio_en, 2)
        lang_layout.addWidget(self.radio_en)

        layout.addLayout(lang_layout)

        # 翻译语言选择
        translate_lang_label = QLabel(i18n.t("select_translate_language") + ":")
        layout.addWidget(translate_lang_label)

        translate_lang_layout = QHBoxLayout()
        self.translate_lang_group = QButtonGroup()

        self.radio_translate_zh = QRadioButton(i18n.t("chinese"))
        self.translate_lang_group.addButton(self.radio_translate_zh, 1)
        translate_lang_layout.addWidget(self.radio_translate_zh)

        self.radio_translate_none = QRadioButton("无翻译")
        self.translate_lang_group.addButton(self.radio_translate_none, 0)
        translate_lang_layout.addWidget(self.radio_translate_none)

        # 根据 LLM 配置状态设置翻译选项
        if not self.llm_config_ok:
            # LLM 未配置，禁用翻译选项
            self.radio_translate_zh.setEnabled(False)
            self.radio_translate_none.setChecked(True)
        else:
            # LLM 已配置，启用翻译选项
            self.radio_translate_zh.setEnabled(True)
            self.radio_translate_zh.setChecked(True)

        layout.addLayout(translate_lang_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton(i18n.t("start"))
        self.btn_ok.setEnabled(False)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(i18n.t("cancel"))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # 语言切换
        self.lang_group.buttonClicked.connect(self._on_lang_changed)

        # 初始化显示和健康检查
        self._on_server_changed()

    def _on_server_changed(self):
        """服务器切换"""
        url = self.server_combo.currentData()
        if url:
            self.selected_server = url
            self.url_display.setText(url)
            self._start_health_check()

    def _on_lang_changed(self):
        """语言切换"""
        if self.radio_ja.isChecked():
            self.selected_language = "ja"
        else:
            self.selected_language = "en"

    def _start_health_check(self):
        """开始健康检查"""
        self.health_ok = False
        self.btn_ok.setEnabled(False)

        self.status_label.setText(i18n.t("service_checking"))
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                background-color: #FFF3CD;
            }
        """)

        if hasattr(self, 'health_worker'):
            self.health_worker.quit()
            self.health_worker.wait()

        self.health_worker = HealthCheckWorker(self.selected_server)
        self.health_worker.finished.connect(self._on_health_finished)
        self.health_worker.start()

    def _on_health_finished(self, ok: bool, message: str):
        """健康检查完成"""
        self.health_ok = ok

        if ok:
            self.status_label.setText(f"{i18n.t('service_status')}: ✓ {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    border-radius: 4px;
                    background-color: #D4EDDA;
                    color: #155724;
                }
            """)
            self.btn_ok.setEnabled(True)
        else:
            self.status_label.setText(f"{i18n.t('service_status')}: ✗ {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    border-radius: 4px;
                    background-color: #F8D7DA;
                    color: #721C24;
                }
            """)
            self.btn_ok.setEnabled(False)

    def _on_ok(self):
        """确定按钮"""
        if not self.health_ok:
            QMessageBox.warning(self, i18n.t("service_unavailable"), i18n.t("service_unavailable_msg"))
            return

        self.accept()

    def get_selected_server(self) -> str:
        """获取选中的服务器 URL"""
        return self.selected_server

    def get_selected_language(self) -> str:
        """获取选中的语言"""
        return self.selected_language

    def get_selected_translate_language(self) -> str:
        """获取选中的翻译语言"""
        if self.radio_translate_zh.isChecked():
            return "zh"
        else:
            return None  # 不翻译

    def closeEvent(self, event):
        """关闭对话框时停止健康检查线程"""
        if hasattr(self, 'health_worker') and self.health_worker.isRunning():
            self.health_worker.quit()
            self.health_worker.wait()
        super().closeEvent(event)
