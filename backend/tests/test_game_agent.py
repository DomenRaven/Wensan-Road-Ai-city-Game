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


def test_catalog_express_laser_skips_llm(tmp_path: Path) -> None:
    """「发射激光」应走 catalog 快车道，不调用多轮 LLM。"""
    from app.services.creative.game_agent import run_game_agent

    templates, workspace, root = _mini_tree(tmp_path)
    # shmup 树：补 optional 目录技能依赖
    shmup = templates / "shmup"
    (shmup / "config").mkdir(parents=True, exist_ok=True)
    (shmup / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "meta": {"genre": "shmup"},
                "tuning": {"enabled_skills": [], "player": {"move_speed": 200}},
                "theme": {"title": "测"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "meta": {"genre": "shmup"},
                "tuning": {"enabled_skills": [], "player": {"move_speed": 200}},
                "theme": {"title": "测"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    settings = _settings(templates, workspace, api_key="sk-test")
    with patch("app.services.creative.game_agent._llm_turn") as llm:
        with patch(
            "app.services.creative.game_agent.refresh_ai_sandbox_bridge",
            return_value=True,
        ):
            with patch(
                "app.services.creative.game_agent.enable_catalog_skill",
                return_value={"skill_id": "laser_beam", "label": "激光"},
            ):
                with patch(
                    "app.services.creative.game_agent.run_done_gates",
                    return_value=[],
                ):
                    out = run_game_agent(
                        settings, root, "shmup", "我想加发射激光"
                    )
    assert out["ok"] is True
    assert out.get("express") is True
    assert out["agent_rounds"] == 0
    assert "laser_beam" in (out.get("applied_capabilities") or [])
    llm.assert_not_called()


def test_enable_catalog_skill_writes_config(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    out = enable_catalog_skill(root, "platformer", "double_jump")
    assert out["skill_id"] == "double_jump"
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert "double_jump" in cfg["tuning"]["enabled_skills"]


def test_salvage_bugfix_rollback_does_not_claim_playable(tmp_path: Path) -> None:
    """HF-9：故障局回滚不得声称「能正常玩」。"""
    from app.services.creative.game_agent import _salvage_agent_return

    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")
    # 本轮「写坏」了脚本，dry_run 会失败 → 走回滚分支
    bad = root / "core" / "player.gd"
    bad.write_text("extends CharacterBody2D\nfunc _ready():\n\tbroken(\n", encoding="utf-8")
    with patch(
        "app.services.creative.game_agent.dry_run_godot",
        return_value={"ok": False, "skipped": False, "errors": ["Node not found: ../Player"]},
    ):
        out = _salvage_agent_return(
            settings,
            root,
            "platformer",
            route={"intent": "B", "skill_ids": [], "recipe_id": "运行时显示/启动故障"},
            written=["core/player.gd"],
            catalog_changed=False,
            pre_turn_snapshot={"core/player.gd": b"extends CharacterBody2D\n"},
            last_summary="",
            last_how=[],
            last_understanding="人物消失需要修节点路径",
            plan_goals=["修玩家可见"],
            progress_events=[],
            rounds_used=3,
            reason='dry_run: Node not found: "../Player"',
            bugfix=True,
        )
    assert out["ok"] is True
    assert out.get("partial") is True
    assert out.get("playability_suspect") is True
    msg = out["message"]
    assert "能正常玩" not in msg
    assert "没弄坏" not in msg
    assert (
        "原先" in msg
        or "可能还在" in msg
        or "人物仍有问题" in msg
        or "专修" in msg
    )


def test_llm_bad_json_salvages_inside_agent(tmp_path: Path) -> None:
    """HF-9：Agent 内 LLM 坏 JSON 应 salvage，不抛到入口上锁。"""
    from app.services.creative.game_agent import run_game_agent

    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")
    with patch(
        "app.services.creative.game_agent._llm_turn",
        side_effect=json.JSONDecodeError("Expecting ',' delimiter", "bad", 10),
    ):
        with patch(
            "app.services.creative.game_agent._can_catalog_express",
            return_value=False,
        ):
            out = run_game_agent(
                settings,
                root,
                "platformer",
                "人物消失不见了",
                max_rounds=2,
            )
    assert out["ok"] is True
    assert out.get("partial") is True
    assert "没改成" not in out["message"]
    assert "换个说法" not in out["message"]
