"""意图路由 A/B/C/D + catalog runtime 门禁单测。"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.creative.agent_contracts import (
    assert_catalog_runtime,
    load_contract,
    run_done_gates,
)
from app.services.creative.intent_router import (
    enforce_route_on_actions,
    route_intent,
)


def test_route_shmup_catalog_is_a() -> None:
    c = load_contract("shmup")
    r = route_intent("飞机技能太少，来个炸弹和激光", c)
    assert r["intent"] == "A"
    assert "bomb" in r["skill_ids"]
    assert "laser_beam" in r["skill_ids"]
    assert any(a.get("tool") == "enable_catalog_skill" for a in r["actions"])


def test_route_mouse_skill_conflict_is_b_not_a() -> None:
    """鼠标跟机抢按钮：优先 B 补丁，禁止再走 A 重复开技能。"""
    c = load_contract("shmup")
    r = route_intent(
        "飞机是鼠标操控的，点击炸弹激光按钮只会改变飞机位置，技能不能用",
        c,
    )
    assert r["intent"] == "B"
    assert r["skill_ids"] == []
    assert any(a.get("tool") == "patch_mouse_steer_guard" for a in r["actions"])


def test_route_touch_dead_keyboard_ok_not_a() -> None:
    c = load_contract("shmup")
    r = route_intent("点击激光按钮不发射激光，点击e键发射", c)
    assert r["intent"] == "B"
    assert r["skill_ids"] == []
    assert any(
        a.get("tool") in ("refresh_ai_sandbox_bridge", "ensure_touch_skill_buttons")
        for a in r["actions"]
    )
    assert not any(a.get("tool") == "enable_catalog_skill" for a in r["actions"])


def test_route_platformer_double_jump_is_a() -> None:
    c = load_contract("platformer")
    r = route_intent("我想要二段跳", c)
    assert r["intent"] == "A"
    assert "double_jump" in r["skill_ids"]


def test_route_rainbow_bullets_is_c() -> None:
    c = load_contract("shmup")
    r = route_intent("子弹五颜六色", c)
    assert r["intent"] == "C"
    assert r["stop"] is False


def test_route_novel_request_is_c_free_create() -> None:
    """前所未有需求走 C 自由创作，不停；提示需求对齐而非特例劝退。"""
    c = load_contract("platformer")
    r = route_intent("加一个boss试试", c)
    assert r["intent"] == "C"
    assert r["stop"] is False
    assert "顶替" in r["hint"] or "捷径" in r["hint"]


def test_route_novel_feedback_stays_actionable() -> None:
    c = load_contract("platformer")
    r = route_intent("没有看到boss，重做一下", c)
    assert r["stop"] is False
    assert r["intent"] in ("B", "C")


def test_route_player_missing_is_repair() -> None:
    c = load_contract("platformer")
    r = route_intent("人物消失不显示。修复问题", c)
    assert r["intent"] == "B"
    assert r["stop"] is False
    assert "可见" in r["hint"] or "玩家" in r["hint"]


def test_route_invented_bridge_is_d() -> None:
    c = load_contract("shmup")
    r = route_intent("请用 bridge.add_method 挂一个新引擎技能", c)
    assert r["intent"] == "D"
    assert r["stop"] is True


def test_enforce_route_a_allows_core_write() -> None:
    """catalog 命中不再强制 enable；允许会话 core 另写。"""
    c = load_contract("shmup")
    r = route_intent("开炸弹", c)
    errs = enforce_route_on_actions(
        r,
        [
            {
                "tool": "write_file",
                "path": "core/custom_bomb.gd",
                "content": "extends Node\n",
            }
        ],
    )
    assert errs == []


def test_seven_contracts_catalog_have_runtime() -> None:
    for genre in (
        "platformer",
        "shmup",
        "survivor",
        "parkour",
        "pingpong",
        "fighting",
        "racing",
    ):
        c = load_contract(genre)
        skills = c.get("catalog_skills") or []
        assert skills, genre
        for s in skills:
            assert isinstance(s, dict)
            rt = s.get("runtime")
            assert isinstance(rt, dict), f"{genre}/{s.get('id')}"
            assert rt.get("input")
            assert rt.get("effect")
            assert rt.get("touch")
        names = {x["name"] for x in c["bridge_apis"] if isinstance(x, dict)}
        assert "ensure_touch_action" in names, genre


def test_diagnose_workspace_reports_skills(tmp_path: Path) -> None:
    from app.services.creative.agent_contracts import diagnose_workspace

    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["laser_beam"]}}),
        encoding="utf-8",
    )
    (root / "core" / "ai_sandbox_bridge.gd").write_text(
        "extends Node\nfunc ensure_touch_action(a, b):\n\tpass\n",
        encoding="utf-8",
    )
    d = diagnose_workspace(root, "shmup", load_contract("shmup"))
    assert d["enabled_skills"] == ["laser_beam"]
    assert d["has_bridge"] is True
    assert d["bridge_has_ensure_touch"] is True


def test_runtime_gate_blocks_config_only_no_core(tmp_path: Path) -> None:
    """L3 收紧：仅有 config、无 core/桥/overlay → 拒。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb"]}}),
        encoding="utf-8",
    )
    c = load_contract("shmup")
    errs = assert_catalog_runtime(
        root,
        c,
        summary="已启用炸弹",
        how_to_play=["重开后点屏幕下方炸弹按钮"],
    )
    assert any("未接线" in e or "触屏" in e for e in errs)


def test_runtime_gate_passes_with_bridge_ensure_touch(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb"]}}),
        encoding="utf-8",
    )
    (root / "core" / "ai_sandbox_bridge.gd").write_text(
        "extends Node\nfunc ensure_touch_action(a: String, b: String) -> void:\n\tpass\n",
        encoding="utf-8",
    )
    c = load_contract("shmup")
    errs = assert_catalog_runtime(
        root,
        c,
        summary="已启用炸弹",
        how_to_play=["重开后点屏幕下方炸弹按钮"],
    )
    assert errs == []



def test_runtime_gate_blocks_missing_runtime_field(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb"]}}),
        encoding="utf-8",
    )
    c = load_contract("shmup")
    # 剥离 runtime 模拟坏契约
    bad = dict(c)
    bad["catalog_skills"] = [
        {"id": "bomb", "label": "炸弹", "desc": "x", "trigger": "y"}
    ]
    errs = assert_catalog_runtime(root, bad, summary="已启用炸弹可玩", how_to_play=["重开"])
    assert any("runtime" in e or "L1" in e for e in errs)


def test_done_gate_how_to_play_requires_touch(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb"]}}),
        encoding="utf-8",
    )
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=[],
        summary="已启用炸弹",
        how_to_play=["请重新启动游戏后按 Q"],
        genre="shmup",
        contract=c,
        catalog_changed=True,
    )
    assert any("触屏" in e for e in errs)
