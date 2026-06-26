from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.creative import loader
from app.services.edu_workspace import EDU_ACTIONS_LOG, append_edu_action, read_edu_actions


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
            "name_suggestions": ["星星大冒险"],
            "questions": [
                {
                    "id": "q_move",
                    "widget": "single_choice",
                    "options": [
                        {"id": "default", "tuning_path": "tuning.player.move_speed", "value": 200, "code_anchor_id": "move"},
                    ],
                },
                {
                    "id": "q_jump",
                    "widget": "single_choice",
                    "options": [
                        {"id": "default", "tuning_path": "tuning.player.jump_velocity", "value": -400, "code_anchor_id": "jump"},
                    ],
                },
                {
                    "id": "q_enemy",
                    "widget": "single_choice",
                    "options": [
                        {"id": "default", "tuning_path": "tuning.enemy.patrol_speed", "value": 50, "code_anchor_id": "enemy_patrol"},
                    ],
                },
            ],
        },
    )

    _write_json(
        config_dir / "code_anchors" / "platformer.json",
        {
            "anchors": {
                "move": {"file": "config/game_config.json", "path": "tuning.player.move_speed", "line_hint": 10, "caption": "移动速度"},
                "jump": {"file": "config/game_config.json", "path": "tuning.player.jump_velocity", "line_hint": 11, "caption": "跳跃力度"},
                "enemy_patrol": {"file": "config/game_config.json", "path": "tuning.enemy.patrol_speed", "line_hint": 14, "caption": "敌人巡逻速度"},
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


def test_append_edu_action_writes_jsonl(tmp_path: Path) -> None:
    workspace_root: Path = tmp_path / "ws"
    workspace_root.mkdir()
    t_ms: int = append_edu_action(workspace_root, "jump")
    assert t_ms > 0
    log_path: Path = workspace_root / EDU_ACTIONS_LOG
    assert log_path.is_file()
    line: str = log_path.read_text(encoding="utf-8").strip()
    row: dict[str, object] = json.loads(line)
    assert row == {"action_id": "jump", "t_ms": t_ms}
    events: list[dict[str, object]] = read_edu_actions(workspace_root, since_ms=0)
    assert len(events) == 1
    assert events[0]["action_id"] == "jump"


def test_play_action_post_then_get_actions(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        assert created.status_code == 201
        session_id: str = created.json()["session_id"]

        intent_resp = client.post(
            "/intent/match-genre",
            json={"text": "马里奥闯关", "session_id": session_id},
        )
        assert intent_resp.status_code == 200

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

        action_resp = client.post(
            f"/sessions/{session_id}/play/action",
            json={"action_id": "jump"},
        )
        assert action_resp.status_code == 200
        action_data = action_resp.json()
        assert action_data["ok"] is True
        assert action_data["action_id"] == "jump"
        assert action_data["t_ms"] > 0

        list_resp = client.get(f"/sessions/{session_id}/play/actions", params={"since": 0})
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        action_ids: list[str] = [str(row["action_id"]) for row in list_data["actions"]]
        assert "jump" in action_ids

        since_resp = client.get(
            f"/sessions/{session_id}/play/actions",
            params={"since": action_data["t_ms"]},
        )
        assert since_resp.status_code == 200
        assert since_resp.json()["actions"] == []


def test_play_action_rejects_empty_action_id(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        session_id: str = created.json()["session_id"]
        resp = client.post(f"/sessions/{session_id}/play/action", json={"action_id": "  "})
        assert resp.status_code == 400


def test_play_action_requires_workspace(tmp_path: Path, monkeypatch) -> None:
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        session_id: str = created.json()["session_id"]
        resp = client.post(f"/sessions/{session_id}/play/action", json={"action_id": "jump"})
        assert resp.status_code == 400
