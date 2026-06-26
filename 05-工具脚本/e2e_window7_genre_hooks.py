#!/usr/bin/env python3
"""窗7 抽测：直接调用 generate 核心服务，绕过 bootstrap 孤儿清理."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.services.creative.analyzer import analyze_preset_only  # noqa: E402
from app.services.creative.code_map import build_code_map_for_workspace  # noqa: E402
from app.services.edu_workspace import GENRE_HOOKS, apply_edu_workspace_patch  # noqa: E402
from app.services.workspace import copy_template_to_workspace  # noqa: E402

CASES: list[tuple[str, dict[str, str]]] = [
    ("shmup", {"q_speed": "default", "q_fire_rate": "default", "q_spawn": "default"}),
    ("survivor", {"q_speed": "default", "q_spawn": "default", "q_duration": "default"}),
    ("pingpong", {"q_ball": "default", "q_win": "default", "q_ai": "default"}),
]


def assert_edu_workspace(workspace_root: Path, genre: str) -> None:
    hooks_filename: str = GENRE_HOOKS[genre]
    assert (workspace_root / "core" / "edu_action_bridge.gd").is_file()
    assert (workspace_root / "core" / hooks_filename).is_file()
    assert "EduActionBridge=" in (workspace_root / "project.godot").read_text(encoding="utf-8")
    assert 'name="EduHooks"' in (workspace_root / "scenes" / "main.tscn").read_text(encoding="utf-8")


def main() -> int:
    settings = Settings()
    results: list[dict[str, str]] = []

    for genre, answers in CASES:
        session_id: str = str(uuid.uuid4())
        workspace_root = copy_template_to_workspace(
            settings.templates_dir,
            settings.workspace_dir,
            genre,
            session_id,
        )
        analyze = analyze_preset_only(genre, answers, settings.templates_dir)
        resolutions = list(analyze.get("resolutions", []))
        if not resolutions:
            print(f"FAIL {genre}: no resolutions")
            return 1

        edu_applied: bool = apply_edu_workspace_patch(
            workspace_root,
            genre,
            settings.templates_dir,
            settings.workspace_dir,
        )
        if not edu_applied:
            print(f"FAIL {genre}: edu_bridge not applied")
            return 1

        build_code_map_for_workspace(workspace_root, genre, resolutions)
        assert_edu_workspace(workspace_root, genre)

        print(
            f"OK {genre}: session_id={session_id} "
            f"workspace={workspace_root} edu_bridge_applied={edu_applied}"
        )
        results.append(
            {
                "genre": genre,
                "session_id": session_id,
                "workspace_path": str(workspace_root),
                "edu_bridge_applied": str(edu_applied),
            }
        )

    print("\n=== WINDOW7 SAMPLE RESULTS ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
