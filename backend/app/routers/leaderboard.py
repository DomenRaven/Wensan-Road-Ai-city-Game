from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services.leaderboard_daily import (
    DEFAULT_TIMEZONE,
    LEADERBOARD_GENRES,
    append_entry,
    get_daily_top,
    resolve_date,
)

router = APIRouter(tags=["leaderboard"])

LeaderboardGenre = Literal[
    "platformer",
    "shmup",
    "survivor",
    "pingpong",
    "fighting",
    "parkour",
    "racing",
]


class LeaderboardEntryRequest(BaseModel):
    session_id: str | None = None
    creator_name: str = ""
    display_name: str = ""
    score: int = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)
    survival_ms: int = Field(default=0, ge=0)
    level_reached: int = Field(default=0, ge=0)
    metric: str = "score"


class LeaderboardEntryResponse(BaseModel):
    ok: bool = True
    entry: dict[str, Any]


class LeaderboardDailyResponse(BaseModel):
    ok: bool = True
    genre: str
    date: str
    timezone: str
    entries: list[dict[str, Any]]


def _data_dir(request: Request) -> Path:
    settings = request.app.state.settings
    root: Path = Path(__file__).resolve().parents[2] / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _timezone(request: Request) -> str:
    return DEFAULT_TIMEZONE


@router.post("/leaderboard/{genre}/entries", response_model=LeaderboardEntryResponse)
def post_leaderboard_entry(
    genre: LeaderboardGenre,
    body: LeaderboardEntryRequest,
    request: Request,
) -> LeaderboardEntryResponse:
    if genre not in LEADERBOARD_GENRES:
        raise HTTPException(status_code=400, detail="unsupported genre")

    default_metric: str = "score"
    if genre == "platformer":
        default_metric = "level_reached"
    elif genre == "survivor":
        default_metric = "survival_ms"
    elif genre == "parkour":
        default_metric = "distance_m"
    elif genre == "racing":
        default_metric = "lap_count"
    elif genre == "fighting":
        default_metric = "win"
    metric: str = body.metric.strip() or default_metric
    try:
        entry: dict[str, Any] = append_entry(
            _data_dir(request),
            genre,
            creator_name=body.creator_name,
            display_name=body.display_name,
            score=body.score,
            elapsed_ms=body.elapsed_ms,
            survival_ms=body.survival_ms,
            level_reached=body.level_reached,
            metric=metric,
            session_id=body.session_id,
            timezone=_timezone(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LeaderboardEntryResponse(entry=entry)


@router.get("/leaderboard/{genre}/daily", response_model=LeaderboardDailyResponse)
def get_leaderboard_daily(
    genre: LeaderboardGenre,
    request: Request,
    date_param: str = Query("today", alias="date"),
    limit: int = Query(10, ge=1, le=50),
) -> LeaderboardDailyResponse:
    if genre not in LEADERBOARD_GENRES:
        raise HTTPException(status_code=400, detail="unsupported genre")

    timezone: str = _timezone(request)
    try:
        day: date = resolve_date(date_param, timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date") from exc

    entries: list[dict[str, Any]] = get_daily_top(_data_dir(request), genre, day=day, limit=limit)
    return LeaderboardDailyResponse(
        genre=genre,
        date=day.isoformat(),
        timezone=timezone,
        entries=entries,
    )
