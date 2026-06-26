from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Literal

from app.config import Settings
from app.models.session import SessionPhase, SessionRecord

StoreBackend = Literal["redis", "memory"]


class SessionStore(ABC):
    @abstractmethod
    def ping(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def count_active(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def create(self) -> SessionRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get(self, session_id: str) -> SessionRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, record: SessionRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_active(self) -> list[SessionRecord]:
        raise NotImplementedError


class MemorySessionStore(SessionStore):
    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._sessions: dict[str, SessionRecord] = {}

    def ping(self) -> bool:
        return True

    def count_active(self) -> int:
        return len(self._sessions)

    def create(self) -> SessionRecord | None:
        if self.count_active() >= self._settings.max_sessions:
            return None
        now: float = time.time()
        record: SessionRecord = SessionRecord(
            session_id=str(uuid.uuid4()),
            phase=SessionPhase.INTENT,
            wizard_step="S0",
            wizard_index=0,
            created_at=now,
            updated_at=now,
        )
        self._sessions[record.session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def save(self, record: SessionRecord) -> None:
        record.updated_at = time.time()
        self._sessions[record.session_id] = record

    def delete(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        return True

    def list_active(self) -> list[SessionRecord]:
        return list(self._sessions.values())


class RedisSessionStore(SessionStore):
    INDEX_KEY: str = "gameforge:sessions:index"

    def __init__(self, settings: Settings) -> None:
        import redis

        self._settings: Settings = settings
        self._client: redis.Redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    def _session_key(self, session_id: str) -> str:
        return f"gameforge:session:{session_id}"

    def ping(self) -> bool:
        return bool(self._client.ping())

    def count_active(self) -> int:
        return int(self._client.scard(self.INDEX_KEY))

    def create(self) -> SessionRecord | None:
        if self.count_active() >= self._settings.max_sessions:
            return None
        now: float = time.time()
        record: SessionRecord = SessionRecord(
            session_id=str(uuid.uuid4()),
            phase=SessionPhase.INTENT,
            wizard_step="S0",
            wizard_index=0,
            created_at=now,
            updated_at=now,
        )
        payload: str = record.model_dump_json()
        pipe = self._client.pipeline()
        pipe.set(self._session_key(record.session_id), payload, ex=self._settings.session_ttl_sec)
        pipe.sadd(self.INDEX_KEY, record.session_id)
        pipe.execute()
        return record

    def get(self, session_id: str) -> SessionRecord | None:
        raw: str | None = self._client.get(self._session_key(session_id))
        if raw is None:
            return None
        return SessionRecord.model_validate_json(raw)

    def save(self, record: SessionRecord) -> None:
        record.updated_at = time.time()
        self._client.set(
            self._session_key(record.session_id),
            record.model_dump_json(),
            ex=self._settings.session_ttl_sec,
        )

    def delete(self, session_id: str) -> bool:
        pipe = self._client.pipeline()
        pipe.delete(self._session_key(session_id))
        pipe.srem(self.INDEX_KEY, session_id)
        deleted, _ = pipe.execute()
        return bool(deleted)

    def list_active(self) -> list[SessionRecord]:
        ids: list[str] = list(self._client.smembers(self.INDEX_KEY))
        sessions: list[SessionRecord] = []
        for session_id in ids:
            record: SessionRecord | None = self.get(session_id)
            if record is not None:
                sessions.append(record)
        return sessions


def create_session_store(settings: Settings) -> tuple[SessionStore, StoreBackend]:
    try:
        store: RedisSessionStore = RedisSessionStore(settings)
        if store.ping():
            return store, "redis"
    except Exception:
        pass
    if not settings.allow_memory_fallback:
        raise RuntimeError("Redis unavailable and memory fallback disabled")
    return MemorySessionStore(settings), "memory"
