from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR

FEEL_PRESETS: dict[str, dict[str, Any]] = {
    "easy": {
        "player_speed_scale": 1.0,
        "enemy_speed_scale": 0.85,
        "damage_taken_scale": 0.8,
        "label": "轻松好玩",
    },
    "balanced": {
        "player_speed_scale": 1.0,
        "enemy_speed_scale": 1.0,
        "damage_taken_scale": 1.0,
        "label": "刚刚好",
    },
    "challenge": {
        "player_speed_scale": 1.05,
        "enemy_speed_scale": 1.15,
        "damage_taken_scale": 1.2,
        "label": "有点挑战",
    },
}

DEFAULT_CLAMP_PERCENT: float = 30.0


@lru_cache
def load_feel_overrides() -> dict[str, Any]:
    path: Path = CONFIG_DIR / "tuning_feel_overrides.json"
    return json.loads(path.read_text(encoding="utf-8"))


def map_feel_card(feel_id: str, genre: str | None = None) -> dict[str, Any]:
    preset: dict[str, Any] = FEEL_PRESETS.get(feel_id, FEEL_PRESETS["balanced"]).copy()
    preset["feel_id"] = feel_id
    if genre:
        preset["genre"] = genre
    return preset


def merge_tuning(base: dict[str, Any] | None, feel_id: str, genre: str | None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base or {})
    merged.update(map_feel_card(feel_id, genre))
    return merged


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def set_nested(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts: list[str] = dotted_path.split(".")
    current: dict[str, Any] = data
    for part in parts[:-1]:
        next_val: Any = current.get(part)
        if not isinstance(next_val, dict):
            next_val = {}
            current[part] = next_val
        current = next_val
    current[parts[-1]] = value


def clamp_value(base_val: float, new_val: float, clamp_percent: float) -> float:
    if base_val == 0:
        return new_val
    ratio: float = abs(new_val / base_val)
    low: float = 1.0 - clamp_percent / 100.0
    high: float = 1.0 + clamp_percent / 100.0
    if ratio < low:
        return base_val * low
    if ratio > high:
        return base_val * high
    return new_val


def apply_feel_overrides(
    config: dict[str, Any],
    base_config: dict[str, Any],
    genre: str,
    feel_id: str,
    clamp_percent: float | None = None,
) -> dict[str, Any]:
    """Apply genre feel_id multipliers to tuning fields with ±clamp_percent (B3)."""
    overrides_doc: dict[str, Any] = load_feel_overrides()
    percent: float = clamp_percent if clamp_percent is not None else float(
        overrides_doc.get("clamp_percent", DEFAULT_CLAMP_PERCENT)
    )
    genre_overrides: dict[str, Any] = overrides_doc.get("genres", {}).get(genre, {})
    feel_fields: dict[str, float] = genre_overrides.get(feel_id, genre_overrides.get("balanced", {}))
    if not feel_fields:
        return config

    tuning: dict[str, Any] = dict(config.get("tuning", {}))
    base_tuning: dict[str, Any] = base_config.get("tuning", {})

    for dotted_path, scale in feel_fields.items():
        base_val: Any = get_nested(base_tuning, dotted_path)
        if not isinstance(base_val, (int, float)):
            continue
        base_float: float = float(base_val)
        scaled: float = base_float * float(scale)
        clamped: float = clamp_value(base_float, scaled, percent)
        if isinstance(base_val, int):
            set_nested(tuning, dotted_path, int(round(clamped)))
        else:
            set_nested(tuning, dotted_path, clamped)

    config["tuning"] = tuning
    return config


def tuning_delta_direction(
    genre: str,
    feel_id: str,
    field: str,
    balanced_val: float,
    feel_val: float,
) -> str:
    """Return 'harder_or_faster_vs_balanced' if feel differs from balanced in expected direction."""
    overrides_doc: dict[str, Any] = load_feel_overrides()
    genre_overrides: dict[str, Any] = overrides_doc.get("genres", {}).get(genre, {})
    balanced_scale: float = float(genre_overrides.get("balanced", {}).get(field, 1.0))
    feel_scale: float = float(genre_overrides.get(feel_id, {}).get(field, 1.0))
    if feel_scale != balanced_scale:
        return "harder_or_faster_vs_balanced" if feel_val != balanced_val else "unchanged"
    return "unchanged"
