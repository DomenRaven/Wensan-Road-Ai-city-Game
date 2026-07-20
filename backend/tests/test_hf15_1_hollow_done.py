"""HF-15.1：虚空 Done / 同错早停 · 非法 evidence · symbols_added。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.creative.agent_contracts import (
    assert_evidence_wired,
    extract_symbols_added_from_gd,
    gate_error_key_sets_similar,
    load_contract,
    normalize_gate_error_keys,
    update_gate_error_streak,
)
from app.services.creative.game_agent import _run_action


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _settings(templates: Path, workspace: Path) -> Settings:
    learned = workspace.parent / "learned_skills_hf151"
    learned.mkdir(parents=True, exist_ok=True)
    ref = workspace.parent / "reference_skills_hf151"
    ref.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        reference_skills_dir=ref,
        allow_memory_fallback=True,
        llm_api_key="sk-test",
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
        llm_timeout_sec=5.0,
        agent_max_rounds=16,
        agent_soft_extra_rounds=0,
        agent_wall_clock_sec=360.0,
    )


def _mini_shmup_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    genre = "shmup"
    cfg = {
        "meta": {"genre": genre},
        "tuning": {"enabled_skills": []},
        "theme": {"title": "测"},
    }
    (templates / genre / "config").mkdir(parents=True)
    (templates / genre / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    root = workspace / "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    ship = (
        "extends CharacterBody2D\n"
        "func _ready() -> void:\n"
        "\tpass\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
        "func _physics_process(delta: float) -> void:\n"
        "\tpass\n"
        "func notify_hazard() -> void:\n"
        "\tpass\n"
        "func apply_powerup(_t: String) -> void:\n"
        "\tpass\n"
    )
    _write(root / "core" / "player_ship.gd", ship)
    _write(
        root / "scenes" / "player.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n'
        '[node name="Sprite2D" type="Sprite2D" parent="."]\n',
    )
    return templates, workspace, root


def test_reject_tscn_path_as_symbol(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "scenes" / "hud.tscn",
        '[node name="LivesPanel" type="Control"]\n',
    )
    errs = assert_evidence_wired(
        root,
        [
            {
                "goal": "命数图标",
                "path": "scenes/hud.tscn",
                "symbol": "LivesPanel",
                "wired_by": "_ready",
            }
        ],
        require=True,
    )
    assert errs
    assert any("不可用场景路径" in e for e in errs)


def test_reject_arrow_wired_by(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "func _ready() -> void:\n"
        "\tpass\n"
        "func add_life() -> void:\n"
        "\tpass\n",
    )
    errs = assert_evidence_wired(
        root,
        [
            {
                "goal": "回命",
                "path": "core/player_ship.gd",
                "symbol": "add_life",
                "wired_by": "_ready -> add_life",
            }
        ],
        require=True,
    )
    assert errs
    assert any("箭头链" in e for e in errs)


def test_new_symbol_requires_written_path(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    rel = "core/player_ship.gd"
    body = (
        "extends CharacterBody2D\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
    )
    _write(root / rel, body)
    snap = {rel: body.encode("utf-8")}
    errs = assert_evidence_wired(
        root,
        [
            {
                "goal": "Boss回命",
                "path": rel,
                "symbol": "add_life",
                "wired_by": "_process",
            }
        ],
        require=True,
        written_paths=["config/game_config.json"],
        pre_turn_snapshot=snap,
    )
    assert any("新符号须本轮写入" in e for e in errs)


def test_gate_error_streak_helpers() -> None:
    err = "evidence 符号未定义：add_life @ core/player_ship.gd（Boss回命）"
    keys = normalize_gate_error_keys([err])
    assert "symbol_undefined:add_life@core/player_ship.gd" in keys
    streak = 0
    last: frozenset[str] = frozenset()
    streak, last = update_gate_error_streak(streak, last, [err])
    assert streak == 1
    streak, last = update_gate_error_streak(streak, last, [err])
    assert streak == 2
    streak, last = update_gate_error_streak(streak, last, [err])
    assert streak == 3
    assert gate_error_key_sets_similar(keys, keys)


def test_same_error_streak_stops_early(tmp_path: Path) -> None:
    """连续 3 轮同一 evidence 门禁失败 → partial 早停（轮次远小于 max）。"""
    from app.services.creative.game_agent import run_game_agent

    templates, workspace, root = _mini_shmup_tree(tmp_path)
    settings = _settings(templates, workspace)
    llm_calls = {"n": 0}
    wrote_marker = {"done": False}

    def fake_llm(*_args: object, **_kwargs: object) -> dict[str, object]:
        llm_calls["n"] += 1
        actions: list[dict[str, object]] = []
        if not wrote_marker["done"]:
            actions.append(
                {
                    "tool": "replace_text",
                    "path": "core/player_ship.gd",
                    "old_text": "func _process(delta: float) -> void:\n\tpass\n",
                    "new_text": (
                        "func _process(delta: float) -> void:\n"
                        "\t# hf151 marker\n"
                        "\tpass\n"
                    ),
                }
            )
            wrote_marker["done"] = True
        actions.append(
            {
                "tool": "done",
                "summary": "已实现 Boss 回命与命数图标全部功能，请重开试玩",
                "how_to_play": ["请重新启动游戏后拖动飞机试玩", "点屏幕下方按钮"],
                "evidence": [
                    {
                        "goal": "Boss回命",
                        "path": "core/player_ship.gd",
                        "symbol": "add_life",
                        "wired_by": "_process",
                    }
                ],
            }
        )
        return {
            "understanding": "Boss 击败回命",
            "goals": ["Boss回命", "命数图标", "难度提升", "HUD显示"],
            "thought": "宣称已实现",
            "actions": actions,
        }

    with patch("app.services.creative.game_agent._llm_turn", side_effect=fake_llm):
        with patch(
            "app.services.creative.game_agent._can_catalog_express",
            return_value=False,
        ):
            with patch(
                "app.services.creative.game_agent.dry_run_godot",
                return_value={"ok": True, "skipped": False, "errors": []},
            ):
                out = run_game_agent(
                    settings,
                    root,
                    "shmup",
                    "Boss 击败后回一条命并显示命数图标",
                    max_rounds=12,
                )

    assert out.get("partial") is True
    assert out.get("gate_passed") is False
    assert llm_calls["n"] <= 4
    gaps_blob = " ".join(str(x) for x in (out.get("verify_gaps") or []))
    assert "连续三次相同门禁失败" in gaps_blob


def test_symbols_added_on_replace(tmp_path: Path) -> None:
    templates, workspace, root = _mini_shmup_tree(tmp_path)
    settings = _settings(templates, workspace)
    out = _run_action(
        settings,
        root,
        "shmup",
        {
            "tool": "replace_text",
            "path": "core/player_ship.gd",
            "old_text": "func _process(delta: float) -> void:\n\tpass\n",
            "new_text": (
                "func _process(delta: float) -> void:\n"
                "\tadd_life()\n"
                "func add_life() -> void:\n"
                "\tpass\n"
            ),
        },
        load_contract("shmup"),
        [],
    )
    assert "add_life" in (out.get("symbols_added") or [])
    assert extract_symbols_added_from_gd(
        "func foo() -> void:\n\tpass\nfunc bar() -> void:\n\tpass\n"
    ) == ["foo", "bar"]


def test_hf15_regression_smoke(tmp_path: Path) -> None:
    """HF-15 L1 多 wired_by 回归（与 test_hf15_oracle_layers 同案）。"""
    root = tmp_path / "ws"
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "func foo() -> void:\n"
        "\tbar()\n"
        "func bar() -> void:\n"
        "\t_update_x()\n"
        "func _update_x() -> void:\n"
        "\tpass\n",
    )
    assert (
        assert_evidence_wired(
            root,
            [
                {
                    "path": "core/player_ship.gd",
                    "symbol": "_update_x",
                    "wired_by": "foo|bar",
                }
            ],
            require=True,
        )
        == []
    )
