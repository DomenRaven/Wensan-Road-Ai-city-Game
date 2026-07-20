"""HF-14：evidence 协议 · 接线硬核 · 反馈轮真差分。"""

from __future__ import annotations

from pathlib import Path

from app.services.creative.agent_contracts import (
    assert_evidence_wired,
    assert_feedback_has_real_diff,
    load_contract,
    normalize_evidence_list,
    run_done_gates,
    summaries_near_duplicate,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.replace("\n", "\n"), encoding="utf-8")


def test_normalize_evidence_list_filters_junk() -> None:
    raw = [
        {"path": "core/a.gd", "symbol": "_update_x", "wired_by": "_process", "goal": "g"},
        "bad",
        {"path": "", "symbol": ""},
        {"missing": True, "goal": "未完成"},
    ]
    items = normalize_evidence_list(raw)
    assert len(items) == 2
    assert items[0]["symbol"] == "_update_x"
    assert items[1]["missing"] is True


def test_s1_require_evidence_empty_fails(tmp_path: Path) -> None:
    errs = assert_evidence_wired(tmp_path, [], require=True)
    assert errs
    assert any("evidence" in e for e in errs)


def test_s1_missing_flag_blocks_done(tmp_path: Path) -> None:
    errs = assert_evidence_wired(
        tmp_path,
        [{"goal": "无敌", "missing": True}],
        require=True,
    )
    assert any("missing" in e for e in errs)


def test_s2_ag1_half_done_no_update_fn(tmp_path: Path) -> None:
    """AG-1 T1 形态：有 _god_mode_active 检查，无 _update_god_mode → 接线失败。"""
    root = tmp_path / "ws"
    ship = root / "core" / "player_ship.gd"
    _write(
        ship,
        "extends CharacterBody2D\n"
        "var _god_mode_active: bool = false\n"
        "func _ready() -> void:\n"
        "\tpass\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
        "func take_damage() -> void:\n"
        "\tif _god_mode_active:\n"
        "\t\treturn\n",
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
    assert any("未定义" in e or "接线失败" in e for e in errs)


def test_s2_ag1_flag_not_wired_in_process(tmp_path: Path) -> None:
    """仅效果分支读 flag、_process 未引用 → 失败。"""
    root = tmp_path / "ws"
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "var _god_mode_active: bool = false\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
        "func take_damage() -> void:\n"
        "\tif _god_mode_active:\n"
        "\t\treturn\n",
    )
    evidence = [
        {
            "goal": "无敌状态",
            "path": "core/player_ship.gd",
            "symbol": "_god_mode_active",
            "wired_by": "_process",
        }
    ]
    errs = assert_evidence_wired(root, evidence, require=True)
    assert any("接线失败" in e for e in errs)


def test_s2_wired_update_passes(tmp_path: Path) -> None:
    """有 _update_god_mode 且 _process 调用 → 过证据门。"""
    root = tmp_path / "ws"
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "var _god_mode_active: bool = false\n"
        "var _god_cd: float = 0.0\n"
        "func _process(delta: float) -> void:\n"
        "\t_update_god_mode(delta)\n"
        "func _update_god_mode(delta: float) -> void:\n"
        "\t_god_cd += delta\n"
        "\tif _god_cd >= 20.0:\n"
        "\t\t_god_mode_active = true\n"
        "\t\t_god_cd = 0.0\n",
    )
    evidence = [
        {
            "goal": "每过20秒进入无敌",
            "path": "core/player_ship.gd",
            "symbol": "_update_god_mode",
            "wired_by": "_process",
            "note": "20s 冷却",
        }
    ]
    assert assert_evidence_wired(root, evidence, require=True) == []


def test_s2_run_done_gates_half_done_blocked(tmp_path: Path) -> None:
    """合成案接入 run_done_gates：半成品 evidence 不能过。"""
    root = tmp_path / "ws"
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text("{}", encoding="utf-8")
    _write(
        root / "core" / "player_ship.gd",
        "extends CharacterBody2D\n"
        "var _god_mode_active: bool = false\n"
        "func _ready() -> void:\n"
        "\tpass\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
        "func _physics_process(delta: float) -> void:\n"
        "\tpass\n"
        "func notify_hazard() -> void:\n"
        "\tpass\n"
        "func apply_powerup(_t: String) -> void:\n"
        "\tpass\n",
    )
    _write(
        root / "scenes" / "player.tscn",
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n'
        '[node name="Sprite2D" type="Sprite2D" parent="."]\n',
    )
    # shmup 关键链可能仍报错；本测只断言 evidence 相关错误一定出现
    c = load_contract("shmup")
    errs = run_done_gates(
        root,
        written_paths=["core/player_ship.gd"],
        summary="已加入每过20秒无敌循环，请重开后试玩",
        how_to_play=["请重新启动游戏后拖动飞机试玩"],
        genre="shmup",
        contract=c,
        catalog_changed=False,
        user_text="每过20秒无敌",
        evidence=[
            {
                "goal": "每过20秒进入无敌",
                "path": "core/player_ship.gd",
                "symbol": "_update_god_mode",
                "wired_by": "_process",
            }
        ],
        require_evidence=True,
        goals=["每过20秒进入无敌"],
    )
    assert any("未定义" in e or "接线失败" in e or "evidence" in e for e in errs)


def test_s2_run_done_gates_require_empty_evidence(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "core").mkdir(parents=True)
    _write(root / "core" / "x.gd", "extends Node\nfunc _ready() -> void:\n\tpass\n")
    c = load_contract("platformer")
    errs = run_done_gates(
        root,
        written_paths=["core/x.gd"],
        summary="改了一点",
        how_to_play=["请重新启动游戏查看"],
        genre="platformer",
        contract=c,
        user_text="没生效",
        evidence=[],
        require_evidence=True,
    )
    assert any("evidence" in e for e in errs)


def test_s3_feedback_no_real_diff(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    rel = "core/player_ship.gd"
    body = (
        "extends CharacterBody2D\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
    )
    _write(root / rel, body)
    before = body.encode("utf-8")
    # 仅加注释：指纹应相同
    _write(
        root / rel,
        "extends CharacterBody2D\n"
        "# 假装修复\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n",
    )
    errs = assert_feedback_has_real_diff(
        root,
        written_paths=[rel],
        pre_turn_snapshot={rel: before},
        summary="已修复每过20秒无敌，请重开试玩",
        previous_summary="已加入每过20秒无敌循环，请重开后试玩",
    )
    assert errs
    assert any("真代码 diff" in e or "近亲复读" in e for e in errs)


def test_s3_feedback_real_diff_ok(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    rel = "core/player_ship.gd"
    before = (
        "extends CharacterBody2D\n"
        "func _process(delta: float) -> void:\n"
        "\tpass\n"
    ).encode("utf-8")
    _write(
        root / rel,
        "extends CharacterBody2D\n"
        "func _process(delta: float) -> void:\n"
        "\t_update_god_mode(delta)\n"
        "func _update_god_mode(delta: float) -> void:\n"
        "\tpass\n",
    )
    errs = assert_feedback_has_real_diff(
        root,
        written_paths=[rel],
        pre_turn_snapshot={rel: before},
        summary="已把 _update_god_mode 接到 _process",
        previous_summary="已加入变量与 HUD",
    )
    assert errs == []


def test_s3_summaries_near_duplicate() -> None:
    assert summaries_near_duplicate(
        "已加入每过20秒无敌循环，请重开后试玩",
        "已加入每过20秒无敌循环，请重开试玩",
    )
    assert not summaries_near_duplicate(
        "已把更新函数接到 _process",
        "已加入 HUD 充能条",
    )
