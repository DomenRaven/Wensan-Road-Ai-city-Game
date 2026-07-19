"""HF-12：结构保真 / 关键链 / salvage 交付 / drop-loot 工具化。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.agent_workspace import (
    AgentWorkspaceError,
    list_workspace_tree_high_signal,
    write_workspace_file,
)
from app.services.creative.agent_contracts import (
    assert_script_structure_fidelity,
    load_contract,
    parse_gdscript_structure,
)
from app.services.creative.intent_router import route_intent
from app.services.creative.reference_skills import format_reference_summary_for_prompt
from app.services.creative.sandbox_intent import catalog_for_prompt


def _settings(templates: Path, workspace: Path) -> Settings:
    learned = workspace.parent / "learned_skills_test"
    learned.mkdir(parents=True, exist_ok=True)
    ref = workspace.parent / "reference_skills_test"
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
        agent_max_rounds=8,
        agent_soft_extra_rounds=0,
        agent_wall_clock_sec=60.0,
    )


def test_fidelity_reset_color_only_passes() -> None:
    before = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tposition = Vector2.ZERO\n"
        "func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:\n"
        "\treturn true\n"
        "func _check_scoring() -> void:\n"
        "\tpass\n"
    )
    after = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tposition = Vector2.ZERO\n"
        "\t_visual.color = Color.WHITE\n"
        "func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:\n"
        "\treturn true\n"
        "func _check_scoring() -> void:\n"
        "\tpass\n"
    )
    errs = assert_script_structure_fidelity(
        "core/ball.gd",
        before,
        after,
        genre="pingpong",
        target_func_hints=["reset_to_center"],
    )
    assert errs == []


def test_fidelity_delete_bounce_fails() -> None:
    before = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tpass\n"
        "func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:\n"
        "\treturn true\n"
        "func _apply_paddle_bounce(paddle: Area2D, direction: int) -> void:\n"
        "\tpass\n"
        "func _check_scoring() -> void:\n"
        "\tpass\n"
        "func halt() -> void:\n"
        "\tpass\n"
    )
    after = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tpass\n"
        "func _check_scoring() -> void:\n"
        "\tpass\n"
        "func halt() -> void:\n"
        "\tpass\n"
    )
    errs = assert_script_structure_fidelity(
        "core/ball.gd", before, after, genre="pingpong"
    )
    assert any("_try_paddle_bounce" in e for e in errs)


def test_fidelity_rewrite_scoring_fails() -> None:
    before = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tpass\n"
        "func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:\n"
        "\treturn true\n"
        "func _apply_paddle_bounce(paddle: Area2D, direction: int) -> void:\n"
        "\tpass\n"
        "func _check_scoring() -> void:\n"
        "\tif position.x < 0:\n"
        "\t\tpass\n"
        "func halt() -> void:\n"
        "\tpass\n"
    )
    # 大幅改写计分 + 多处漂移
    after = (
        "extends Area2D\n"
        "func reset_to_center() -> void:\n"
        "\tpass\n"
        "func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:\n"
        "\treturn false\n"
        "func _apply_paddle_bounce(paddle: Area2D, direction: int) -> void:\n"
        "\tqueue_free()\n"
        "func _check_scoring() -> void:\n"
        "\t# totally different scoring\n"
        "\tprint('score')\n"
        "\tprint('again')\n"
        "\tprint('drift')\n"
        "func halt() -> void:\n"
        "\tpass\n"
    )
    errs = assert_script_structure_fidelity(
        "core/ball.gd",
        before,
        after,
        genre="pingpong",
        target_func_hints=["reset_to_center"],
    )
    assert errs
    assert any("非目标" in e or "改动比例" in e for e in errs)


def test_parse_gdscript_structure_funcs() -> None:
    src = "extends Node\nsignal foo\nfunc bar(a: int) -> void:\n\tpass\n"
    st = parse_gdscript_structure(src)
    assert st["extends"] == "Node"
    assert "foo" in st["signals"]
    assert "bar" in st["funcs"]


def test_done_gate_rejects_gutted_critical_chain(tmp_path: Path) -> None:
    """门禁：关键玩法被 stub 掏空时 done 不得过（跨品类通用）。"""
    from app.services.creative.agent_contracts import (
        assert_workspace_critical_chain,
        load_contract,
        run_done_gates,
    )

    root = tmp_path / "ws"
    (root / "core").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        '{"tuning":{"enabled_skills":[]},"theme":{"title":"t"}}',
        encoding="utf-8",
    )
    # stub：无碰撞/计分锚点
    (root / "core" / "ball.gd").write_text(
        "extends Area2D\nfunc start() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "core" / "paddle.gd").write_text(
        "extends Area2D\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "core" / "match_controller.gd").write_text(
        "extends Node\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "scenes").mkdir(parents=True)
    (root / "scenes" / "game.tscn").write_text(
        '[node name="Game" type="Node2D"]\n',
        encoding="utf-8",
    )
    chain_errs = assert_workspace_critical_chain(root, "pingpong")
    assert any("_try_paddle_bounce" in e for e in chain_errs)
    contract = load_contract("pingpong")
    errs = run_done_gates(
        root,
        written_paths=["core/ball.gd"],
        summary="已修复球色恢复，重开后触屏拖动球拍试玩",
        how_to_play=["重开游戏后触屏拖动球拍接球"],
        genre="pingpong",
        contract=contract,
        user_text="发完大力球颜色没恢复",
    )
    assert any("关键" in e or "_try_paddle_bounce" in e for e in errs)


def test_fidelity_preserves_export_and_onready() -> None:
    before = (
        "extends Node\n"
        "@export var speed: float = 2.0\n"
        "@onready var sprite: Sprite2D = $Sprite\n"
        "func run() -> void:\n"
        "\tpass\n"
    )
    after = "extends Node\nfunc run() -> void:\n\tpass\n"
    errs = assert_script_structure_fidelity(
        "core/player.gd", before, after, genre="parkour"
    )
    assert any("@export" in e for e in errs)
    assert any("@onready" in e for e in errs)


def test_minimal_contract_uses_generic_player_node(tmp_path: Path) -> None:
    contract = load_contract("missing_genre", contracts_dir=tmp_path)
    player = next(
        item for item in contract["bridge_apis"] if item.get("name") == "get_player"
    )
    assert player["sig"] == "() -> Node"


@pytest.mark.parametrize(
    "genre",
    [
        "platformer",
        "shmup",
        "parkour",
        "survivor",
        "fighting",
        "racing",
        "pingpong",
    ],
)
def test_seven_contracts_match_template_and_edu_paths(genre: str) -> None:
    from app.config import ROOT_DIR
    from app.services.creative.agent_contracts import PLAYER_PRESENCE_BY_GENRE
    from app.services.edu_workspace import GENRE_HOOKS

    presence = PLAYER_PRESENCE_BY_GENRE[genre]
    template = ROOT_DIR / "templates" / genre
    assert (template / str(presence["script"])).is_file()
    assert (template / str(presence["scene"])).is_file()
    contract = load_contract(genre)
    assert contract["genre"] == genre
    hook = GENRE_HOOKS[genre]
    assert (ROOT_DIR / "templates" / "_edu" / hook).is_file()
    assert (
        ROOT_DIR / "templates" / "_edu" / f"{genre}_touch_overlay.gd"
    ).is_file()
    for skill in contract.get("catalog_skills") or []:
        if not isinstance(skill, dict):
            continue
        sid = str(skill.get("id") or "")
        if sid:
            assert (template / "core" / "skills" / f"{sid}.gd").is_file()


def test_catalog_prompt_genre_isolated() -> None:
    pp = catalog_for_prompt(
        "pingpong",
        {"genre": "pingpong", "catalog_skills": [{"id": "power_smash", "title": "扣杀"}]},
    )
    assert "double_jump" not in pp
    assert "ground_pound" not in pp
    assert "power_smash" in pp

    plat = catalog_for_prompt("platformer", {"genre": "platformer", "catalog_skills": []})
    assert "double_jump" in plat


def test_reference_prompt_is_index_only(tmp_path: Path) -> None:
    root = tmp_path / "reference"
    (root / "_common").mkdir(parents=True)
    (root / "pingpong").mkdir(parents=True)
    (root / "_common" / "agent_loop.md").write_text(
        "SHOULD_NOT_INLINE_COMMON", encoding="utf-8"
    )
    (root / "pingpong" / "SKILL.md").write_text(
        "SHOULD_NOT_INLINE_GENRE", encoding="utf-8"
    )
    prompt = format_reference_summary_for_prompt(root, "pingpong")
    assert "Reference Skills 索引" in prompt
    assert "read_reference_skill" in prompt
    assert "SHOULD_NOT_INLINE" not in prompt


def test_conditional_route_not_pure_a() -> None:
    contract = {
        "genre": "pingpong",
        "catalog_skills": [
            {"id": "power_smash", "title": "大力扣杀", "triggers": ["扣杀", "大力"]}
        ],
        "intent_recipes": [],
        "bridge_apis": [],
    }
    route = route_intent("每接 3 球触发一次大力扣杀，球速也要更快", contract)
    assert route["intent"] != "A"
    assert route.get("express") is False


def test_non_shmup_drop_does_not_route_to_shmup_tool() -> None:
    contract = {
        "genre": "platformer",
        "catalog_skills": [],
        "intent_recipes": [],
        "bridge_apis": [],
    }
    route = route_intent("怪物掉落爱心，捡到才回血", contract)
    assert route["intent"] == "C"
    assert not any(
        action.get("tool") == "apply_shmup_drop_loot_chain"
        for action in route.get("actions") or []
    )


def test_high_signal_tree_prefers_core(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    root = workspace / "sess"
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "assets" / "sfx").mkdir(parents=True)
    (root / "core" / "ball.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "core" / "paddle.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "scenes" / "game.tscn").write_text("[gd_scene]\n", encoding="utf-8")
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    for i in range(30):
        (root / "assets" / "sfx" / f"footstep_{i}.ogg").write_bytes(b"x")
        (root / "assets" / "sfx" / f"footstep_{i}.ogg.import").write_text("x", encoding="utf-8")
    tree = list_workspace_tree_high_signal(
        root, workspace, templates, max_entries=20
    )
    joined = "\n".join(tree)
    assert "core/ball.gd" in joined
    assert "core/paddle.gd" in joined
    assert "scenes/game.tscn" in joined
    assert "footstep" not in joined


def test_drop_loot_tool_enters_llm_path(tmp_path: Path) -> None:
    """有 Key 掉落请求不再 pre-LLM return；走 _llm_turn。"""
    from app.services.creative.game_agent import run_game_agent

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    shmup = templates / "shmup"
    (shmup / "config").mkdir(parents=True)
    (shmup / "core").mkdir(parents=True)
    cfg = {
        "meta": {"genre": "shmup"},
        "tuning": {"enabled_skills": [], "powerup_types": [], "player": {}},
    }
    (shmup / "config" / "game_config.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )
    (shmup / "core" / "player_ship.gd").write_text(
        "extends Area2D\nfunc apply_powerup(powerup_name: String) -> void:\n\tpass\n",
        encoding="utf-8",
    )
    root = workspace / "sess-drop"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )
    (root / "core" / "player_ship.gd").write_text(
        (shmup / "core" / "player_ship.gd").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    settings = _settings(templates, workspace)

    calls = {"n": 0}

    def fake_llm(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "understanding": "掉落才开激光炸弹",
                "goals": ["掉落解锁"],
                "actions": [
                    {
                        "tool": "apply_shmup_drop_loot_chain",
                        "skills": ["laser_beam", "bomb"],
                    },
                    {
                        "tool": "done",
                        "summary": "已改成打敌机捡掉落才开激光炸弹",
                        "how_to_play": ["重开后打敌机捡掉落", "触屏点技能键"],
                    },
                ],
            }
        return {
            "understanding": "收尾",
            "goals": ["掉落解锁"],
            "actions": [
                {
                    "tool": "done",
                    "summary": "已改成打敌机捡掉落才开激光炸弹",
                    "how_to_play": ["重开后打敌机捡掉落", "触屏点技能键"],
                }
            ],
        }

    with patch("app.services.creative.game_agent._llm_turn", side_effect=fake_llm):
        with patch(
            "app.services.creative.game_agent.dry_run_godot",
            return_value={"ok": True, "skipped": True},
        ):
            with patch(
                "app.services.creative.game_agent.run_done_gates",
                return_value=[],
            ):
                result = run_game_agent(
                    settings,
                    root,
                    "shmup",
                    "激光和炸弹做成敌机掉落，捡到才开",
                )
    assert calls["n"] >= 1
    assert int(result.get("agent_rounds") or 0) >= 1


def test_action_dry_run_failure_rolls_back_new_file(tmp_path: Path) -> None:
    from app.services.creative.game_agent import run_game_agent

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    (templates / "unknown" / "core").mkdir(parents=True)
    root = workspace / "sess-action-rollback"
    (root / "core").mkdir(parents=True)
    settings = _settings(templates, workspace)
    calls = {"n": 0}

    def fake_llm(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "understanding": "新增机制",
                "goals": ["新增机制"],
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "core/new_mechanic.gd",
                        "content": "extends Node\nfunc apply() -> void:\n\tpass\n",
                    }
                ],
            }
        return {
            "understanding": "新增机制",
            "goals": ["新增机制"],
            "actions": [
                {
                    "tool": "done",
                    "summary": "尚未完成",
                    "how_to_play": ["重开后查看"],
                }
            ],
        }

    with patch("app.services.creative.game_agent._llm_turn", side_effect=fake_llm):
        with patch(
            "app.services.creative.game_agent.dry_run_godot",
            return_value={
                "ok": False,
                "skipped": False,
                "errors": ["Parse Error: probe"],
            },
        ):
            result = run_game_agent(
                settings,
                root,
                "unknown",
                "新增机制",
                max_rounds=2,
            )
    assert not (root / "core" / "new_mechanic.gd").exists()
    assert result.get("sandbox_files") == []
    assert calls["n"] >= 2


def test_agent_action_rejects_full_write_of_existing_large_file(
    tmp_path: Path,
) -> None:
    from app.services.creative.game_agent import _run_action

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    root = workspace / "sess-large-write"
    (root / "core").mkdir(parents=True)
    big = "extends Node\n" + "".join(
        f"func f{i}() -> void:\n\tpass\n" for i in range(130)
    )
    path = root / "core" / "big.gd"
    path.write_text(big, encoding="utf-8")
    settings = _settings(templates, workspace)
    with pytest.raises(AgentWorkspaceError, match="replace_text"):
        _run_action(
            settings,
            root,
            "unknown",
            {
                "tool": "write_file",
                "path": "core/big.gd",
                "content": big.replace("\tpass", "\treturn", 1),
            },
            load_contract("unknown", contracts_dir=tmp_path / "contracts"),
            [],
            read_eof_by_path={"core/big.gd": True},
            plan_goals=["修改一个函数"],
        )
    assert path.read_text(encoding="utf-8") == big


def test_apply_nl_patch_production_entry_runs_patch_and_gate(tmp_path: Path) -> None:
    from app.services.creative.llm_patch import apply_nl_patch

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    (templates / "unknown" / "core").mkdir(parents=True)
    (templates / "unknown" / "config").mkdir(parents=True)
    config = {
        "meta": {"genre": "unknown"},
        "theme": {"title": "Test"},
        "tuning": {"enabled_skills": []},
    }
    (templates / "unknown" / "config" / "game_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    root = workspace / "sess-production-entry"
    (root / "core").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    settings = _settings(templates, workspace)

    payload = {
        "understanding": "新增一个会话机制",
        "goals": ["新增可加载机制"],
        "actions": [
            {
                "tool": "write_file",
                "path": "core/new_mechanic.gd",
                "content": "extends Node\nfunc apply() -> void:\n\tpass\n",
            },
            {
                "tool": "done",
                "summary": "已新增一个会话机制",
                "how_to_play": ["重开后点屏试玩"],
            },
        ],
    }
    with patch(
        "app.services.creative.game_agent._llm_turn", return_value=payload
    ):
        with patch(
            "app.services.creative.game_agent.dry_run_godot",
            return_value={"ok": True, "skipped": False, "errors": []},
        ):
            with patch(
                "app.services.creative.game_agent.run_done_gates",
                return_value=[],
            ):
                result = apply_nl_patch(
                    settings,
                    root,
                    templates,
                    "unknown",
                    "新增一个会话机制",
                )
    assert result.get("provider") == "agent"
    assert result.get("gate_passed") is True, result
    assert result.get("partial") is False
    assert result.get("sandbox_files") == ["core/new_mechanic.gd"]
    assert (root / "core" / "new_mechanic.gd").is_file()


def test_failed_tool_result_is_reinjected_with_pending_done(
    tmp_path: Path,
) -> None:
    from app.services.creative.game_agent import run_game_agent

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    root = workspace / "sess-tool-feedback"
    (root / "core").mkdir(parents=True)
    src = (
        "extends Node\n"
        "const A := 1\nconst B := 2\nconst C := 3\nconst D := 4\n"
        "const E := 5\nconst F := 6\nconst G := 7\nconst H := 8\n"
        "func value() -> int:\n\treturn 1\n"
    )
    (root / "core" / "logic.gd").write_text(src, encoding="utf-8")
    settings = _settings(templates, workspace)
    seen = {"feedback": False, "calls": 0}

    def fake_llm(_settings, messages):
        seen["calls"] += 1
        return {
            "understanding": "修改返回值",
            "goals": ["返回 2"],
            "actions": [
                {
                    "tool": "replace_text",
                    "path": "core/logic.gd",
                    "old_text": "\treturn 1",
                    "new_text": "\treturn 2",
                    "expected_sha256": "bad-hash",
                },
                {
                    "tool": "done",
                    "summary": "已修改返回值",
                    "how_to_play": ["重开后点屏查看"],
                },
            ],
        }

    def fake_gates(_root, **kwargs):
        return [] if kwargs.get("written_paths") else ["没有有效写入"]

    with patch("app.services.creative.game_agent._llm_turn", side_effect=fake_llm):
        with patch(
            "app.services.creative.game_agent.dry_run_godot",
            return_value={"ok": True, "skipped": False, "errors": []},
        ):
            with patch(
                "app.services.creative.game_agent.run_done_gates",
                side_effect=fake_gates,
            ):
                result = run_game_agent(
                    settings,
                    root,
                    "unknown",
                    "把返回值改成 2",
                    max_rounds=3,
                )
    # 陈旧 hash + 唯一命中 → 首轮即写入成功（不再靠「hash 冲突」回灌空转）
    assert seen["calls"] == 1
    assert result.get("gate_passed") is True
    assert "\treturn 2" in (root / "core" / "logic.gd").read_text(encoding="utf-8")


def test_salvage_with_written_rolls_back_and_reports_attempted(
    tmp_path: Path,
) -> None:
    from app.services.creative.game_agent import _salvage_agent_return

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    root = workspace / "sess-salvage-rollback"
    (root / "core").mkdir(parents=True)
    path = root / "core" / "logic.gd"
    original = b"extends Node\nfunc old() -> void:\n\tpass\n"
    path.write_bytes(b"extends Node\nfunc changed() -> void:\n\tpass\n")
    settings = _settings(templates, workspace)
    with patch(
        "app.services.creative.game_agent.dry_run_godot",
        return_value={"ok": True, "skipped": False, "errors": []},
    ):
        result = _salvage_agent_return(
            settings,
            root,
            "unknown",
            route={"intent": "C", "skill_ids": []},
            written=["core/logic.gd"],
            catalog_changed=False,
            pre_turn_snapshot={"core/logic.gd": original},
            last_summary="尝试修改",
            last_how=["重开后查看"],
            last_understanding="修改逻辑",
            plan_goals=["修改逻辑"],
            progress_events=[],
            rounds_used=2,
            reason="测试回滚",
        )
    assert path.read_bytes() == original
    assert result.get("sandbox_files") == []
    assert result.get("attempted_paths") == ["core/logic.gd"]
    assert result.get("gate_passed") is False
    assert result.get("partial") is True


def test_kiosk_partial_agent_badge_is_not_success_badge() -> None:
    from app.config import ROOT_DIR

    js = (ROOT_DIR / "kiosk" / "edu" / "nl-patch-dialog.js").read_text(
        encoding="utf-8"
    )
    assert "智能体施工中 · 尚未验收" in js
    assert "const isPartial" in js
