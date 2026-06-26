"""
转录历史数据读取层（纯 Python，无 Qt 依赖）

数据目录结构:
  ~/.smoco/data/
    YYYYMMDD_HHMMSS/                # session 目录
      metadata.json                  # session 元数据 + entries 摘要
      entry_0001.json                # 单条转录完整记录
      translate_0001.json            # 一批翻译（文件名用 batch 第一条 id，内容是 list）
      translate_latest.json          # 最新翻译快照（非 entry，跳过）
      translate_error.json           # 错误日志（非 entry，跳过）

metadata.json 有两种格式（运行中 vs end_session 后），均需兼容:
  - 完整版:  entries = [{"id", "timestamp", "text"}, ...]
  - 简化版:  entries = [1, 2, 3, ...]   （仅 id 列表，需 fallback 扫 entry 文件）
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from paths import get_smoco_data_dir


TRANSLATE_FILE_RE = re.compile(r"^translate_(\d+)\.json$")
ENTRY_FILE_RE = re.compile(r"^entry_(\d+)\.json$")


@dataclass
class SessionMeta:
    session_id: str          # 目录名 YYYYMMDD_HHMMSS
    start_time: str | None
    end_time: str | None
    total_entries: int
    preview: str             # 第一条 entry 的文本预览


@dataclass
class EntrySummary:
    id: int
    timestamp: str
    text_preview: str


@dataclass
class EntryDetail:
    id: int
    timestamp: str
    text: str                # 完整原文
    translation: str | None
    api_url: str
    processing_time: float


def _data_dir() -> Path:
    return get_smoco_data_dir()


def list_sessions(offset: int = 0, limit: int = 20) -> tuple[list[SessionMeta], int]:
    """列出所有 session（按 start_time 倒序），返回 (当前页, 总数)。"""
    data_dir = _data_dir()
    if not data_dir.exists():
        return [], 0

    sessions: list[SessionMeta] = []
    for session_path in data_dir.iterdir():
        if not session_path.is_dir():
            continue
        meta = _load_session_meta(session_path)
        if meta is not None:
            sessions.append(meta)

    sessions.sort(key=lambda s: s.start_time or "", reverse=True)

    total = len(sessions)
    page = sessions[offset:offset + limit]
    return page, total


def _load_session_meta(session_path: Path) -> SessionMeta | None:
    meta_file = session_path / "metadata.json"
    if not meta_file.exists():
        return None

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    entries = data.get("entries", [])
    preview = ""
    if entries and isinstance(entries[0], dict):
        preview = entries[0].get("text", "") or ""

    return SessionMeta(
        session_id=session_path.name,
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        total_entries=data.get("total_entries", len(entries) if entries else 0),
        preview=preview,
    )


def get_session_entries(session_id: str, offset: int = 0, limit: int = 50) -> tuple[list[EntrySummary], int]:
    """获取 session 的 entries 分页。优先用 metadata.json，简化版回退扫 entry 文件。"""
    session_path = _data_dir() / session_id
    meta_file = session_path / "metadata.json"
    if not meta_file.exists():
        return [], 0

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [], 0

    raw_entries = data.get("entries", [])
    summaries: list[EntrySummary] = []
    for e in raw_entries:
        if isinstance(e, dict):
            summaries.append(EntrySummary(
                id=e.get("id", 0),
                timestamp=e.get("timestamp", ""),
                text_preview=e.get("text", "") or "",
            ))
        elif isinstance(e, int):
            # 简化版：只有 id，回退读 entry 文件取摘要
            entry_data = _load_entry_file(session_path, e)
            if entry_data:
                text = entry_data.get("response_text", "") or ""
                summaries.append(EntrySummary(
                    id=e,
                    timestamp=entry_data.get("timestamp", ""),
                    text_preview=text[:50],
                ))

    total = len(summaries)
    page = summaries[offset:offset + limit]
    return page, total


def get_entry_detail(session_id: str, entry_id: int) -> EntryDetail | None:
    """读单条 entry + 关联翻译。"""
    session_path = _data_dir() / session_id
    entry_data = _load_entry_file(session_path, entry_id)
    if entry_data is None:
        return None

    translation = _find_translation(session_path, entry_id)

    return EntryDetail(
        id=entry_data.get("id", entry_id),
        timestamp=entry_data.get("timestamp", ""),
        text=entry_data.get("response_text", "") or "",
        translation=translation,
        api_url=entry_data.get("api_url", "") or "",
        processing_time=entry_data.get("processing_time_seconds", 0.0),
    )


def _load_entry_file(session_path: Path, entry_id: int) -> dict | None:
    entry_file = session_path / f"entry_{entry_id:04d}.json"
    if not entry_file.exists():
        return None
    try:
        with open(entry_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _find_translation(session_path: Path, entry_id: int) -> str | None:
    """扫描 translate_*.json 找指定 entry_id 的最新翻译。

    翻译是上下文 batch 写入：每次新 entry 触发时，最近 N 条一起发去 LLM。
    所以同一个 entry_id 的翻译可能出现在多个 translate_*.json 里，
    后写入的（文件名更大）用的上下文更多，翻译更准。
    按文件名数字降序遍历，第一个匹配即为最新版本。
    """
    if not session_path.exists():
        return None

    translate_files: list[tuple[int, Path]] = []
    for f in session_path.iterdir():
        if not f.is_file():
            continue
        m = TRANSLATE_FILE_RE.match(f.name)
        if m:
            translate_files.append((int(m.group(1)), f))
    translate_files.sort(key=lambda x: x[0], reverse=True)  # 文件名降序 = 最新优先

    for _, f in translate_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                items = json.load(fp)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("id") == entry_id:
                return item.get("translation")
    return None


def build_translation_index(session_path: Path) -> dict[int, str]:
    """构建整个 session 的 entry_id → 最新译文 映射。

    用于 entries 列表批量显示译文预览（避免每条都扫一遍）。
    按文件名升序遍历，后写入的覆盖前面的，最终得到每条的最新版本。
    """
    if not session_path.exists():
        return {}

    translate_files: list[tuple[int, Path]] = []
    for f in session_path.iterdir():
        if not f.is_file():
            continue
        m = TRANSLATE_FILE_RE.match(f.name)
        if m:
            translate_files.append((int(m.group(1)), f))
    translate_files.sort(key=lambda x: x[0])  # 升序：让后写入的覆盖

    index: dict[int, str] = {}
    for _, f in translate_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                items = json.load(fp)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and "id" in item and "translation" in item:
                index[item["id"]] = item["translation"]
    return index


def export_session(session_id: str, fmt: str, out_path: Path) -> None:
    """导出 session 为 txt 或 markdown。"""
    session_path = _data_dir() / session_id

    # 收集所有 entry summaries
    all_summaries: list[EntrySummary] = []
    offset = 0
    while True:
        page, total = get_session_entries(session_id, offset, 100)
        if not page:
            break
        all_summaries.extend(page)
        offset += len(page)
        if offset >= total:
            break

    lines: list[str] = []
    if fmt == "markdown":
        lines.append(f"# 转录会话 {session_id}\n")
        for summary in all_summaries:
            detail = get_entry_detail(session_id, summary.id)
            if not detail:
                continue
            lines.append(f"## #{detail.id} ({detail.timestamp})\n")
            lines.append(f"**原文:**\n\n{detail.text}\n")
            if detail.translation:
                lines.append(f"**翻译:**\n\n{detail.translation}\n")
            lines.append("")
    else:  # txt
        lines.append(f"转录会话 {session_id}")
        lines.append("=" * 40)
        lines.append("")
        for summary in all_summaries:
            detail = get_entry_detail(session_id, summary.id)
            if not detail:
                continue
            lines.append(f"[{detail.timestamp}] #{detail.id}")
            lines.append(f"原文: {detail.text}")
            if detail.translation:
                lines.append(f"翻译: {detail.translation}")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
