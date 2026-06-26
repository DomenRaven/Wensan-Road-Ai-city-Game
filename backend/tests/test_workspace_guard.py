from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from app.config import Settings
from app.services.config_builder import build_game_config
from app.services.workspace_guard import (
    WorkspaceGuardError,
    cleanup_orphan_workspaces,
    copy_template_to_workspace,
    remove_workspace,
    validate_session_id,
    validate_template_genre,
)


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates: Path = tmp_path / "templates"
    workspace: Path = tmp_path / "workspace"
    genre: Path = templates / "platformer"
    (genre / "config").mkdir(parents=True)
    (genre / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    base_cfg = {"meta": {"display_name": "L0"}, "theme": {"title": "L0"}, "tuning": {}}
    (genre / "config" / "game_config.json").write_text(
        json.dumps(base_cfg, ensure_ascii=False),
        encoding="utf-8",
    )
    return templates, workspace, genre


def test_validate_session_id_rejects_path_traversal() -> None:
    with pytest.raises(WorkspaceGuardError):
        validate_session_id("../../etc/passwd")


def test_copy_template_isolated_per_session(sandbox: tuple[Path, Path, Path]) -> None:
    templates, workspace, _ = sandbox
    sid_a = str(uuid.uuid4())
    sid_b = str(uuid.uuid4())
    wa = copy_template_to_workspace(templates, workspace, "platformer", sid_a)
    wb = copy_template_to_workspace(templates, workspace, "platformer", sid_b)
    assert wa != wb
    cfg_a = wa / "config" / "game_config.json"
    cfg_b = wb / "config" / "game_config.json"
    data_a = json.loads(cfg_a.read_text(encoding="utf-8"))
    data_a["meta"]["display_name"] = "用户A"
    cfg_a.write_text(json.dumps(data_a), encoding="utf-8")
    data_b = json.loads(cfg_b.read_text(encoding="utf-8"))
    assert data_b["meta"]["display_name"] == "L0"
    original = json.loads(
        (templates / "platformer" / "config" / "game_config.json").read_text(encoding="utf-8")
    )
    assert original["meta"]["display_name"] == "L0"


def test_build_game_config_refuses_template_write(sandbox: tuple[Path, Path, Path]) -> None:
    templates, workspace, genre = sandbox
    sid = str(uuid.uuid4())
    root = copy_template_to_workspace(templates, workspace, "platformer", sid)
    payload = {
        "meta": {"display_name": "测试作品"},
        "tuning": {"feel_id": "balanced", "enabled_skills": []},
    }
    out = build_game_config(sid, payload, "platformer", root, templates)
    assert out.is_file()
    assert "workspace" in str(out)
    assert "templates" not in str(out.resolve().parts[-3:])


def test_orphan_workspace_cleanup(sandbox: tuple[Path, Path, Path]) -> None:
    templates, workspace, _ = sandbox
    sid_alive = str(uuid.uuid4())
    sid_dead = str(uuid.uuid4())
    copy_template_to_workspace(templates, workspace, "platformer", sid_alive)
    copy_template_to_workspace(templates, workspace, "platformer", sid_dead)
    removed = cleanup_orphan_workspaces(workspace, {sid_alive})
    assert sid_dead in removed
    assert (workspace / sid_alive).is_dir()
    assert not (workspace / sid_dead).exists()
    remove_workspace(workspace, sid_alive)


def test_validate_template_genre(sandbox: tuple[Path, Path, Path]) -> None:
    templates, _, _ = sandbox
    info = validate_template_genre(templates, "platformer")
    assert info["slug"] == "platformer"
