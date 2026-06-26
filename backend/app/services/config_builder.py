from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR
from app.services.tuning_mapper import apply_feel_overrides
from app.services.workspace_guard import assert_not_under_templates, assert_under_workspace


@lru_cache
def load_wizard_payload_mapping() -> dict[str, Any]:
    path: Path = CONFIG_DIR / "wizard_payload_mapping.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_valid_genres() -> set[str]:
    path: Path = CONFIG_DIR / "genre_registry.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return {str(g["slug"]) for g in data.get("genres", [])}


@lru_cache
def load_optional_skills_catalog() -> dict[str, list[str]]:
    path: Path = CONFIG_DIR / "optional_skills.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    catalog: dict[str, list[str]] = {}
    for genre, entries in data.get("catalog", {}).items():
        catalog[genre] = [str(e["id"]) for e in entries]
    return catalog


def trim_max_32(value: str) -> str:
    return value.strip()[:32]


def genre_slug_validate(value: str) -> str:
    slug: str = value.strip()
    valid: set[str] = load_valid_genres()
    if slug not in valid:
        raise ValueError(f"Invalid genre: {slug}")
    return slug


def set_path(config: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts: list[str] = dotted_path.split(".")
    current: dict[str, Any] = config
    for part in parts[:-1]:
        next_val: Any = current.get(part)
        if not isinstance(next_val, dict):
            next_val = {}
            current[part] = next_val
        current = next_val
    current[parts[-1]] = value


def get_path(config: dict[str, Any], dotted_path: str) -> Any:
    current: Any = config
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def merge_payload_into_config(
    config: dict[str, Any],
    payload: dict[str, Any],
    genre: str,
) -> dict[str, Any]:
    """Merge Session.payload into game_config per wizard_payload_mapping.json (B2)."""
    mapping_doc: dict[str, Any] = load_wizard_payload_mapping()
    merged: dict[str, Any] = json.loads(json.dumps(config))

    for entry in mapping_doc.get("mappings", []):
        payload_path: str = str(entry["payload_path"])
        transform: str | None = entry.get("transform")
        game_config_paths: list[str] = list(entry.get("game_config_paths", []))

        if transform == "tuning_mapper_merge":
            continue

        raw: Any = get_path(payload, payload_path)
        if raw is None:
            continue

        if transform == "trim_max_32":
            raw = trim_max_32(str(raw))
        elif transform == "genre_slug_validate":
            raw = genre_slug_validate(str(raw))

        for target_path in game_config_paths:
            set_path(merged, target_path, raw)

    meta: dict[str, Any] = merged.setdefault("meta", {})
    meta["genre"] = genre
    if payload.get("meta", {}).get("display_name"):
        name: str = trim_max_32(str(payload["meta"]["display_name"]))
        meta["display_name"] = name
        merged.setdefault("theme", {})["title"] = name

    theme_payload: dict[str, Any] = payload.get("theme", {})
    theme: dict[str, Any] = merged.setdefault("theme", {})
    if theme_payload.get("style_pack") is not None:
        theme["style_pack"] = theme_payload["style_pack"]
    if theme_payload.get("mood_keywords") is not None:
        theme["mood_keywords"] = theme_payload["mood_keywords"]
    if theme_payload.get("character") is not None:
        theme["character"] = theme_payload["character"]
        character: dict[str, Any] = theme_payload["character"]
        color: str | None = character.get("color")
        if isinstance(color, str) and color.startswith("#"):
            theme["background_color"] = color
    if theme_payload.get("props") is not None:
        theme["props"] = theme_payload["props"]

    tuning_payload: dict[str, Any] = payload.get("tuning", {})
    feel_id: str = str(tuning_payload.get("feel_id", "balanced"))
    skills: list[str] = list(tuning_payload.get("enabled_skills", []))
    if len(skills) > 2:
        raise ValueError("At most 2 skills allowed")
    catalog: dict[str, list[str]] = load_optional_skills_catalog()
    allowed: set[str] = set(catalog.get(genre, []))
    for skill_id in skills:
        if allowed and skill_id not in allowed:
            raise ValueError(f"Unknown skill for {genre}: {skill_id}")

    tuning: dict[str, Any] = merged.setdefault("tuning", {})
    tuning["enabled_skills"] = skills

    return merged


def build_game_config(
    session_id: str,
    payload: dict[str, Any],
    genre: str,
    workspace_root: Path,
    templates_dir: Path,
) -> Path:
    """Full B2+B3 pipeline: merge payload + feel overrides + write config."""
    config_path: Path = workspace_root / "config" / "game_config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"workspace config missing: {config_path}")

    base_template_path: Path = templates_dir / genre / "config" / "game_config.json"
    base_config: dict[str, Any] = json.loads(base_template_path.read_text(encoding="utf-8"))
    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))

    merged: dict[str, Any] = merge_payload_into_config(config, payload, genre)
    merged["meta"]["session_id"] = session_id

    feel_id: str = str(payload.get("tuning", {}).get("feel_id", "balanced"))
    merged = apply_feel_overrides(merged, base_config, genre, feel_id)

    assert_under_workspace(config_path, workspace_root.resolve())
    assert_not_under_templates(config_path, templates_dir.resolve())

    config_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path.resolve()
