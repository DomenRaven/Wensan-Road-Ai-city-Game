"""教学学情库 · SQLite（与 auth 同库，与 learned_skills 分离）。"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings

_AGENT_REPLY_MAX_CHARS = 80_000

RATING_LABELS: dict[int, str] = {
    1: "非常不满意",
    2: "比较不满意",
    3: "一般般",
    4: "比较满意",
    5: "非常满意",
}


def rating_label(score: int) -> str:
    return RATING_LABELS.get(int(score), "")


def compose_agent_reply_full(
    message: str,
    summary: str,
    how_to_play: list[str] | None = None,
) -> str:
    """F5-L2：对齐 UI · message||summary + how_to_play 列表。"""
    main: str = (message or "").strip() or (summary or "").strip()
    steps: list[str] = [str(s).strip() for s in (how_to_play or []) if str(s).strip()]
    if not steps:
        return main
    parts: list[str] = []
    if main:
        parts.append(main)
        parts.append("")
    parts.append("试玩步骤：")
    for i, step in enumerate(steps, start=1):
        parts.append(f"{i}. {step}")
    return "\n".join(parts).strip()


@dataclass(frozen=True)
class AgentTurnRecord:
    turn_id: str
    play_session_id: str
    user_text: str
    agent_reply_full: str
    agent_summary: str
    truncated: bool


class LearningAnalyticsStore:
    def __init__(self, db_path: Path, blobs_dir: Path) -> None:
        self._db_path: Path = db_path
        self._blobs_dir: Path = blobs_dir
        self._lock = threading.RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._blobs_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS play_sessions (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL UNIQUE,
                        user_id TEXT,
                        guest_key TEXT,
                        genre TEXT NOT NULL DEFAULT '',
                        display_name TEXT NOT NULL DEFAULT '',
                        creator_name TEXT NOT NULL DEFAULT '',
                        auth_mode TEXT NOT NULL DEFAULT 'guest',
                        workspace_key TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL,
                        ended_at REAL
                    );
                    CREATE INDEX IF NOT EXISTS idx_play_sessions_user
                        ON play_sessions(user_id);

                    CREATE TABLE IF NOT EXISTS agent_turns (
                        id TEXT PRIMARY KEY,
                        play_session_id TEXT NOT NULL
                            REFERENCES play_sessions(id) ON DELETE CASCADE,
                        session_id TEXT NOT NULL,
                        user_id TEXT,
                        turn_index INTEGER NOT NULL DEFAULT 0,
                        user_text TEXT NOT NULL DEFAULT '',
                        agent_reply_full TEXT NOT NULL DEFAULT '',
                        agent_summary TEXT NOT NULL DEFAULT '',
                        how_to_play_json TEXT NOT NULL DEFAULT '[]',
                        provider TEXT NOT NULL DEFAULT '',
                        gate_passed INTEGER NOT NULL DEFAULT 0,
                        partial INTEGER NOT NULL DEFAULT 0,
                        rolled_back INTEGER NOT NULL DEFAULT 0,
                        outcome TEXT NOT NULL DEFAULT '',
                        goals_json TEXT NOT NULL DEFAULT '[]',
                        sandbox_files_json TEXT NOT NULL DEFAULT '[]',
                        truncated INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_agent_turns_session
                        ON agent_turns(session_id);
                    CREATE INDEX IF NOT EXISTS idx_agent_turns_play
                        ON agent_turns(play_session_id);

                    CREATE TABLE IF NOT EXISTS turn_ratings (
                        turn_id TEXT PRIMARY KEY
                            REFERENCES agent_turns(id) ON DELETE CASCADE,
                        user_id TEXT,
                        score INTEGER NOT NULL,
                        label TEXT NOT NULL DEFAULT '',
                        comment TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        revision INTEGER NOT NULL DEFAULT 1
                    );

                    CREATE TABLE IF NOT EXISTS agent_turn_diffs (
                        turn_id TEXT PRIMARY KEY
                            REFERENCES agent_turns(id) ON DELETE CASCADE,
                        rolled_back INTEGER NOT NULL DEFAULT 0,
                        file_count INTEGER NOT NULL DEFAULT 0,
                        overview_note TEXT NOT NULL DEFAULT '',
                        blob_relpath TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def ensure_play_session(
        self,
        *,
        session_id: str,
        user_id: str | None,
        auth_mode: str,
        genre: str = "",
        display_name: str = "",
        creator_name: str = "",
        workspace_key: str = "",
    ) -> str:
        """返回 play_sessions.id；已存在则更新可变元数据。"""
        now: float = time.time()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT id FROM play_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if row is not None:
                    play_id = str(row["id"])
                    conn.execute(
                        "UPDATE play_sessions SET genre = CASE WHEN ? != '' THEN ? ELSE genre END, "
                        "display_name = CASE WHEN ? != '' THEN ? ELSE display_name END, "
                        "creator_name = CASE WHEN ? != '' THEN ? ELSE creator_name END, "
                        "workspace_key = CASE WHEN ? != '' THEN ? ELSE workspace_key END "
                        "WHERE id = ?",
                        (
                            genre,
                            genre,
                            display_name,
                            display_name,
                            creator_name,
                            creator_name,
                            workspace_key,
                            workspace_key,
                            play_id,
                        ),
                    )
                    conn.commit()
                    return play_id

                play_id = str(uuid.uuid4())
                guest_key = None if user_id else session_id
                conn.execute(
                    "INSERT INTO play_sessions "
                    "(id, session_id, user_id, guest_key, genre, display_name, creator_name, "
                    "auth_mode, workspace_key, created_at, ended_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        play_id,
                        session_id,
                        user_id,
                        guest_key,
                        genre,
                        display_name,
                        creator_name,
                        auth_mode or "guest",
                        workspace_key,
                        now,
                    ),
                )
                conn.commit()
                return play_id
            finally:
                conn.close()

    def mark_play_session_ended(self, session_id: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE play_sessions SET ended_at = ? WHERE session_id = ? AND ended_at IS NULL",
                    (time.time(), session_id),
                )
                conn.commit()
            finally:
                conn.close()

    def record_agent_turn(
        self,
        *,
        session_id: str,
        user_id: str | None,
        auth_mode: str,
        user_text: str,
        message: str,
        summary: str,
        how_to_play: list[str],
        provider: str = "",
        gate_passed: bool = False,
        partial: bool = False,
        rolled_back: bool = False,
        goals: list[str] | None = None,
        sandbox_files: list[str] | None = None,
        genre: str = "",
        display_name: str = "",
        creator_name: str = "",
        workspace_key: str = "",
    ) -> AgentTurnRecord:
        play_id: str = self.ensure_play_session(
            session_id=session_id,
            user_id=user_id,
            auth_mode=auth_mode,
            genre=genre,
            display_name=display_name,
            creator_name=creator_name,
            workspace_key=workspace_key,
        )
        full: str = compose_agent_reply_full(message, summary, how_to_play)
        truncated: bool = False
        if len(full) > _AGENT_REPLY_MAX_CHARS:
            full = full[:_AGENT_REPLY_MAX_CHARS]
            truncated = True

        turn_id: str = f"trn_{uuid.uuid4().hex[:16]}"
        now: float = time.time()
        outcome: str = (
            "failed"
            if rolled_back
            else ("partial" if partial else ("success" if gate_passed else "failed"))
        )

        with self._lock:
            conn = self._connect()
            try:
                idx_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM agent_turns WHERE play_session_id = ?",
                    (play_id,),
                ).fetchone()
                turn_index: int = int(idx_row["c"]) if idx_row else 0
                conn.execute(
                    "INSERT INTO agent_turns "
                    "(id, play_session_id, session_id, user_id, turn_index, user_text, "
                    "agent_reply_full, agent_summary, how_to_play_json, provider, "
                    "gate_passed, partial, rolled_back, outcome, goals_json, "
                    "sandbox_files_json, truncated, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        turn_id,
                        play_id,
                        session_id,
                        user_id,
                        turn_index,
                        user_text,
                        full,
                        (summary or "").strip(),
                        json.dumps(list(how_to_play or []), ensure_ascii=False),
                        provider,
                        1 if gate_passed else 0,
                        1 if partial else 0,
                        1 if rolled_back else 0,
                        outcome,
                        json.dumps(list(goals or []), ensure_ascii=False),
                        json.dumps(list(sandbox_files or []), ensure_ascii=False),
                        1 if truncated else 0,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return AgentTurnRecord(
            turn_id=turn_id,
            play_session_id=play_id,
            user_text=user_text,
            agent_reply_full=full,
            agent_summary=(summary or "").strip(),
            truncated=truncated,
        )

    def get_turn(self, turn_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM agent_turns WHERE id = ?",
                    (turn_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        return dict(row)

    def list_turns_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM agent_turns WHERE session_id = ? ORDER BY turn_index ASC",
                    (session_id,),
                ).fetchall()
            finally:
                conn.close()
        return [dict(r) for r in rows]

    def count_turns(self) -> int:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT COUNT(*) AS c FROM agent_turns").fetchone()
            finally:
                conn.close()
        return int(row["c"]) if row else 0

    def upsert_turn_rating(
        self,
        *,
        turn_id: str,
        score: int,
        comment: str = "",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        score_i: int = int(score)
        if score_i not in RATING_LABELS:
            raise ValueError("score must be 1..5")
        label: str = RATING_LABELS[score_i]
        note: str = (comment or "").strip()[:200]
        now: float = time.time()
        with self._lock:
            conn = self._connect()
            try:
                turn = conn.execute(
                    "SELECT id, session_id FROM agent_turns WHERE id = ?",
                    (turn_id,),
                ).fetchone()
                if turn is None:
                    raise KeyError("turn not found")
                existing = conn.execute(
                    "SELECT revision FROM turn_ratings WHERE turn_id = ?",
                    (turn_id,),
                ).fetchone()
                if existing is None:
                    conn.execute(
                        "INSERT INTO turn_ratings "
                        "(turn_id, user_id, score, label, comment, created_at, updated_at, revision) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                        (turn_id, user_id, score_i, label, note, now, now),
                    )
                    revision = 1
                else:
                    revision = int(existing["revision"]) + 1
                    conn.execute(
                        "UPDATE turn_ratings SET user_id = ?, score = ?, label = ?, comment = ?, "
                        "updated_at = ?, revision = ? WHERE turn_id = ?",
                        (user_id, score_i, label, note, now, revision, turn_id),
                    )
                conn.commit()
            finally:
                conn.close()
        return {
            "turn_id": turn_id,
            "score": score_i,
            "label": label,
            "comment": note,
            "revision": revision,
            "updated_at": now,
        }

    def get_rating(self, turn_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM turn_ratings WHERE turn_id = ?",
                    (turn_id,),
                ).fetchone()
            finally:
                conn.close()
        return dict(row) if row is not None else None

    def save_turn_diff(self, turn_id: str, diff_payload: dict[str, Any]) -> str:
        """将 Diff JSON 写入 blobs/，索引进 agent_turn_diffs。返回 blob 相对路径。"""
        turn = self.get_turn(turn_id)
        if turn is None:
            raise KeyError("turn not found")
        rel = f"{turn_id}/diff.json"
        blob_path: Path = self._blobs_dir / rel
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_text(
            json.dumps(diff_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        now: float = time.time()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO agent_turn_diffs "
                    "(turn_id, rolled_back, file_count, overview_note, blob_relpath, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(turn_id) DO UPDATE SET "
                    "rolled_back=excluded.rolled_back, "
                    "file_count=excluded.file_count, "
                    "overview_note=excluded.overview_note, "
                    "blob_relpath=excluded.blob_relpath, "
                    "created_at=excluded.created_at",
                    (
                        turn_id,
                        1 if diff_payload.get("rolled_back") else 0,
                        int(diff_payload.get("file_count") or 0),
                        str(diff_payload.get("overview_note") or ""),
                        rel,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return rel

    def get_turn_diff(self, turn_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM agent_turn_diffs WHERE turn_id = ?",
                    (turn_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        rel = str(row["blob_relpath"] or "")
        blob_path = self._blobs_dir / rel if rel else None
        payload: dict[str, Any] = {
            "turn_id": turn_id,
            "rolled_back": bool(row["rolled_back"]),
            "file_count": int(row["file_count"]),
            "overview_note": str(row["overview_note"] or ""),
            "files": [],
        }
        if blob_path is not None and blob_path.is_file():
            try:
                data = json.loads(blob_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    payload.update(data)
                    payload["turn_id"] = turn_id
            except (OSError, json.JSONDecodeError):
                pass
        return payload

    def get_previous_turn_user_rating(self, session_id: str) -> dict[str, Any] | None:
        """取本会话最近一次已提交评价，供下一轮 nl-patch 注入（无评价则 None）。"""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT r.score, r.label, r.comment, r.turn_id, "
                    "t.user_text, t.outcome, t.gate_passed "
                    "FROM turn_ratings r "
                    "JOIN agent_turns t ON t.id = r.turn_id "
                    "WHERE t.session_id = ? "
                    "ORDER BY t.turn_index DESC, r.updated_at DESC "
                    "LIMIT 1",
                    (session_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        user_text: str = str(row["user_text"] or "").strip()
        summary: str = user_text[:80] + ("…" if len(user_text) > 80 else "")
        return {
            "score": int(row["score"]),
            "label": str(row["label"] or ""),
            "comment": str(row["comment"] or ""),
            "rated_turn_id": str(row["turn_id"]),
            "rated_user_request_summary": summary,
            "rated_agent_outcome": str(row["outcome"] or ""),
            "gate_passed": bool(row["gate_passed"]),
        }


@lru_cache
def get_learning_store() -> LearningAnalyticsStore:
    settings: Settings = get_settings()
    root: Path = Path(settings.learning_analytics_dir)
    return LearningAnalyticsStore(root / "learning.db", root / "blobs")


def clear_learning_store_cache() -> None:
    get_learning_store.cache_clear()
