"""七品类 catalog 快车道：点名开技能不得掉进多轮 LLM。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.creative.agent_contracts import load_contract
from app.services.creative.game_agent import (
    _can_catalog_express,
    _run_catalog_express,
    run_game_agent,
)
from app.services.creative.intent_router import route_intent
from app.services.config_builder import load_optional_skills_catalog

# 每品类：口语 → 期望 skill_id
_EXPRESS_CASES: list[tuple[str, str, str]] = [
    ("platformer", "我想加二段跳", "double_jump"),
    ("platformer", "开下砸", "ground_pound"),
    ("shmup", "我想加发射激光", "laser_beam"),
    ("shmup", "来个炸弹", "bomb"),
    ("survivor", "开磁铁", "magnet"),
    ("survivor", "环形爆发", "nova"),
    ("parkour", "加滑铲", "slide"),
    ("parkour", "开二段跳", "double_jump"),
    ("pingpong", "大力扣杀", "power_smash"),
    ("pingpong", "旋转球", "curve_ball"),
    ("fighting", "开格挡", "block_parry"),
    ("fighting", "上勾拳", "special_uppercut"),
    ("racing", "开氮气", "boost"),
    ("racing", "漂移", "drift_snap"),
]


def _settings(templates: Path, workspace: Path) -> Settings:
    learned = workspace.parent / "learned_express"
    learned.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        allow_memory_fallback=True,
        llm_api_key="sk-test",
        llm_base_url="https://example.invalid/v1",
        llm_model="test",
        llm_timeout_sec=5.0,
    )


def _session_for_genre(tmp_path: Path, genre: str) -> tuple[Path, Path, Path]:
    from app.services.creative.agent_contracts import PLAYER_PRESENCE_BY_GENRE

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    cfg = {
        "meta": {"genre": genre},
        "tuning": {"enabled_skills": [], "player": {"move_speed": 200}},
        "theme": {"title": "测"},
    }
    (templates / genre / "config").mkdir(parents=True)
    (templates / genre / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    # 最小 _edu 桥/触屏，供快车道拷贝
    edu = templates / "_edu"
    edu.mkdir(parents=True, exist_ok=True)
    (edu / "ai_sandbox_bridge.gd").write_text(
        "extends Node\nfunc ensure_touch_action(a,b):\n\tpass\n",
        encoding="utf-8",
    )
    (edu / f"{genre}_touch_overlay.gd").write_text(
        "extends CanvasLayer\n", encoding="utf-8"
    )
    root = workspace / f"{genre}-sess"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    (root / "core").mkdir(parents=True)
    # HF-10：快车道 done 门禁要玩家健康；补最小脚本/场景
    presence = PLAYER_PRESENCE_BY_GENRE.get(genre) or {}
    script_rel = str(presence.get("script") or "")
    scene_rel = str(presence.get("scene") or "scenes/player.tscn")
    node = str(presence.get("scene_node") or "Player")
    if script_rel:
        sp = root / script_rel
        sp.parent.mkdir(parents=True, exist_ok=True)
        body = "extends Node\n"
        if genre == "survivor":
            body = 'extends Area2D\nfunc _ready() -> void:\n\tadd_to_group("player")\n'
        elif genre == "pingpong":
            body = "extends Area2D\n"
        elif genre == "racing":
            body = "extends Node2D\n"
        else:
            body = "extends CharacterBody2D\n"
        sp.write_text(body, encoding="utf-8")
    sc = root / scene_rel
    sc.parent.mkdir(parents=True, exist_ok=True)
    if genre == "pingpong":
        sc.write_text(
            f'[gd_scene load_steps=1 format=3]\n'
            f'[node name="Game" type="Node2D"]\n'
            f'[node name="{node}" type="Area2D" parent="."]\n'
            f'[node name="Sprite" type="Sprite2D" parent="{node}"]\n'
            f'[node name="Visual" type="ColorRect" parent="{node}"]\n',
            encoding="utf-8",
        )
    elif genre == "survivor":
        sc.write_text(
            f'[gd_scene load_steps=2 format=3]\n'
            f'[node name="{node}" type="Area2D"]\n'
            f'[node name="Sprite2D" type="Sprite2D" parent="."]\n',
            encoding="utf-8",
        )
    elif genre == "fighting":
        sc.write_text(
            f'[gd_scene load_steps=2 format=3]\n'
            f'[node name="{node}" type="CharacterBody2D" groups=["player"]]\n'
            f'[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]\n',
            encoding="utf-8",
        )
    else:
        sc.write_text(
            f'[gd_scene load_steps=2 format=3]\n'
            f'[node name="{node}" type="CharacterBody2D" groups=["player"]]\n'
            f'[node name="Sprite2D" type="Sprite2D" parent="."]\n',
            encoding="utf-8",
        )
    return templates, workspace, root


@pytest.mark.parametrize("genre,text,skill_id", _EXPRESS_CASES)
def test_route_and_express_eligible(genre: str, text: str, skill_id: str) -> None:
    contract = load_contract(genre)
    catalog = set(load_optional_skills_catalog().get(genre, []))
    assert skill_id in catalog
    assert any(s.get("id") == skill_id for s in contract.get("catalog_skills") or [])

    route = route_intent(text, contract)
    assert route["intent"] == "A", f"{genre}:{text} -> {route}"
    assert skill_id in route["skill_ids"]
    assert _can_catalog_express(route, text, "") is True


@pytest.mark.parametrize("genre,text,skill_id", _EXPRESS_CASES)
def test_express_runs_without_llm(tmp_path: Path, genre: str, text: str, skill_id: str) -> None:
    templates, workspace, root = _session_for_genre(tmp_path, genre)
    settings = _settings(templates, workspace)
    contract = load_contract(genre)
    route = route_intent(text, contract)

    with patch("app.services.creative.game_agent._llm_turn") as llm:
        with patch(
            "app.services.creative.game_agent.refresh_ai_sandbox_bridge",
            return_value=True,
        ):
            out = _run_catalog_express(
                settings, root, genre, text, route, contract
            )
    assert out["ok"] is True
    assert out.get("express") is True
    assert out["agent_rounds"] == 0
    assert skill_id in (out.get("applied_capabilities") or [])
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert skill_id in cfg["tuning"]["enabled_skills"]
    llm.assert_not_called()


def test_bugfix_does_not_express() -> None:
    c = load_contract("shmup")
    text = "激光按钮没反应，只有键盘可以"
    r = route_intent(text, c)
    assert r["intent"] != "A" or not _can_catalog_express(r, text, "")


def test_run_game_agent_platformer_express_no_llm(tmp_path: Path) -> None:
    templates, workspace, root = _session_for_genre(tmp_path, "platformer")
    settings = _settings(templates, workspace)
    with patch("app.services.creative.game_agent._llm_turn") as llm:
        with patch(
            "app.services.creative.game_agent.refresh_ai_sandbox_bridge",
            return_value=True,
        ):
            out = run_game_agent(settings, root, "platformer", "我想加二段跳")
    assert out.get("express") is True
    assert out["agent_rounds"] == 0
    llm.assert_not_called()
