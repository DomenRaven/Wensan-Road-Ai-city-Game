#!/usr/bin/env python3
"""为 workspace 目录下已有会话补打触控 overlay 注入（B5/B7 之后代码升级时用）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import GENRE_HOOKS, apply_edu_workspace_patch

TOUCH_GENRES: frozenset[str] = frozenset(
    {"fighting", "platformer", "parkour", "survivor", "pingpong", "racing"}
)


def main() -> int:
    settings = Settings()
    workspace_root_dir: Path = settings.workspace_dir.resolve()
    if not workspace_root_dir.is_dir():
        print("workspace 目录不存在")
        return 1

    repaired: int = 0
    for child in sorted(workspace_root_dir.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "project.godot").is_file():
            continue
        config_path: Path = child / "config" / "game_config.json"
        genre: str = ""
        if config_path.is_file():
            import json

            try:
                cfg: dict[str, object] = json.loads(config_path.read_text(encoding="utf-8"))
                meta: dict[str, object] = cfg.get("meta", {})  # type: ignore[assignment]
                genre = str(meta.get("genre", "")).strip()
            except (json.JSONDecodeError, OSError):
                genre = ""
        if genre not in GENRE_HOOKS:
            continue
        ok: bool = apply_edu_workspace_patch(
            child,
            genre,
            settings.templates_dir,
            settings.workspace_dir,
        )
        touch_hint: str = "touch" if genre in TOUCH_GENRES else "hooks"
        main_text: str = (child / "scenes" / "main.tscn").read_text(encoding="utf-8")
        has_touch: bool = any(
            marker in main_text
            for marker in (
                "FightingTouch",
                "PlatformerTouch",
                "ParkourTouch",
                "SurvivorTouch",
                "PingpongTouch",
                "RacingTouch",
            )
        )
        print(f"  [{genre}] {child.name} applied={ok} {touch_hint}={'yes' if has_touch else 'no'}")
        if ok:
            repaired += 1

    print(f"OK: repaired {repaired} workspace(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
