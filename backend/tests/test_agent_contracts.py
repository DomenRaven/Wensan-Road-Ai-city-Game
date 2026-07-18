"""门禁 / 契约 / 进度事件单测（v1.1 闭环）。"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.creative.agent_contracts import (
    PROGRESS_STAGES,
    assert_apis_in_contract,
    assert_claims,
    emit_progress,
    load_contract,
    run_done_gates,
    validate_gdscript,
)
from app.services.creative.genre_context import build_genre_llm_context


def test_load_seven_contracts() -> None:
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
        assert c["genre"] == genre
        assert len(c["bridge_apis"]) >= 8
        names = {x["name"] for x in c["bridge_apis"] if isinstance(x, dict)}
        assert "set_tuning_number" in names


def test_shmup_contract_has_tint_and_shield() -> None:
    c = load_contract("shmup")
    names = {x["name"] for x in c["bridge_apis"] if isinstance(x, dict)}
    assert "tint_player_bullets" in names
    assert "rainbow_player_bullets" in names
    assert "grant_temp_shield" in names
    assert "ensure_touch_action" in names
    bomb = next(s for s in c["catalog_skills"] if s["id"] == "bomb")
    assert bomb["runtime"]["effect"] == "bridge:activate_bomb"


def test_assert_apis_blocks_invented() -> None:
    c = load_contract("shmup")
    bad = """
extends Node
func apply(bridge) -> void:
	bridge.add_method("foo", Callable())
	bullet.set_color(Color.red)
"""
    errs = assert_apis_in_contract(bad, c)
    assert any("add_method" in e or "禁止" in e for e in errs)
    syn = validate_gdscript(bad)
    assert any("Color.red" in e or "幻想" in e or "禁止" in e for e in syn)


def test_assert_apis_allows_contract_methods() -> None:
    c = load_contract("shmup")
    good = """
extends Node
func apply(bridge) -> void:
	bridge.rainbow_player_bullets()
	bridge.grant_temp_shield(6.0)
"""
    assert assert_apis_in_contract(good, c) == []
    assert validate_gdscript(good) == []


def test_edu_bridge_not_flagged_for_merge_overrides_helper() -> None:
    """模板桥合法函数 _merge_overrides_json 不得被误判为幻想 API。"""
    from pathlib import Path

    from app.config import ROOT_DIR

    bridge = ROOT_DIR / "templates" / "_edu" / "ai_sandbox_bridge.gd"
    text = bridge.read_text(encoding="utf-8")
    assert "_merge_overrides_json" in text
    assert validate_gdscript(text) == []
    c = load_contract("shmup")
    assert assert_apis_in_contract(text, c) == []


def test_forbidden_api_still_catches_bare_merge_overrides() -> None:
    bad = 'extends Node\nfunc apply(b):\n\tmerge_overrides({"a":1})\n'
    assert any("merge_overrides" in e for e in validate_gdscript(bad))


def test_done_gate_skips_trusted_edu_bridge(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        '{"tuning":{"enabled_skills":["laser_beam"]}}', encoding="utf-8"
    )
    # 故意写「会被旧门禁误杀」的桥内容
    (root / "core" / "ai_sandbox_bridge.gd").write_text(
        "extends Node\nfunc _merge_overrides_json() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "core" / "shmup_touch_overlay.gd").write_text(
        "extends CanvasLayer\n", encoding="utf-8"
    )
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=["core/ai_sandbox_bridge.gd", "config/game_config.json"],
        summary="已为你开启「激光」。请重新启动游戏，点屏幕下方对应按钮试玩。",
        how_to_play=[
            "重要：必须重新启动游戏后新技能才会生效",
            "点屏幕下方「激光」按钮试玩（触屏）",
        ],
        genre="shmup",
        contract=c,
        catalog_changed=True,
        user_text="开启激光",
    )
    assert not any("merge_overrides" in e or "括号" in e for e in errs)


def test_done_gate_bugfix_allows_relaunch_howto(tmp_path: Path) -> None:
    """故障修复局：how_to_play 写「重开后查看」即可，不强制技能按钮文案。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    (root / "core" / "fix.gd").write_text(
        "extends CharacterBody2D\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "core" / "player_platformer.gd").write_text(
        "extends CharacterBody2D\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "scenes" / "player.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n'
        '[node name="Sprite2D" type="Sprite2D" parent="."]\n',
        encoding="utf-8",
    )
    c = load_contract("platformer")
    errs = run_done_gates(
        root,
        written_paths=["core/fix.gd"],
        summary="已修复人物显示，visible 恢复为 true",
        how_to_play=["请重新启动游戏查看人物是否出现"],
        genre="platformer",
        contract=c,
        catalog_changed=False,
        user_text="人物消失不显示。修复问题",
    )
    assert errs == []


