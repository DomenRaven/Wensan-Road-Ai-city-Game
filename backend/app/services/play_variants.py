from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR


@lru_cache
def _load_play_variants() -> dict[str, Any]:
    path: Path = CONFIG_DIR / "play_variants.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_variants_for_genre(genre: str) -> list[dict[str, Any]]:
    data: dict[str, Any] = _load_play_variants()
    variants: dict[str, list[dict[str, Any]]] = data.get("variants", {})
    return variants.get(genre, [])


def resolve_play_variant(genre: str, variant_id: str) -> dict[str, Any]:
    for item in list_variants_for_genre(genre):
        if item.get("id") == variant_id:
            maps_to: dict[str, Any] = item.get("maps_to", {})
            resolved_genre: str = str(maps_to.get("genre", genre))
            return {
                "requested_genre": genre,
                "variant_id": variant_id,
                "label": item.get("label", variant_id),
                "redirect_hint": item.get("redirect_hint"),
                "resolved_genre": resolved_genre,
                "tuning_preset": maps_to.get("tuning_preset"),
                "redirected": resolved_genre != genre,
            }
    defaults: dict[str, Any] = _load_play_variants().get("default_for_genre", {})
    fallback: dict[str, Any] | None = defaults.get(genre)
    if fallback:
        return {
            "requested_genre": genre,
            "variant_id": fallback.get("id", "default"),
            "label": fallback.get("label", "默认"),
            "redirect_hint": None,
            "resolved_genre": genre,
            "tuning_preset": f"{genre}_default",
            "redirected": False,
        }
    return {
        "requested_genre": genre,
        "variant_id": variant_id,
        "label": variant_id,
        "redirect_hint": None,
        "resolved_genre": genre,
        "tuning_preset": f"{genre}_default",
        "redirected": False,
    }
