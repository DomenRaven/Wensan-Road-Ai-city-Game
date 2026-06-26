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
    (templates_dir / "platformer" / "core").mkdir(parents=True, exist_ok=True)
    (templates_dir / "platformer" / "core" / "player_platformer.gd").write_text(
        "extends CharacterBody2D\n\nfunc _physics_process(delta: float) -> void:\n\tpass\n",
        encoding="utf-8",
    )

    _write_json(
        config_dir / "creative_templates" / "platformer.json",
        {
            "version": "1.0",
            "genre": "platformer",
            "display_name": "横版闯关",
            "name_suggestions": ["星星大冒险"],
            "questions": [
                {
                    "id": "q_move",
                    "widget": "single_choice",
                    "options": [
                        {
                            "id": "default",
                            "tuning_path": "tuning.player.move_speed",
                            "value": 200,
                            "code_anchor_id": "move",
                        },
                    ],
                },
                {
                    "id": "q_jump",
                    "widget": "single_choice",
                    "options": [
                        {
                            "id": "default",
                            "tuning_path": "tuning.player.jump_velocity",
                            "value": -400,
                            "code_anchor_id": "jump",
                        },
                    ],
                },
                {
                    "id": "q_enemy",
                    "widget": "single_choice",
                    "options": [
                        {
                            "id": "default",
                            "tuning_path": "tuning.enemy.patrol_speed",
                            "value": 50,
                            "code_anchor_id": "enemy_patrol",
                        },
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
            }
        },
    )

    _write_json(
        config_dir / "intent_genre_lexicon.json",
        {"genres": {"platformer": {"keywords": ["马里奥", "闯关"], "weight": 1.0}}},
    )
    _write_json(
        config_dir / "optional_skills.json",
        {"rules": {"max_skills_per_session": 2}, "catalog": {"platformer": []}},
    )

    return templates_dir, workspace_dir, config_dir


def _create_client(tmp_path: Path, monkeypatch) -> TestClient:
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
    return TestClient(create_app())


def _bootstrap_platformer_session(client: TestClient, display_name: str = "星星大冒险") -> str:
    created = client.post("/sessions")
    assert created.status_code == 201
    session_id: str = created.json()["session_id"]

    intent_resp = client.post(
        "/intent/match-genre",
        json={"text": "马里奥闯关", "session_id": session_id},
    )
    assert intent_resp.status_code == 200

    name_resp = client.post(
        f"/sessions/{session_id}/wizard/S0",
        json={"data": {"display_name": display_name}},
    )
    assert name_resp.status_code == 200

    answers_resp = client.post(
        f"/sessions/{session_id}/creative/answers",
        json={"answers": {"q_move": "default", "q_jump": "default", "q_enemy": "default"}},
    )
    assert answers_resp.status_code == 200

    analyze_resp = client.post(f"/sessions/{session_id}/analyze-requirements")
    assert analyze_resp.status_code == 200

    generate_resp = client.post(f"/sessions/{session_id}/generate/v2")
    assert generate_resp.status_code == 200
    assert generate_resp.json()["ok"] is True
    return session_id


def test_workspace_game_config_returns_full_json(tmp_path: Path, monkeypatch) -> None:
    display_name = "星星大冒险"
    with _create_client(tmp_path, monkeypatch) as client:
        session_id = _bootstrap_platformer_session(client, display_name)

        resp = client.get(f"/sessions/{session_id}/workspace/game-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["genre"] == "platformer"
        assert data["path"] == "config/game_config.json"

        parsed = json.loads(data["content"])
        assert parsed["meta"]["display_name"] == display_name
        assert "jump_velocity" in data["content"]
        assert "move_speed" in data["content"]


def test_workspace_game_config_404_without_workspace(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        session_id: str = created.json()["session_id"]

        resp = client.get(f"/sessions/{session_id}/workspace/game-config")
        assert resp.status_code == 404
        assert "game_config" in resp.json()["detail"]


def test_workspace_game_config_404_unknown_session(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        resp = client.get(
            "/sessions/00000000-0000-4000-8000-000000000001/workspace/game-config"
        )
        assert resp.status_code == 404


def test_workspace_file_returns_core_gd(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        session_id = _bootstrap_platformer_session(client)

        resp = client.get(
            f"/sessions/{session_id}/workspace/file",
            params={"rel_path": "core/player_platformer.gd"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["path"] == "core/player_platformer.gd"
        assert "CharacterBody2D" in data["content"]


def test_workspace_file_rejects_path_traversal(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        session_id = _bootstrap_platformer_session(client)

        resp = client.get(
            f"/sessions/{session_id}/workspace/file",
            params={"rel_path": "../templates/platformer/project.godot"},
        )
        assert resp.status_code == 400