def test_assert_claims_blocks_fake_shield(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb"]}}),
        encoding="utf-8",
    )
    errs = assert_claims(
        root,
        "已新增护盾技能，飞机更安全",
        ["按右键开护盾", "请重新启动游戏"],
        [],
        genre="shmup",
    )
    assert errs


def test_assert_claims_blocks_boss_via_invincibility(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core" / "ai_sandbox").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": []}}),
        encoding="utf-8",
    )
    (root / "core" / "ai_sandbox" / "fake_boss.gd").write_text(
        "extends Node\nfunc apply(bridge) -> void:\n"
        "\tbridge.watch_coins(func(_n): bridge.grant_invincibility(5.0))\n",
        encoding="utf-8",
    )
    errs = assert_claims(
        root,
        "已加 Boss 战，吃金币触发无敌当 Boss",
        ["重开后打 Boss"],
        ["core/ai_sandbox/fake_boss.gd"],
        genre="platformer",
    )
    assert errs
    assert any("Boss" in e for e in errs)


def test_assert_claims_honest_boss_limit_ok(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    errs = assert_claims(
        root,
        "当前做不到真正的 Boss 战（没有 Boss 敌人能力）",
        ["请换一句已有玩法试试"],
        [],
        genre="platformer",
    )
    assert errs == []


def test_assert_claims_accepts_real_boss_script(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    (root / "core" / "boss_enemy.gd").write_text(
        "extends CharacterBody2D\n"
        "var max_hp: int = 20\n"
        "var boss_hp: int = 20\n"
        "func take_damage(n: int) -> void:\n\tboss_hp -= n\n",
        encoding="utf-8",
    )
    errs = assert_claims(
        root,
        "已加关底 Boss，有血条",
        ["重开后走到关底打 Boss"],
        ["core/boss_enemy.gd"],
        genre="platformer",
    )
    assert errs == []


def test_done_gate_requires_reply_to_problem_turn(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    (root / "core" / "fix.gd").write_text("extends Node\n", encoding="utf-8")
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=["core/fix.gd"],
        summary="已添加炸弹技能，不改变原有子弹",
        how_to_play=["重开后点屏幕下方炸弹按钮"],
        genre="shmup",
        contract=c,
        catalog_changed=True,
        user_text="游戏没法正常启动，点击开始游戏按钮看不到画面",
    )
    assert errs
    assert any("本轮" in e or "回应" in e for e in errs)


def test_assert_claims_passes_with_bridge_impl(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core" / "ai_sandbox").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"tuning": {"enabled_skills": ["bomb", "laser_beam"]}}),
        encoding="utf-8",
    )
    (root / "core" / "ai_sandbox" / "rainbow.gd").write_text(
        "extends Node\nfunc apply(bridge) -> void:\n\tbridge.rainbow_player_bullets()\n\tbridge.grant_temp_shield(8.0)\n",
        encoding="utf-8",
    )
    errs = assert_claims(
        root,
        "子弹五颜六色，并加了临时护盾",
        ["重开后自动彩色子弹；点屏幕下方按钮开护盾倒计时"],
        ["core/ai_sandbox/rainbow.gd"],
        genre="shmup",
    )
    assert errs == []


def test_done_gate_blocks_empty_write(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=[],
        summary="好了",
        how_to_play=["请重新启动游戏", "点屏幕下方按钮试用"],
        genre="shmup",
        contract=c,
        catalog_changed=False,
    )
    assert any("写入" in e for e in errs)


def test_emit_progress_writes_file(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    seen: list[tuple[str, str, str]] = []

    def _cb(stage: str, title: str, detail: str) -> None:
        seen.append((stage, title, detail))

    payload = emit_progress(
        root, "validate", "检查幻想 API", on_progress=_cb, log=False
    )
    assert payload["title"] == PROGRESS_STAGES["validate"][0]
    disk = json.loads((root / ".agent_progress.json").read_text(encoding="utf-8"))
    assert disk["stage"] == "validate"
    assert seen and seen[0][0] == "validate"


def test_genre_context_allows_session_core(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    (templates / "shmup" / "core").mkdir(parents=True)
    (templates / "shmup" / "core" / "player_ship.gd").write_text(
        "extends Area2D\n", encoding="utf-8"
    )
    (templates / "shmup" / "config").mkdir(parents=True)
    (templates / "shmup" / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    ctx = build_genre_llm_context(templates, "shmup")
    assert "禁止修改 templates" in ctx
    assert "可改" in ctx or "会话" in ctx
    assert "禁止修改 templates 与已有 core" not in ctx
    assert "禁止改已有 core" not in ctx
    assert "tint_player_bullets" in ctx or "grant_temp_shield" in ctx
    assert "player_ship" in ctx


def test_assert_player_presence_blocks_bad_paths(tmp_path: Path) -> None:
    """HF-10：../Player 与玩家根 visible=false 须被门禁拦住。"""
    from app.services.creative.agent_contracts import (
        assert_player_presence_health,
        restore_last_playable_snapshot,
        save_last_playable_snapshot,
        validate_player_write_content,
    )

    root = tmp_path / "ws"
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    good_script = "extends CharacterBody2D\nfunc _ready() -> void:\n\tpass\n"
    good_scene = (
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n'
        '[node name="Sprite2D" type="Sprite2D" parent="."]\n'
    )
    (root / "core" / "player_runner.gd").write_text(good_script, encoding="utf-8")
    (root / "scenes" / "player.tscn").write_text(good_scene, encoding="utf-8")
    assert assert_player_presence_health(root, "parkour") == []

    bad_hooks = (
        "extends Node\n"
        "func _ready() -> void:\n"
        '\tvar p = get_node("../Player")\n'
        "\tp.visible = false\n"
    )
    (root / "core" / "parkour_hooks.gd").write_text(bad_hooks, encoding="utf-8")
    errs = assert_player_presence_health(root, "parkour")
    assert any("../Player" in e or "Main/Player" in e for e in errs)
    assert any("visible=false" in e for e in errs)

    write_errs = validate_player_write_content(
        "core/parkour_hooks.gd", bad_hooks, "parkour"
    )
    assert write_errs

    (root / "core" / "parkour_hooks.gd").write_text("extends Node\n", encoding="utf-8")
    assert save_last_playable_snapshot(root, "parkour") is True
    (root / "core" / "player_runner.gd").write_text(
        "extends CharacterBody2D\nfunc _ready() -> void:\n\tself.visible = false\n",
        encoding="utf-8",
    )
    assert assert_player_presence_health(root, "parkour")
    restored = restore_last_playable_snapshot(root, "parkour")
    assert "core/player_runner.gd" in restored
    assert assert_player_presence_health(root, "parkour") == []


def test_genre_playbook_warns_player_path() -> None:
    from app.config import ROOT_DIR

    for genre in ("shmup", "platformer", "parkour"):
        ctx = build_genre_llm_context(ROOT_DIR / "templates", genre)
        assert "get_nodes_in_group" in ctx or "get_player_node" in ctx
        assert "../Player" in ctx or "Main/Player" in ctx
