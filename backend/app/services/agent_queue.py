"""S4 · Agent 并发帽与单会话互斥（进程内；多进程请再叠 Redis）。"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


class AgentQueueError(Exception):
    """排队/占槽失败。"""

    def __init__(self, code: str, message: str, *, queue_size: int = 0) -> None:
        super().__init__(message)
        self.code: str = code
        self.message: str = message
        self.queue_size: int = queue_size


@dataclass
class AgentQueueSnapshot:
    active: int
    max_concurrent: int
    waiting: int


class AgentQueueGate:
    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._active: dict[str, float] = {}
        self._user_to_session: dict[str, str] = {}
        self._waiters: int = 0

    def snapshot(self, max_concurrent: int) -> AgentQueueSnapshot:
        with self._cv:
            return AgentQueueSnapshot(
                active=len(self._active),
                max_concurrent=max(1, int(max_concurrent)),
                waiting=self._waiters,
            )

    def _can_enter(
        self,
        session_id: str,
        user_id: str | None,
        max_concurrent: int,
    ) -> str | None:
        """返回 None 表示可进入；否则返回错误码。"""
        if session_id in self._active:
            return "session_busy"
        if user_id and user_id in self._user_to_session:
            other = self._user_to_session[user_id]
            if other != session_id:
                return "user_busy"
        if len(self._active) >= max(1, int(max_concurrent)):
            return "full"
        return None

    @contextmanager
    def acquire(
        self,
        session_id: str,
        *,
        user_id: str | None = None,
        max_concurrent: int = 6,
        wait_sec: float = 90.0,
    ) -> Iterator[None]:
        sid = session_id.strip()
        uid = (user_id or "").strip() or None
        cap = max(1, int(max_concurrent))
        deadline = time.monotonic() + max(0.0, float(wait_sec))
        entered = False
        with self._cv:
            self._waiters += 1
            try:
                while True:
                    reason = self._can_enter(sid, uid, cap)
                    if reason is None:
                        self._active[sid] = time.time()
                        if uid:
                            self._user_to_session[uid] = sid
                        entered = True
                        break
                    if reason == "session_busy":
                        raise AgentQueueError(
                            "session_busy",
                            "你已有一轮改游戏正在进行，请稍候完成后再发",
                            queue_size=self._waiters,
                        )
                    if reason == "user_busy":
                        raise AgentQueueError(
                            "user_busy",
                            "同一账号同时只能进行一轮改游戏，请稍候",
                            queue_size=self._waiters,
                        )
                    # full → 排队等待
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AgentQueueError(
                            "agent_queue_full",
                            "当前同时改游戏的人数已满，请稍后再试",
                            queue_size=self._waiters,
                        )
                    self._cv.wait(timeout=min(1.0, remaining))
            finally:
                self._waiters = max(0, self._waiters - 1)
        try:
            yield
        finally:
            with self._cv:
                self._active.pop(sid, None)
                if uid and self._user_to_session.get(uid) == sid:
                    self._user_to_session.pop(uid, None)
                self._cv.notify_all()


_GATE = AgentQueueGate()


def get_agent_queue() -> AgentQueueGate:
    return _GATE


def reset_agent_queue_for_tests() -> None:
    """单测隔离：清空占槽。"""
    gate = get_agent_queue()
    with gate._cv:
        gate._active.clear()
        gate._user_to_session.clear()
        gate._waiters = 0
        gate._cv.notify_all()
