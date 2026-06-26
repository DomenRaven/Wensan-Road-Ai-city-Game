from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.creative import loader


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_fixture_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates_dir: Path = tmp_path / "templates"
    workspace_dir: Path = tmp_path / "workspace"
    config_dir: Path = tmp_path / "config"

    _write_json(
        templates_dir / "platformer" / "config" / "game_config.json",
        {
            "meta": {"genre": "platformer", "session_id": "", "display_name": "测试平台跳跃"},
            "tuning": {
                "player": {"move_speed": 200, "jump_velocity": -400},
                "enemy": {"patrol_speed": 50},
                "enabled_skills": [],
            },
            "theme": {"title": "测试平台跳跃"},
        },
    )
    (templates_dir / "platformer" / "project.godot").parent.mkdir(parents=True, exist_ok=True)
    (templates_dir / "platformer" / "project.godot").write_text(
        "config_version=5\n",
        encoding="utf-8",
    )

    _write_json(
        config_dir / "creative_templates" / "platformer.json",
        {
            "version": "1.0",
            "genre": "platformer",
            "display_name": "横版闯关",
            "name_suggestions": ["星星大冒险", "跳跳小子"],
            "questions": [
                {
                    "id": "q_move",
                    "widget": "single_choice",
                    "options": [
                        {"id": "slow", "tuning_path": "tuning.player.move_speed", "value": 170, "code_anchor_id": "move"},
                        {"id": "default", "tuning_path": "tuning.player.move_speed", "value": 200, "code_anchor_id": "move"},
                        {"id": "fast", "tuning_path": "tuning.player.move_speed", "value": 240, "code_anchor_id": "move"},
                    ],
                },
                {
                    "id": "q_jump",
                    "widget": "single_choice",
                    "options": [
                        {"id": "low", "tuning_path": "tuning.player.jump_velocity", "value": -360, "code_anchor_id": "jump"},
                        {"id": "default", "tuning_path": "tuning.player.jump_velocity", "value": -400, "code_anchor_id": "jump"},
                        {"id": "high", "tuning_path": "tuning.player.jump_velocity", "value": -440, "code_anchor_id": "jump"},
                    ],
                },
                {
                    "id": "q_enemy",
                    "widget": "single_choice",
                    "options": [
                        {"id": "easy", "tuning_path": "tuning.enemy.patrol_speed", "value": 40, "code_anchor_id": "enemy_patrol"},
                        {"id": "default", "tuning_path": "tuning.enemy.patrol_speed", "value": 50, "code_anchor_id": "enemy_patrol"},
                        {"id": "hard", "tuning_path": "tuning.enemy.patrol_speed", "value": 65, "code_anchor_id": "enemy_patrol"},
                    ],
                },
            ],
        },
    )

    _write_json(
        config_dir / "code_anchors" / "platformer.json",
        {
            "anchors": {
                "move": {
                    "file": "config/game_config.json",
                    "path": "tuning.player.move_speed",
                    "line_hint": 10,
                    "caption": "移动速度",
                },
                "jump": {
                    "file": "config/game_config.json",
                    "path": "tuning.player.jump_velocity",
                    "line_hint": 11,
                    "caption": "跳跃力度",
                },
                "enemy_patrol": {
                    "file": "config/game_config.json",
                    "path": "tuning.enemy.patrol_speed",
                    "line_hint": 14,
                    "caption": "敌人巡逻速度",
                },
            }
        },
    )

    _write_json(
        config_dir / "intent_genre_lexicon.json",
        {
            "genres": {
                "platformer": {
                    "keywords": ["马里奥", "闯关", "跳"],
                    "weight": 1.0,
                    "reply_text": "听起来你想玩横版闯关！",
                },
                "shmup": {"keywords": ["打飞机", "射击"], "weight": 1.0},
            }
        },
    )
    _write_json(
        config_dir / "optional_skills.json",
        {
            "rules": {"max_skills_per_session": 2},
            "catalog": {"platformer": [{"id": "double_jump"}, {"id": "ground_pound"}]},
        },
    )

    return templates_dir, workspace_dir, config_dir


def test_creative_platformer_end_to_end(tmp_path: Path, monkeypatch) -> None:
    templates_dir, workspace_dir, config_dir = _prepare_fixture_tree(tmp_path)

    settings = Settings(
        templates_dir=templates_dir,
        workspace_dir=workspace_dir,
        max_sessions=5,
        allow_memory_fallback=True,
    )

    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr(loader, "CONFIG_DIR", config_dir)
    loader.load_creative_template.cache_clear()
    loader.load_code_anchors.cache_clear()
    loader.load_intent_lexicon.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        created = client.post("/sessions")
        assert created.status_code == 201
        session_id: str = created.json()["session_id"]

        intent_resp = client.post(
            "/intent/match-genre",
            json={"text": "我想玩马里奥闯关", "session_id": session_id},
        )
        assert intent_resp.status_code == 200
        assert intent_resp.json()["matched_genre"] == "platformer"

        tpl_resp = client.get("/creative/templates/platformer")
        assert tpl_resp.status_code == 200
        assert tpl_resp.json()["genre"] == "platformer"

        names_resp = client.get("/creative/name-suggestions", params={"genre": "platformer"})
        assert names_resp.status_code == 200
        assert len(names_resp.json()["suggestions"]) == 2

        answers_resp = client.post(
            f"/sessions/{session_id}/creative/answers",
            json={"answers": {"q_move": "fast", "q_jump": "high", "q_enemy": "hard"}},
        )
        assert answers_resp.status_code == 200

        analyze_resp = client.post(f"/sessions/{session_id}/analyze-requirements")
        assert analyze_resp.status_code == 200
        analyze_data = analyze_resp.json()
        assert analyze_data["llm_patch_required"] is False
        assert len(analyze_data["resolutions"]) == 3
        assert "jump" in analyze_data["code_map_preview"]

        generate_resp = client.post(f"/sessions/{session_id}/generate/v2")
        assert generate_resp.status_code == 200
        generated = generate_resp.json()
        assert generated["ok"] is True
        assert generated["genre"] == "platformer"
        assert "jump" in generated["code_map"]

        config_path = Path(generated["config_path"])
        merged = json.loads(config_path.read_text(encoding="utf-8"))
        assert merged["tuning"]["player"]["move_speed"] == 240
        assert merged["tuning"]["player"]["jump_velocity"] == -440
        assert merged["tuning"]["enemy"]["patrol_speed"] == 65
