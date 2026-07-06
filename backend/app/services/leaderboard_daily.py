from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

LEADERBOARD_GENRES: frozenset[str] = frozenset({
    "platformer",
    "shmup",
    "survivor",
    "pingpong",
    "fighting",
    "parkour",
    "racing",
})
DEFAULT_TIMEZONE: str = "Asia/Shanghai"
STORE_LIMIT: int = 50

_file_locks: dict[str, threading.Lock] = {}
_file_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key: str = str(path.resolve())
    with _file_locks_guard:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]


def _data_root(base_dir: Path) -> Path:
    root: Path = base_dir / "leaderboard_daily"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_date(date_param: str, timezone: str = DEFAULT_TIMEZONE) -> date:
    if date_param == "today":
        return datetime.now(ZoneInfo(timezone)).date()
    return date.fromisoformat(date_param)


def _daily_file(base_dir: Path, genre: str, day: date) -> Path:
    genre_dir: Path = _data_root(base_dir) / genre
    genre_dir.mkdir(parents=True, exist_ok=True)
    return genre_dir / f"{day.isoformat()}.json"


def _sort_key(entry: dict[str, Any], genre: str) -> tuple[Any, ...]:
    score: int = int(entry.get("score") or 0)
    elapsed_ms: int = int(entry.get("elapsed_ms") or 0)
    survival_ms: int = int(entry.get("survival_ms") or 0)
    level_reached: int = int(entry.get("level_reached") or 0)
    created_at: str = str(entry.get("created_at") or "")

    if genre == "platformer":
        return (-level_reached, -score, elapsed_ms, created_at)
    if genre == "survivor":
        return (-survival_ms, -score, created_at)
    if genre == "parkour":
        return (-score, survival_ms, created_at)
    if genre == "racing":
        return (-score, elapsed_ms, created_at)
    if genre == "fighting":
        return (-score, created_at)
    if genre == "pingpong":
        return (-score, elapsed_ms, created_at)
    if genre == "shmup":
        return (-score, -survival_ms, created_at)
    return (-score, elapsed_ms, created_at)


def _read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, dict)]


def _atomic_write(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path = path.with_suffix(path.suffix + ".tmp")
    payload: str = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, path)


def _prune(entries: list[dict[str, Any]], genre: str, limit: int = STORE_LIMIT) -> list[dict[str, Any]]:
    sorted_entries: list[dict[str, Any]] = sorted(entries, key=lambda row: _sort_key(row, genre))
    return sorted_entries[:limit]


def append_entry(
    base_dir: Path,
    genre: str,
    *,
    creator_name: str,
    display_name: str,
    score: int = 0,
    elapsed_ms: int = 0,
    survival_ms: int = 0,
    level_reached: int = 0,
    metric: str,
    session_id: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    store_limit: int = STORE_LIMIT,
) -> dict[str, Any]:
    if genre not in LEADERBOARD_GENRES:
        raise ValueError(f"unsupported genre: {genre}")

    day: date = resolve_date("today", timezone)
    path: Path = _daily_file(base_dir, genre, day)
    created_at: str = datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")
    entry: dict[str, Any] = {
        "entry_id": uuid.uuid4().hex,
        "creator_name": creator_name.strip() or "小创作者",
        "display_name": display_name.strip() or "未命名游戏",
        "score": max(0, int(score)),
        "elapsed_ms": max(0, int(elapsed_ms)),
        "survival_ms": max(0, int(survival_ms)),
        "level_reached": max(0, int(level_reached)),
        "metric": metric,
        "created_at": created_at,
        "session_id": session_id,
    }

    lock: threading.Lock = _lock_for(path)
    with lock:
        entries: list[dict[str, Any]] = _read_entries(path)
        entries.append(entry)
        entries = _prune(entries, genre, store_limit)
        _atomic_write(path, entries)
    return entry


def get_daily_top(
    base_dir: Path,
    genre: str,
    *,
    day: date,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if genre not in LEADERBOARD_GENRES:
        raise ValueError(f"unsupported genre: {genre}")

    path: Path = _daily_file(base_dir, genre, day)
    lock: threading.Lock = _lock_for(path)
    with lock:
        entries: list[dict[str, Any]] = _read_entries(path)

    ranked: list[dict[str, Any]] = sorted(entries, key=lambda row: _sort_key(row, genre))[:limit]
    result: list[dict[str, Any]] = []
    for index, row in enumerate(ranked, start=1):
        item: dict[str, Any] = dict(row)
        item["rank"] = index
        result.append(item)
    return result
