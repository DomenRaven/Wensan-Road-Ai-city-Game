from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import CONFIG_DIR
from app.models.session import SessionRecord
from app.services.play_variants import list_variants_for_genre, resolve_play_variant
from app.services.wizard import apply_wizard_step, build_recap, load_wizard_steps, next_step_id

router = APIRouter(tags=["wizard"])


class WizardStepRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class WizardStepResponse(BaseModel):
    session: SessionRecord
    next_step: str | None = None
    recap: dict[str, Any] | None = None


@router.get("/wizard/steps")
def get_wizard_steps() -> dict[str, Any]:
    path = CONFIG_DIR / "wizard_steps.json"
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/genres")
def get_genres() -> dict[str, Any]:
    path = CONFIG_DIR / "genre_registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/genres/{genre}/play-variants")
def get_play_variants(genre: str) -> dict[str, Any]:
    return {"genre": genre, "variants": list_variants_for_genre(genre)}


@router.post("/play-variants/resolve")
def resolve_variant(body: dict[str, str]) -> dict[str, Any]:
    genre: str = body.get("genre", "")
    variant_id: str = body.get("variant_id", "")
    if not genre or not variant_id:
        raise HTTPException(status_code=400, detail="genre and variant_id required")
    return resolve_play_variant(genre, variant_id)


@router.post("/sessions/{session_id}/wizard/{step_id}", response_model=WizardStepResponse)
def submit_wizard_step(
    session_id: str,
    step_id: str,
    body: WizardStepRequest,
    request: Request,
) -> WizardStepResponse:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        record = apply_wizard_step(record, step_id, body.data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.save(record)
    recap: dict[str, Any] | None = build_recap(record) if step_id == "R" else None
    return WizardStepResponse(
        session=record,
        next_step=next_step_id(step_id),
        recap=recap,
    )


@router.get("/sessions/{session_id}/recap")
def get_recap(session_id: str, request: Request) -> dict[str, Any]:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return build_recap(record)


@router.post("/sessions/{session_id}/recap")
def confirm_recap(session_id: str, request: Request) -> dict[str, Any]:
    """Confirm ★R recap — required before POST /generate."""
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload: dict[str, Any] = dict(record.payload)
    payload["recap_confirmed"] = True
    record.payload = payload
    record.wizard_step = "R"
    store.save(record)
    return build_recap(record)
