#!/usr/bin/env python3
"""RECIPE-B · cross-check creative_templates vs code_anchors vs game_config."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREATIVE_DIR = ROOT / "config" / "creative_templates"
ANCHORS_DIR = ROOT / "config" / "code_anchors"
TEMPLATES_DIR = ROOT / "templates"


def get_nested(data: dict, dotted: str) -> object | None:
    current: object = data
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def main() -> int:
    errors: list[str] = []
    for tp in sorted(CREATIVE_DIR.glob("*.json")):
        schema: dict = json.loads(tp.read_text(encoding="utf-8"))
        genre: str = str(schema.get("genre", ""))
        gc_path = TEMPLATES_DIR / genre / "config" / "game_config.json"
        if not gc_path.is_file():
            errors.append(f"{genre}: missing {gc_path}")
            continue
        game_config: dict = json.loads(gc_path.read_text(encoding="utf-8"))
        anchors_doc: dict = json.loads(
            (ANCHORS_DIR / f"{genre}.json").read_text(encoding="utf-8")
        )
        anchors: set[str] = set((anchors_doc.get("anchors") or {}).keys())
        for question in schema.get("questions", []):
            qid: str = str(question.get("id", "?"))
            if question.get("widget") == "skill_pick":
                errors.append(f"{genre}: still has skill_pick ({qid})")
            for option in question.get("options", []):
                path: str = str(option.get("tuning_path", ""))
                if path and get_nested(game_config, path) is None:
                    errors.append(f"{genre}/{qid}: tuning_path missing in game_config: {path}")
                aid: str = str(option.get("code_anchor_id", ""))
                if aid and aid not in anchors:
                    errors.append(f"{genre}/{qid}: unknown code_anchor_id: {aid}")
    if errors:
        print("RECIPE ALIGNMENT FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: creative_templates <-> code_anchors <-> game_config aligned")
    for tp in sorted(CREATIVE_DIR.glob("*.json")):
        d: dict = json.loads(tp.read_text(encoding="utf-8"))
        print(f"  {d['genre']}: {len(d.get('questions', []))} questions, no skill_pick")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
