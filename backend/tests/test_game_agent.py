"""会话智能体工作区读写 + nl-patch agent / 无 Key stub。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.agent_workspace import (
    AgentWorkspaceError,
    list_workspace_tree,
    read_workspace_file,
    write_workspace_file,
)
from app.services.creative.learned_skills import enable_catalog_skill
from app.services.creative.llm_patch import apply_nl_patch


def _settings(templates: Path, workspace: Path, api_key: str = "sk-test") -> Settings:
    learned = workspace.parent / "learned_skills_test"
    learned.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        allow_memory_fallback=True,
        llm_api_key=api_key,
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
        llm_timeout_sec=5.0,
    )


def _mini_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    genre = "platformer"
    cfg = {
        "meta": {"genre": genre},
        "tuning": {
            "player": {"move_speed": 200, "jump_velocity": -400},
            "enabled_skills": [],
        },
        "theme": {"title": "测"},
    }
    (templates / genre / "config").mkdir(parents=True)
    (templates / genre / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    (templates / genre / "core").mkdir(parents=True)
    (templates / genre / "core" / "player.gd").write_text(
        "extends CharacterBody2D\n", encoding="utf-8"
    )
    root = workspace / "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    (root / "core").mkdir(parents=True)
    (root / "core" / "player.gd").write_text("extends CharacterBody2D\n", encoding="utf-8")
    return templates, workspace, root


def test_agent_can_write_session_core_not_templates(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    rel = write_workspace_file(
        root,
        workspace,
        templates,
        "core/player.gd",
        "extends CharacterBody2D\n# agent edit\n",
    )
    assert rel == "core/player.gd"
    assert "agent edit" in (root / "core" / "player.gd").read_text(encoding="utf-8")
    assert "# agent edit" not in (
        templates / "platformer" / "core" / "player.gd"
    ).read_text(encoding="utf-8")
    with pytest.raises(AgentWorkspaceError):
        write_workspace_file(root, workspace, templates, "project.godot", "hack=1\n")


def test_agent_sandbox_new_file_and_list(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    write_workspace_file(
        root,
        workspace,
        templates,
        "core/ai_sandbox/fun_buff.gd",
        "extends Node\nfunc apply(bridge) -> void:\n\tpass\n",
    )
    entries = list_workspace_tree(root, workspace, templates, "core")
    assert any(e.endswith("fun_buff.gd") for e in entries)
    text = read_workspace_file(
        root, workspace, templates, "core/ai_sandbox/fun_buff.gd"
    )
    assert "func apply" in text


def test_nl_patch_agent_with_key_stub_without(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")

    fake_agent = {
        "ok": True,
        "provider": "agent",
        "summary": "已加趣味技能",
        "message": "已加趣味技能",
        "sandbox_files": ["core/ai_sandbox/fun.gd"],
        "how_to_play": ["重开后按技能键"],
        "agent_rounds": 2,
    }
    with patch(
        "app.services.creative.llm_patch.run_game_agent", return_value=fake_agent
    ):
        result = apply_nl_patch(
            settings, root, templates, "platformer", "多加有趣的技能"
        )
    assert result["ok"] is True
    assert result["provider"] == "agent"
    assert "core/ai_sandbox/fun.gd" in result["sandbox_files"]

    settings2 = _settings(templates, workspace, api_key="")
    result2 = apply_nl_patch(
        settings2, root, templates, "platformer", "加二段跳并画图标"
    )
    assert result2["ok"] is True
    assert result2["provider"] == "stub"


def test_enable_catalog_skill_writes_config(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    out = enable_catalog_skill(root, "platformer", "double_jump")
    assert out["skill_id"] == "double_jump"
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert "double_jump" in cfg["tuning"]["enabled_skills"]
