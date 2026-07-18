"""意图路由 A/B/C/D + catalog runtime 门禁单测。"""

from __future__ import annotations

import json
import re
import uuid
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


def test_route_drop_loot_is_c_not_catalog_express() -> None:
    """「敌机掉落才开」不得走 catalog 快开按钮技能。"""
    from app.services.creative.game_agent import _can_catalog_express

    c = load_contract("shmup")
    text = "激光和炸弹是敌机掉落物，掉落才开启"
    r = route_intent(text, c)
    assert r["intent"] == "C"
    assert r.get("skill_ids") == []
    assert r.get("express") is False
    assert not any(a.get("tool") == "enable_catalog_skill" for a in r["actions"])
    assert _can_catalog_express(r, text, "") is False
    # 对比：单纯开激光仍走 A 快车道
    r2 = route_intent("开启激光", c)
    assert r2["intent"] == "A"
    assert _can_catalog_express(r2, "开启激光", "") is True


def test_shmup_drop_loot_express_patches_powerup() -> None:
    """shmup 掉落快车道：powerup_types + apply_powerup，且非 catalog express。"""
    from app.config import get_settings
    from app.services.creative.game_agent import _run_shmup_drop_loot_express
    from app.services.workspace import copy_template_to_workspace
    from app.services.workspace_guard import remove_workspace

    settings = get_settings()
    sid = str(uuid.uuid4())
    root = copy_template_to_workspace(
        settings.templates_dir, settings.workspace_dir, "shmup", sid
    )
    try:
        c = load_contract("shmup")
        text = "激光和炸弹是敌机掉落物，掉落才开启"
        r = route_intent(text, c)
        out = _run_shmup_drop_loot_express(settings, root, text, r, c)
        assert out["ok"] is True
        assert out.get("express") is False
        assert "点屏幕下方对应按钮" not in out["summary"]
        cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
        names = [x.get("name") for x in cfg["tuning"]["powerup_types"]]
        assert "laser" in names and "bomb" in names
        assert cfg["tuning"]["enabled_skills"] == []
        ps = (root / "core" / "player_ship.gd").read_text(encoding="utf-8")
        assert "_unlock_catalog_skill" in ps
        assert re.search(r"func\s+_unlock_catalog_skill\s*\(", ps)
        assert re.search(r'["\']laser["\']', ps)
    finally:
        remove_workspace(settings.workspace_dir, sid)


def test_done_gate_rejects_button_promo_for_drop_loot(tmp_path: Path) -> None:
    """掉落需求：禁止「已开启/点下方按钮」空口交差。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "tuning": {
                    "enabled_skills": ["bomb", "laser_beam"],
                    "powerup_types": [
                        {"name": "fireRate", "frame": 12},
                        {"name": "shield", "frame": 13},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "core" / "player_ship.gd").write_text(
        'extends Area2D\nfunc apply_powerup(powerup_name: String) -> void:\n'
        '\tmatch powerup_name:\n\t\t"fireRate":\n\t\t\tpass\n\t\t"shield":\n\t\t\tpass\n',
        encoding="utf-8",
    )
    c = load_contract("shmup")
    text = "激光和炸弹是敌机掉落物，掉落才开启"
    errs = run_done_gates(
        root,
        written_paths=["config/game_config.json"],
        summary="已为你开启「清屏炸弹、激光」。请重新启动游戏，点屏幕下方对应按钮试玩。",
        how_to_play=[
            "重要：必须重新启动游戏后新技能才会生效",
            "点屏幕下方「清屏炸弹、激光」按钮试玩（触屏）",
        ],
        genre="shmup",
        contract=c,
        catalog_changed=True,
        user_text=text,
    )
    assert any("掉落物" in e for e in errs)


def test_done_gate_accepts_drop_loot_powerup_impl(tmp_path: Path) -> None:
    """掉落需求：powerup_types + apply_powerup + 捡掉落话术可通过。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "tuning": {
                    "enabled_skills": [],
                    "powerup_types": [
                        {"name": "fireRate", "frame": 12},
                        {"name": "laser", "frame": 8},
                        {"name": "bomb", "frame": 9},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "core" / "player_ship.gd").write_text(
        'extends Area2D\nfunc apply_powerup(powerup_name: String) -> void:\n'
        '\tmatch powerup_name:\n'
        '\t\t"laser":\n'
        '\t\t\tvar skills: Array = []\n'
        '\t\t\tskills.append("laser_beam")\n'
        '\t\t\t# unlock via enabled_skills + AiSandboxBridge\n'
        '\t\t"bomb":\n'
        '\t\t\tpass\n',
        encoding="utf-8",
    )
    (root / "core" / "enemy_spawner.gd").write_text(
        "extends Node2D\nsignal request_powerup(spawn_pos: Vector2, count: int)\n",
        encoding="utf-8",
    )
    (root / "scenes" / "main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n[node name="Main" type="Node2D" groups=["game_manager"]]\n'
        '[node name="EnemySpawner" type="Node2D" parent="."]\n',
        encoding="utf-8",
    )
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=["config/game_config.json", "core/player_ship.gd"],
        summary="已把激光和炸弹改成敌机掉落物，捡到后才解锁。",
        how_to_play=[
            "重要：重新启动游戏后生效",
            "打敌机，捡掉落的激光/炸弹道具后再用（触屏飞过去撞拾取）",
        ],
        genre="shmup",
        contract=c,
        catalog_changed=False,
        user_text="激光和炸弹是敌机掉落物，掉落才开启",
    )
    assert not any("掉落物" in e for e in errs)


def test_done_gate_rejects_gutted_spawner_for_drop_loot(tmp_path: Path) -> None:
    """掉落需求：掏空 enemy_spawner 应被门禁拦住。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "tuning": {
                    "enabled_skills": [],
                    "powerup_types": [
                        {"name": "laser", "frame": 14},
                        {"name": "bomb", "frame": 15},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "core" / "player_ship.gd").write_text(
        'extends Area2D\nfunc apply_powerup(n: String) -> void:\n\tmatch n:\n\t\t"laser":\n\t\t\tpass\n',
        encoding="utf-8",
    )
    (root / "core" / "enemy_spawner.gd").write_text(
        "extends Node\nfunc spawn_enemy() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=["core/enemy_spawner.gd", "config/game_config.json"],
        summary="已做成敌机掉落，捡到才开激光炸弹。",
        how_to_play=["重开后打敌机捡掉落物"],
        genre="shmup",
        contract=c,
        user_text="激光和炸弹是敌机掉落物，掉落才开启",
    )
    assert any("request_powerup" in e for e in errs)


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
