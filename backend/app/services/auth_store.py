"""教学账号与 Token · SQLite（与学情库同目录，供 W2 复用）。"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

UserRole = Literal["student", "admin"]


@dataclass(frozen=True)
class AuthUser:
    id: str
    username: str
    nickname: str
    role: UserRole
    class_label: str
    created_at: float


class AuthStore:
    """线程安全的用户 / Token 存储（sqlite3）。"""

    def __init__(self, db_path: Path) -> None:
        self._db_path: Path = db_path
        self._lock = threading.RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
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
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        password_hash TEXT NOT NULL,
                        nickname TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'student',
                        class_label TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS auth_tokens (
                        token TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_auth_tokens_user
                        ON auth_tokens(user_id);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def get_by_username(self, username: str) -> AuthUser | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT id, username, nickname, role, class_label, created_at "
                    "FROM users WHERE username = ? COLLATE NOCASE",
                    (username.strip(),),
                ).fetchone()
            finally:
                conn.close()
        return self._row_to_user(row)

    def get_by_id(self, user_id: str) -> AuthUser | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT id, username, nickname, role, class_label, created_at "
                    "FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            finally:
                conn.close()
        return self._row_to_user(row)

    def get_password_hash(self, username: str) -> str | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ? COLLATE NOCASE",
                    (username.strip(),),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        return str(row["password_hash"])

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        nickname: str,
        role: UserRole = "student",
        class_label: str = "",
    ) -> AuthUser:
        user_id: str = str(uuid.uuid4())
        now: float = time.time()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO users "
                    "(id, username, password_hash, nickname, role, class_label, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        username.strip(),
                        password_hash,
                        nickname.strip(),
                        role,
                        class_label.strip(),
                        now,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("username already exists") from exc
            finally:
                conn.close()
        return AuthUser(
            id=user_id,
            username=username.strip(),
            nickname=nickname.strip(),
            role=role,
            class_label=class_label.strip(),
            created_at=now,
        )

    def issue_token(self, user_id: str, ttl_sec: int) -> str:
        import secrets

        token: str = secrets.token_urlsafe(32)
        now: float = time.time()
        expires_at: float = now + max(300, ttl_sec)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO auth_tokens (token, user_id, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?)",
                    (token, user_id, now, expires_at),
                )
                conn.commit()
            finally:
                conn.close()
        return token

    def resolve_token(self, token: str) -> AuthUser | None:
        raw: str = token.strip()
        if not raw:
            return None
        now: float = time.time()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT t.user_id, t.expires_at, "
                    "u.username, u.nickname, u.role, u.class_label, u.created_at "
                    "FROM auth_tokens t JOIN users u ON u.id = t.user_id "
                    "WHERE t.token = ?",
                    (raw,),
                ).fetchone()
                if row is None:
                    return None
                if float(row["expires_at"]) < now:
                    conn.execute("DELETE FROM auth_tokens WHERE token = ?", (raw,))
                    conn.commit()
                    return None
                return AuthUser(
                    id=str(row["user_id"]),
                    username=str(row["username"]),
                    nickname=str(row["nickname"]),
                    role=str(row["role"]),  # type: ignore[arg-type]
                    class_label=str(row["class_label"] or ""),
                    created_at=float(row["created_at"]),
                )
            finally:
                conn.close()

    def revoke_token(self, token: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token.strip(),))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def ensure_admin(
        self,
        *,
        username: str,
        password_hash: str,
        nickname: str = "管理员",
    ) -> AuthUser | None:
        """若用户名不存在则创建 admin；已存在则不改密。"""
        existing: AuthUser | None = self.get_by_username(username)
        if existing is not None:
            return existing
        return self.create_user(
            username=username,
            password_hash=password_hash,
            nickname=nickname,
            role="admin",
        )

    @staticmethod
    def _row_to_user(row: sqlite3.Row | None) -> AuthUser | None:
        if row is None:
            return None
        return AuthUser(
            id=str(row["id"]),
            username=str(row["username"]),
            nickname=str(row["nickname"]),
            role=str(row["role"]),  # type: ignore[arg-type]
            class_label=str(row["class_label"] or ""),
            created_at=float(row["created_at"]),
        )
