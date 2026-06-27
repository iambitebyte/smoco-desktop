"""
history_reader 单元测试

跑法（在 smoco-gui 目录）：
  uv sync --dev          # 装 pytest
  uv run pytest tests/   # 跑测试

测试用 tmp_path + monkeypatch 隔离 ~/.smoco/data，不污染真实数据。
"""

import json
from pathlib import Path

import pytest

from history_reader import (
    list_sessions,
    get_session_entries,
    get_entry_detail,
    build_translation_index,
    export_session,
)


def _make_entry(entry_id: int, text: str = "sample", ts: str = "2025-01-01T10:00:00") -> dict:
    """造一条 entry_XXXX.json 的完整内容"""
    return {
        "id": entry_id,
        "timestamp": ts,
        "chunk_size_bytes": 48000,
        "api_url": "http://127.0.0.1:8000",
        "language": "ja",
        "processing_time_seconds": 0.5,
        "response_text": text,
    }


def _write_session(
    data_dir: Path,
    session_id: str,
    entries: list[dict],
    translations: dict[int, str] | None = None,
    metadata_format: str = "full",
    extra_translate_files: dict[int, list[dict]] | None = None,
) -> Path:
    """造一个完整的测试 session 目录。

    Args:
        translations: {entry_id: translation_text}，模拟 batch 写入
            （每个 entry 触发时，把已存在 + 自己一起写到一个 batch 文件）
        extra_translate_files: 手动指定 translate 文件内容，{first_id: [items]}
            （用于精确控制翻译覆盖场景）
        metadata_format: "full" 或 "simple"
    """
    session_dir = data_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # 写 entry 文件
    for e in entries:
        (session_dir / f"entry_{e['id']:04d}.json").write_text(
            json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写 translate 文件
    if extra_translate_files is not None:
        for first_id, items in extra_translate_files.items():
            (session_dir / f"translate_{first_id:04d}.json").write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    elif translations:
        ids_sorted = sorted(translations.keys())
        for i, current_id in enumerate(ids_sorted):
            batch_ids = ids_sorted[: i + 1]
            batch_data = [{"id": bid, "translation": translations[bid]} for bid in batch_ids]
            first_id = batch_ids[0]
            (session_dir / f"translate_{first_id:04d}.json").write_text(
                json.dumps(batch_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写 metadata.json
    if metadata_format == "full":
        metadata = {
            "start_time": entries[0]["timestamp"] if entries else None,
            "total_entries": len(entries),
            "entries": [
                {
                    "id": e["id"],
                    "timestamp": e["timestamp"],
                    "text": e["response_text"][:50]
                    + ("..." if len(e["response_text"]) > 50 else ""),
                }
                for e in entries
            ],
        }
    elif metadata_format == "simple":
        metadata = {
            "start_time": entries[0]["timestamp"] if entries else None,
            "end_time": "2025-01-01T11:00:00",
            "total_entries": len(entries),
            "entries": [e["id"] for e in entries],
        }
    else:
        raise ValueError(f"Unknown metadata_format: {metadata_format}")

    (session_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return session_dir


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """mock get_smoco_data_dir，返回临时目录"""
    monkeypatch.setattr("history_reader.get_smoco_data_dir", lambda: tmp_path)
    return tmp_path


# ---------- list_sessions ----------

def test_list_sessions_empty(data_dir):
    sessions, total = list_sessions()
    assert sessions == []
    assert total == 0


def test_list_sessions_sorted_descending(data_dir):
    """session 按 start_time 倒序"""
    for day, sid in enumerate(["20250101_100000", "20250102_100000", "20250103_100000"], start=1):
        _write_session(data_dir, sid, [_make_entry(1, ts=f"2025-01-0{day}T10:00:00")])
    sessions, total = list_sessions()
    assert total == 3
    assert sessions[0].session_id == "20250103_100000"
    assert sessions[1].session_id == "20250102_100000"
    assert sessions[2].session_id == "20250101_100000"


def test_list_sessions_pagination(data_dir):
    """25 个 session，每页 20"""
    for i in range(25):
        sid = f"2025010{i + 1:02d}_100000"
        _write_session(data_dir, sid, [_make_entry(1, ts=f"2025-01-{i + 1:02d}T10:00:00")])
    page1, total = list_sessions(0, 20)
    page2, total = list_sessions(20, 20)
    assert total == 25
    assert len(page1) == 20
    assert len(page2) == 5


def test_list_sessions_skips_non_session_dirs(data_dir):
    """跳过没有 metadata.json 的目录、跳过普通文件"""
    (data_dir / "not_a_session").mkdir()
    (data_dir / "random_file.txt").write_text("hello", encoding="utf-8")
    _write_session(data_dir, "20250101_100000", [_make_entry(1)])
    sessions, total = list_sessions()
    assert total == 1
    assert sessions[0].session_id == "20250101_100000"


def test_list_sessions_preview_from_first_entry(data_dir):
    entries = [_make_entry(1, text="first entry content"), _make_entry(2, text="second")]
    _write_session(data_dir, "20250101_100000", entries)
    sessions, _ = list_sessions()
    assert "first entry content" in sessions[0].preview


# ---------- get_session_entries ----------

def test_get_session_entries_full_metadata(data_dir):
    """完整版 metadata：直接读 entries 字段"""
    entries = [_make_entry(1, text="hello world"), _make_entry(2, text="another text")]
    _write_session(data_dir, "20250101_100000", entries, metadata_format="full")
    page, total = get_session_entries("20250101_100000")
    assert total == 2
    assert page[0].id == 1
    assert "hello world" in page[0].text_preview
    assert page[1].id == 2


def test_get_session_entries_simple_metadata(data_dir):
    """简化版 metadata（只有 id 列表）：回退扫 entry 文件"""
    entries = [_make_entry(1, text="from entry file")]
    _write_session(data_dir, "20250101_100000", entries, metadata_format="simple")
    page, total = get_session_entries("20250101_100000")
    assert total == 1
    assert page[0].id == 1
    assert "from entry file" in page[0].text_preview


def test_get_session_entries_pagination(data_dir):
    entries = [_make_entry(i, text=f"entry {i}") for i in range(1, 101)]
    _write_session(data_dir, "20250101_100000", entries)
    page1, total = get_session_entries("20250101_100000", 0, 50)
    page2, _ = get_session_entries("20250101_100000", 50, 50)
    assert total == 100
    assert len(page1) == 50
    assert page1[0].id == 1
    assert page1[-1].id == 50
    assert len(page2) == 50
    assert page2[0].id == 51


def test_get_session_entries_missing_session(data_dir):
    page, total = get_session_entries("nonexistent_session")
    assert page == []
    assert total == 0


# ---------- get_entry_detail + _find_translation ----------

def test_get_entry_detail_basic(data_dir):
    entries = [_make_entry(1, text="full original text")]
    _write_session(data_dir, "20250101_100000", entries)
    detail = get_entry_detail("20250101_100000", 1)
    assert detail is not None
    assert detail.id == 1
    assert detail.text == "full original text"
    assert detail.translation is None


def test_get_entry_detail_with_translation(data_dir):
    entries = [_make_entry(1, text="original")]
    _write_session(data_dir, "20250101_100000", entries, translations={1: "你好"})
    detail = get_entry_detail("20250101_100000", 1)
    assert detail.translation == "你好"


def test_find_translation_picks_latest(data_dir):
    """同一 entry 在多个 translate 文件里，取最新（文件名最大）"""
    entries = [_make_entry(1, text="x"), _make_entry(2, text="y")]
    _write_session(
        data_dir,
        "20250101_100000",
        entries,
        extra_translate_files={
            1: [
                {"id": 1, "translation": "old 1"},
                {"id": 2, "translation": "OLD version 2"},
            ],
            2: [
                {"id": 2, "translation": "NEW version 2"},
            ],
        },
    )
    # entry 2 在两个文件都有，取 translate_0002 的版本
    detail2 = get_entry_detail("20250101_100000", 2)
    assert detail2.translation == "NEW version 2"
    # entry 1 只在 translate_0001 有
    detail1 = get_entry_detail("20250101_100000", 1)
    assert detail1.translation == "old 1"


def test_get_entry_detail_missing_entry(data_dir):
    _write_session(data_dir, "20250101_100000", [_make_entry(1)])
    detail = get_entry_detail("20250101_100000", 999)
    assert detail is None


def test_get_entry_detail_missing_session(data_dir):
    detail = get_entry_detail("nonexistent_session", 1)
    assert detail is None


# ---------- build_translation_index ----------

def test_build_translation_index_overwrites_with_latest(data_dir):
    """升序遍历，后写入的覆盖前面的"""
    entries = [_make_entry(1), _make_entry(2)]
    session_dir = _write_session(
        data_dir,
        "20250101_100000",
        entries,
        extra_translate_files={
            1: [
                {"id": 1, "translation": "v1 of 1"},
                {"id": 2, "translation": "old v1 of 2"},
            ],
            2: [
                {"id": 2, "translation": "new v1 of 2"},
            ],
        },
    )
    index = build_translation_index(session_dir)
    assert index[1] == "v1 of 1"
    assert index[2] == "new v1 of 2"


def test_build_translation_index_empty(data_dir):
    """无翻译文件时返回空 dict"""
    entries = [_make_entry(1)]
    session_dir = _write_session(data_dir, "20250101_100000", entries)
    index = build_translation_index(session_dir)
    assert index == {}


def test_build_translation_index_ignores_latest_error_files(data_dir):
    """translate_latest.json 和 translate_error.json 不应被纳入"""
    session_dir = data_dir / "20250101_100000"
    session_dir.mkdir(parents=True)
    (session_dir / "translate_0001.json").write_text(
        json.dumps([{"id": 1, "translation": "real"}]), encoding="utf-8")
    (session_dir / "translate_latest.json").write_text(
        json.dumps([{"id": 1, "translation": "should be ignored"}]), encoding="utf-8")
    (session_dir / "translate_error.json").write_text(
        json.dumps({"error": "should be ignored"}), encoding="utf-8")
    index = build_translation_index(session_dir)
    assert index == {1: "real"}


# ---------- export_session ----------

def test_export_session_txt(data_dir, tmp_path):
    entries = [_make_entry(1, text="Hello world")]
    _write_session(data_dir, "20250101_100000", entries, translations={1: "你好世界"})
    out = tmp_path / "export.txt"
    export_session("20250101_100000", "txt", out)
    content = out.read_text(encoding="utf-8")
    assert "20250101_100000" in content
    assert "Hello world" in content
    assert "你好世界" in content


def test_export_session_markdown(data_dir, tmp_path):
    entries = [_make_entry(1, text="Hello"), _make_entry(2, text="World")]
    _write_session(data_dir, "20250101_100000", entries, translations={1: "你好", 2: "世界"})
    out = tmp_path / "export.md"
    export_session("20250101_100000", "markdown", out)
    content = out.read_text(encoding="utf-8")
    assert "# 转录会话 20250101_100000" in content
    assert "**原文:**" in content
    assert "**翻译:**" in content
    assert "Hello" in content
    assert "你好" in content


def test_export_session_no_translation(data_dir, tmp_path):
    """entry 没翻译也能导出（不包含翻译块）"""
    entries = [_make_entry(1, text="only original")]
    _write_session(data_dir, "20250101_100000", entries)
    out = tmp_path / "export.txt"
    export_session("20250101_100000", "txt", out)
    content = out.read_text(encoding="utf-8")
    assert "only original" in content
