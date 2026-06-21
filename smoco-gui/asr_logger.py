"""
ASR 数据日志
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from paths import get_smoco_data_dir


class ASRLogger:
    """ASR 调用日志记录器"""

    def __init__(self):
        self._session_dir: Path | None = None
        self._lock = Lock()
        self._entries = []

    def start_session(self):
        """开始新的转录会话"""
        with self._lock:
            # 创建会话目录，使用时间戳命名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._session_dir = get_smoco_data_dir() / timestamp
            self._session_dir.mkdir(parents=True, exist_ok=True)

            # 创建会话元数据文件
            metadata = {
                "start_time": datetime.now().isoformat(),
                "entries": []
            }
            self._save_metadata(metadata)
            self._entries = []

    def end_session(self):
        """结束转录会话"""
        with self._lock:
            if self._session_dir:
                # 保存最终元数据
                metadata = {
                    "start_time": self._entries[0]["timestamp"] if self._entries else None,
                    "end_time": datetime.now().isoformat(),
                    "total_entries": len(self._entries),
                    "entries": [e["id"] for e in self._entries]
                }
                self._save_metadata(metadata)
                self._session_dir = None
                self._entries = []

    def log_request(self,
                    chunk_size: int,
                    api_url: str,
                    language: str,
                    processing_time: float,
                    response_text: str) -> int:
        """记录一次 ASR 请求，返回 entry_id"""
        with self._lock:
            if not self._session_dir:
                return 0

            entry_id = len(self._entries) + 1
            entry = {
                "id": entry_id,
                "timestamp": datetime.now().isoformat(),
                "chunk_size_bytes": chunk_size,
                "api_url": api_url,
                "language": language,
                "processing_time_seconds": round(processing_time, 3),
                "response_text": response_text
            }

            self._entries.append(entry)

            # 保存到单独的 JSON 文件
            entry_file = self._session_dir / f"entry_{entry_id:04d}.json"
            with open(entry_file, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)

            # 更新元数据
            self._update_metadata()

            return entry_id

    def save_translations(self, translations: list):
        """保存翻译结果
        Args:
            translations: 翻译结果列表，格式 [{"id": 1, "translation": "..."}, ...]
        """
        with self._lock:
            if not self._session_dir:
                return

            # 生成翻译文件名
            if translations:
                first_id = translations[0]["id"]
                translate_file = self._session_dir / f"translate_{first_id:04d}.json"
                with open(translate_file, "w", encoding="utf-8") as f:
                    json.dump(translations, f, ensure_ascii=False, indent=2)

                # 同时保存为最新版本
                latest_file = self._session_dir / "translate_latest.json"
                with open(latest_file, "w", encoding="utf-8") as f:
                    json.dump(translations, f, ensure_ascii=False, indent=2)

    def save_translation_error(self, entries: list, error_msg: str):
        """保存翻译错误"""
        with self._lock:
            if not self._session_dir:
                return

            error_file = self._session_dir / "translate_error.json"
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "error": error_msg,
                "entries": entries
            }
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)

    @property
    def session_dir(self) -> Path:
        """获取当前会话目录"""
        return self._session_dir

    def _save_metadata(self, metadata: dict):
        """保存会话元数据"""
        if self._session_dir:
            meta_file = self._session_dir / "metadata.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _update_metadata(self):
        """更新会话元数据"""
        if self._session_dir and self._entries:
            metadata = {
                "start_time": self._entries[0]["timestamp"],
                "last_update": datetime.now().isoformat(),
                "total_entries": len(self._entries),
                "entries": [
                    {
                        "id": e["id"],
                        "timestamp": e["timestamp"],
                        "text": e["response_text"][:50] + "..." if len(e["response_text"]) > 50 else e["response_text"]
                    }
                    for e in self._entries
                ]
            }
            self._save_metadata(metadata)


# 全局日志实例
_asr_logger = ASRLogger()


def get_asr_logger() -> ASRLogger:
    """获取全局 ASR 日志实例"""
    return _asr_logger
