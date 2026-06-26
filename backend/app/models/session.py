from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from typing import Any

from pydantic import BaseModel, Field


class SessionPhase(StrEnum):
    IDLE = "IDLE"
    INTENT = "INTENT"
    CREATE = "CREATE"
    PLAY = "PLAY"
    DONE = "DONE"
    RESET = "RESET"


class SessionRecord(BaseModel):
    session_id: str
    phase: SessionPhase = SessionPhase.INTENT
    wizard_step: str = "S0"
    wizard_index: int = 0
    display_name: str = ""
    genre: str | None = None
    play_variant_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


class SessionCreateResponse(BaseModel):
    session_id: str
    phase: SessionPhase
    wizard_step: str
    queue_position: int = 0


class SessionListResponse(BaseModel):
    active_count: int
    max_sessions: int
    sessions: list[SessionRecord]
