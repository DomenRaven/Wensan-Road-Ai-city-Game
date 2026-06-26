from __future__ import annotations

import uuid
from pathlib import Path

from app.config import Settings
from app.services.creative.analyzer import analyze_preset_only
from app.services.creative.code_map import build_code_map_for_workspace
from app.services.edu_workspace import GENRE_HOOKS, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
EDU_DIR: Path = REPO_ROOT / "templates" / "_edu"

EXPECTED_SLUGS: tuple[str, ...] = (
    "platformer",
    "shmup",
    "survivor",
    "pingpong",
    "fighting",
    "parkour",
    "racing",
)

GENRE_DEFAULT_ANSWERS: dict[str, dict[str, str]] = {
    "shmup": {
        "q_speed": "default",
        "q_fire_rate": "default",
        "q_spawn": "default",
    },
    "survivor": {
        "q_speed": "default",
        "q_spawn": "default",
        "q_duration": "default",
    },
    "pingpong": {
        "q_ball": "default",
        "q_win": "default",
        "q_ai": "default",
    },
}


def test_genre_hooks_has_seven_slugs_and_edu_files_exist() -> None:
    assert set(GENRE_HOOKS.keys()) == set(EXPECTED_SLUGS)
    bridge: Path = EDU_DIR / "edu_action_bridge.gd"
    assert bridge.is_file(), f"missing {bridge}"
    for slug, hooks_filename in GENRE_HOOKS.items():
        hooks_path: Path = EDU_DIR / hooks_filename
        assert hooks_path.is_file(), f"missing _edu hooks for {slug}: {hooks_path}"


def _assert_edu_workspace(workspace_root: Path, genre: str) -> None:
    hooks_filename: str = GENRE_HOOKS[genre]
    assert (workspace_root / "core" / "edu_action_bridge.gd").is_file()
    assert (workspace_root / "core" / hooks_filename).is_file()
    project_text: str = (workspace_root / "project.godot").read_text(encoding="utf-8")
    assert "EduActionBridge=" in project_text
    main_text: str = (workspace_root / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'name="EduHooks"' in main_text


def test_generate_pipeline_edu_bridge_for_p1_sample_genres() -> None:
    settings = Settings()
    for genre, answers in GENRE_DEFAULT_ANSWERS.items():
        session_id: str = str(uuid.uuid4())
        workspace_root = copy_template_to_workspace(
            settings.templates_dir,
            settings.workspace_dir,
            genre,
            session_id,
        )
        analyze = analyze_preset_only(genre, answers, settings.templates_dir)
        resolutions = list(analyze.get("resolutions", []))
        assert resolutions

        edu_applied: bool = apply_edu_workspace_patch(
            workspace_root,
            genre,
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert edu_applied is True
        build_code_map_for_workspace(workspace_root, genre, resolutions)
        _assert_edu_workspace(workspace_root, genre)
