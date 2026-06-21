"""
翻译 Worker - 异步处理翻译任务
"""

import sys
import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from concurrent.futures import ThreadPoolExecutor

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from llm_client import get_llm_client
from paths import get_smoco_data_dir
from asr_logger import get_asr_logger
from gui_logger import get_gui_logger

# 获取日志记录器
log = get_gui_logger(__name__)


class TranslationWorker(QObject):
    """翻译 Worker - 异步处理翻译任务"""

    translation_ready = pyqtSignal(list)  # 信号：翻译结果 [(id, translation), ...]
    error_occurred = pyqtSignal(int, str)   # 信号：翻译错误 (entry_id, error_msg)

    def __init__(self):
        super().__init__()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._target_lang = "zh"
        self._max_queue_size = 50  # 最大队列大小
        self._queue = []
        self._processing = False

    def set_language(self, lang: str):
        """设置翻译语言"""
        self._target_lang = lang

    def submit_translation(self, entries: list[dict], session_dir: Path):
        """
        提交翻译任务

        Args:
            entries: 待翻译的条目列表，格式 [{"id": 1, "text": "...", "timestamp": "..."}, ...]
            session_dir: 当前会话目录
        """
        if len(self._queue) >= self._max_queue_size:
            log.warning(f"翻译队列已满 ({self._max_queue_size})，跳过此批翻译")
            return

        # 提交到线程池
        self._executor.submit(self._translate, entries, session_dir)

    def _translate(self, entries: list[dict], session_dir: Path):
        """执行翻译（在线程池中运行）"""
        llm_client = get_llm_client()

        if not entries:
            return

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                success, translations, error_msg = llm_client.translate(
                    [entry for entry in entries],
                    self._target_lang
                )

                if success:
                    # 保存翻译结果
                    self._save_translations(translations, session_dir)

                    # 发射信号
                    result = [(t["id"], t["translation"]) for t in translations]
                    self.translation_ready.emit(result)
                    return
                else:
                    if attempt < max_retries - 1:
                        log.warning(f"翻译失败，重试 ({attempt + 1}/{max_retries}): {error_msg}")
                    else:
                        # 最后一次重试也失败
                        log.error(f"翻译失败，已重试 {max_retries} 次: {error_msg}")
                        # 记录错误
                        self._save_error(entries, session_dir, error_msg)
                        # 发射错误信号（只通知第一个 entry）
                        self.error_occurred.emit(entries[0]["id"], error_msg)
                        return

            except Exception as e:
                log.exception(f"翻译异常: {e}")
                if attempt == max_retries - 1:
                    self._save_error(entries, session_dir, str(e))
                    self.error_occurred.emit(entries[0]["id"], str(e))

    def _save_translations(self, translations: list, session_dir: Path):
        """保存翻译结果"""
        try:
            asr_logger = get_asr_logger()
            asr_logger.save_translations(translations)
            log.info(f"翻译结果已保存")
        except Exception as e:
            log.error(f"保存翻译结果失败: {e}")

    def _save_error(self, entries: list, session_dir: Path, error_msg: str):
        """保存翻译错误"""
        try:
            asr_logger = get_asr_logger()
            asr_logger.save_translation_error(entries, error_msg)
            log.info(f"翻译错误已记录")
        except Exception as e:
            log.error(f"保存错误记录失败: {e}")

    def stop(self):
        """停止翻译"""
        self._executor.shutdown(wait=False)


class TranslationController:
    """翻译控制器"""

    def __init__(self):
        self._worker = TranslationWorker()
        self._thread = None
        self._target_lang = "zh"
        self._session_dir = None

    def set_language(self, lang: str):
        """设置翻译语言"""
        self._target_lang = lang
        if self._worker:
            self._worker.set_language(lang)

    def start(self, translation_callback, error_callback):
        """启动翻译"""
        self.stop()

        self._worker = TranslationWorker()
        self._worker.set_language(self._target_lang)
        self._worker.translation_ready.connect(translation_callback)
        self._worker.error_occurred.connect(error_callback)

    def submit(self, entries: list[dict], session_dir: Path):
        """提交翻译任务"""
        self._session_dir = session_dir
        if self._worker:
            self._worker.submit_translation(entries, session_dir)

    def stop(self):
        """停止翻译"""
        if self._worker:
            self._worker.stop()
            self._worker = None
