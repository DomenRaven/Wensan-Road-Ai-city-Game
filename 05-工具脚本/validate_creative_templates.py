#!/usr/bin/env python3
"""Validate creative_templates tuning_path against template game_config.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREATIVE_DIR = REPO_ROOT / "config" / "creative_templates"
ANCHORS_DIR = REPO_ROOT / "config" / "code_anchors"
TEMPLATES_DIR = REPO_ROOT / "templates"


def get_nested(data: dict, dotted_path: str) -> object | None:
    current: object = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_template(path: Path) -> list[str]:
    errors: list[str] = []
    schema: dict = load_json(path)
    genre: str = str(schema.get("genre", ""))
    if not genre:
        errors.append(f"{path.name}: missing genre")
        return errors

    game_config_path = TEMPLATES_DIR / genre / "config" / "game_config.json"
    if not game_config_path.is_file():
        errors.append(f"{path.name}: no game_config at {game_config_path}")
        return errors

    game_config: dict = load_json(game_config_path)
    anchors_path = ANCHORS_DIR / f"{genre}.json"
    anchors: set[str] = set()
    if anchors_path.is_file():
        anchors_doc: dict = load_json(anchors_path)
        anchors = set((anchors_doc.get("anchors") or {}).keys())

    for question in schema.get("questions", []):
        qid: str = str(question.get("id", "?"))
        widget: str = str(question.get("widget", ""))

        if widget == "skill_pick":
            tuning_path = str(question.get("tuning_path", "tuning.enabled_skills"))
            if get_nested(game_config, tuning_path) is None:
                errors.append(
                    f"{path.name} {qid}: tuning_path '{tuning_path}' not in game_config"
                )
            anchor_id = str(question.get("code_anchor_id", ""))
            if anchor_id and anchor_id not in anchors:
                errors.append(f"{path.name} {qid}: unknown code_anchor_id '{anchor_id}'")
            for skill_id in question.get("skill_ids", []):
                skills = get_nested(game_config, "tuning.skills")
                if not isinstance(skills, dict) or skill_id not in skills:
                    errors.append(f"{path.name} {qid}: skill '{skill_id}' not in tuning.skills")
            continue

        for option in question.get("options", []):
            tuning_path = str(option.get("tuning_path", ""))
            if not tuning_path:
                errors.append(f"{path.name} {qid}: option missing tuning_path")
                continue
            if get_nested(game_config, tuning_path) is None:
                errors.append(
                    f"{path.name} {qid} option {option.get('id')}: "
                    f"tuning_path '{tuning_path}' not in game_config"
                )
            anchor_id = str(option.get("code_anchor_id", ""))
            if anchor_id and anchor_id not in anchors:
                errors.append(
                    f"{path.name} {qid} option {option.get('id')}: "
                    f"unknown code_anchor_id '{anchor_id}'"
                )

    return errors


def main() -> int:
    if not CREATIVE_DIR.is_dir():
        print(f"ERROR: {CREATIVE_DIR} not found", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    templates = sorted(CREATIVE_DIR.glob("*.json"))
    if not templates:
        print("WARN: no creative_templates found")
        return 0

    for path in templates:
        all_errors.extend(validate_template(path))

    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(templates)} creative template(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
