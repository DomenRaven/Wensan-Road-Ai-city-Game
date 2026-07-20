"""HF-15：预言机分层 · L1 加固 + L2 表现谓词。"""

from __future__ import annotations

from pathlib import Path

from app.services.creative.agent_contracts import (
    assert_evidence_wired,
    assert_presentation_predicates,
    load_contract,
    run_done_gates,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_l1_rejects_slash_wired_by(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "core" / "ship.gd",
        "extends Node\n"
        "func _ready() -> void:\n"
        "\tadd_life()\n"
        "func add_life() -> void:\n"
        "\tupdate_lives_display()\n"
        "func update_lives_display() -> void:\n"
        "\tpass\n",
    )
    evidence = [
        {
            "goal": "命数显示",
            "path": "core/ship.gd",
            "symbol": "update_lives_display",
            "wired_by": "_ready / add_life / hit_by_enemy_body",
        }
    ]
    errs = assert_evidence_wired(root, evidence, require=True)
    assert errs
    assert any("/" in e or "A|B" in e for e in errs)


def test_l1_accepts_indirect_call(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "core" / "ship.gd",
        "extends Node\n"
        "func hit_by_enemy_body() -> void:\n"
        "\ttake_hit()\n"
        "func take_hit() -> void:\n"
        "\tupdate_lives_display()\n"
        "func update_lives_display() -> void:\n"
        "\tpass\n",
    )
    evidence = [
        {
            "goal": "命数显示",
            "path": "core/ship.gd",
            "symbol": "update_lives_display",
            "wired_by": "hit_by_enemy_body",
        }
    ]
    assert assert_evidence_wired(root, evidence, require=True) == []


def test_l1_multi_wired_by_any(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "core" / "a.gd",
        "extends Node\n"
        "func foo() -> void:\n"
        "\tpass\n"
        "func bar() -> void:\n"
        "\t_update_x()\n"
        "func _update_x() -> void:\n"
        "\tpass\n",
    )
    evidence = [
        {
            "path": "core/a.gd",
            "symbol": "_update_x",
            "wired_by": "foo|bar",
        }
    ]
    assert assert_evidence_wired(root, evidence, require=True) == []


def test_l2_empty_texture_rect_fails(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "scenes" / "hud.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="HUD" type="Control"]\n'
        '[node name="LifeIcon1" type="TextureRect" parent="."]\n'
        "visible = true\n",
    )
    _write(
        root / "core" / "hud.gd",
        "extends Control\n"
        "func update_lives_display() -> void:\n"
        "\t$LifeIcon1.visible = true\n",
    )
    errs = assert_presentation_predicates(
        root,
        goals=["显示命数图标"],
        user_text="",
    )
    assert errs
    assert any("L2 图标" in e for e in errs)


def test_l2_progress_no_value_write_fails(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "scenes" / "hud.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="HUD" type="Control"]\n'
        '[node name="UltBar" type="ProgressBar" parent="."]\n',
    )
    _write(
        root / "core" / "hud.gd",
        "extends Control\n"
        "func _physics_process(delta: float) -> void:\n"
        "\t_update_ultimate_progress_bar()\n"
        "func _update_ultimate_progress_bar() -> void:\n"
        "\tpass\n",
    )
    errs = assert_presentation_predicates(
        root,
        goals=["大招进度条"],
        user_text="",
    )
    assert errs
    assert any("L2 进度条" in e for e in errs)


def test_l2_skipped_without_keywords(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "scenes" / "hud.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="LifeIcon1" type="TextureRect" parent="."]\n',
    )
    assert (
        assert_presentation_predicates(
            root,
            goals=["让飞机更酷"],
            user_text="",
        )
        == []
    )


def test_l2_progress_value_write_passes(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    _write(
        root / "scenes" / "hud.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="UltBar" type="ProgressBar" parent="."]\n',
    )
    _write(
        root / "core" / "hud.gd",
        "extends Control\n"
        "func _physics_process(delta: float) -> void:\n"
        "\t$UltBar.value += delta\n",
    )
    assert (
        assert_presentation_predicates(
            root,
            goals=["充能条"],
        )
        == []
    )


def test_hf14_half_wired_still_fails(tmp_path: Path) -> None:
    """HF-14 半成品无敌案：L1 仍不过。"""
    root = tmp_path / "ws"
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "var _god_mode_active: bool = false\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n",
    )
    evidence = [
        {
            "goal": "每过20秒进入无敌",
            "path": "core/player_ship.gd",
            "symbol": "_update_god_mode",
            "wired_by": "_process",
        }
    ]
    errs = assert_evidence_wired(root, evidence, require=True)
    assert errs


def test_run_done_gates_includes_l2_errors(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    _write(
        root / "scenes" / "hud.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="UltBar" type="ProgressBar" parent="."]\n',
    )
    _write(
        root / "core" / "hud.gd",
        "extends Node\n"
        "func _physics_process(delta: float) -> void:\n"
        "\tpass\n",
    )
    c = load_contract("platformer")
    errs = run_done_gates(
        root,
        written_paths=["core/hud.gd"],
        summary="已加进度条",
        how_to_play=["请重新启动游戏后拖动角色试玩"],
        genre="platformer",
        contract=c,
        user_text="加一条进度条",
        goals=["加一条进度条"],
        evidence=[],
        require_evidence=False,
    )
    assert any("L2 进度条" in e for e in errs)


def test_slash_wired_by_fixed_declaration_passes(tmp_path: Path) -> None:
    """修好 wired_by 声明后，间接接线代码可通过 L1。"""
    root = tmp_path / "ws"
    _write(
        root / "core" / "ship.gd",
        "extends Node\n"
        "func hit_by_enemy_body() -> void:\n"
        "\ttake_hit()\n"
        "func take_hit() -> void:\n"
        "\tupdate_lives_display()\n"
        "func update_lives_display() -> void:\n"
        "\tpass\n",
    )
    evidence = [
        {
            "path": "core/ship.gd",
            "symbol": "update_lives_display",
            "wired_by": "hit_by_enemy_body|take_hit",
        }
    ]
    assert assert_evidence_wired(root, evidence, require=True) == []
