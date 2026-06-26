from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR
from app.models.session import SessionPhase, SessionRecord
from app.services.play_variants import resolve_play_variant
from app.services.tuning_mapper import merge_tuning


@lru_cache
def load_wizard_steps() -> list[dict[str, Any]]:
    path: Path = CONFIG_DIR / "wizard_steps.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("steps", []))


def get_step_def(step_id: str) -> dict[str, Any] | None:
    for step in load_wizard_steps():
        if step.get("id") == step_id:
            return step
    return None


def intent_step_ids() -> list[str]:
    return [s["id"] for s in load_wizard_steps() if s.get("phase") not in ("CREATE", "PLAY")]


def apply_wizard_step(record: SessionRecord, step_id: str, data: dict[str, Any]) -> SessionRecord:
    step: dict[str, Any] | None = get_step_def(step_id)
    if step is None:
        raise ValueError(f"Unknown wizard step: {step_id}")

    payload: dict[str, Any] = dict(record.payload)
    record.wizard_step = step_id

    if step_id == "S0":
        name: str = str(data.get("display_name", "")).strip()
        if not name:
            raise ValueError("display_name is required for S0")
        record.display_name = name
        payload["meta"] = payload.get("meta", {})
        payload["meta"]["display_name"] = name

    elif step_id == "S1":
        genre: str = str(data.get("genre", "")).strip()
        if not genre:
            raise ValueError("genre is required for S1")
        record.genre = genre
        payload["meta"] = payload.get("meta", {})
        payload["meta"]["genre"] = genre

    elif step_id == "S2":
        variant_id: str = str(data.get("play_variant_id", data.get("variant_id", ""))).strip()
        if not record.genre:
            raise ValueError("genre must be set before S2")
        if not variant_id:
            raise ValueError("play_variant_id is required for S2")
        resolved: dict[str, Any] = resolve_play_variant(record.genre, variant_id)
        record.play_variant_id = variant_id
        record.genre = str(resolved["resolved_genre"])
        payload["meta"] = payload.get("meta", {})
        payload["meta"]["play_variant"] = variant_id
        payload["meta"]["genre"] = record.genre
        payload["play_variant_resolution"] = resolved

    elif step_id == "S3":
        payload["theme"] = payload.get("theme", {})
        payload["theme"]["style_pack"] = data.get("style_pack", "default")
        payload["theme"]["mood_keywords"] = data.get("mood_keywords", [])

    elif step_id == "S4":
        payload["theme"] = payload.get("theme", {})
        payload["theme"]["character"] = data.get("character", {})

    elif step_id == "S5":
        payload["theme"] = payload.get("theme", {})
        payload["theme"]["props"] = data.get("props", [])

    elif step_id == "S6":
        feel_id: str = str(data.get("feel_id", "balanced"))
        payload["tuning"] = merge_tuning(payload.get("tuning"), feel_id, record.genre)

    elif step_id == "S7":
        skills: list[str] = list(data.get("enabled_skills", []))
        if len(skills) > 2:
            raise ValueError("At most 2 skills allowed")
        payload["tuning"] = payload.get("tuning", {})
        payload["tuning"]["enabled_skills"] = skills

    elif step_id == "R":
        payload["recap_confirmed"] = True

    elif step_id == "S8":
        record.phase = SessionPhase.CREATE
        payload["generate_started"] = True

    record.payload = payload
    steps: list[str] = intent_step_ids()
    if step_id in steps:
        record.wizard_index = steps.index(step_id)
    return record


def next_step_id(current: str) -> str | None:
    steps: list[str] = intent_step_ids()
    if current not in steps:
        return None
    idx: int = steps.index(current)
    if idx + 1 >= len(steps):
        return None
    return steps[idx + 1]


def build_recap(record: SessionRecord) -> dict[str, Any]:
    return {
        "display_name": record.display_name,
        "genre": record.genre,
        "play_variant_id": record.play_variant_id,
        "payload": record.payload,
    }
