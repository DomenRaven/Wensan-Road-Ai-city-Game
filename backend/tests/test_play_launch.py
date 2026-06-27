from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.creative import loader
from app.services.godot_launcher import LaunchResult


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
            "questions": [],
        },
    )
    _write_json(config_dir / "code_anchors" / "platformer.json", {"anchors": {}})
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


@dataclass
class _FakeLauncher:
    last_layout_rect: dict[str, int] | None = None

    def launch(
        self,
        session_id: str,
        genre: str,
        *,
        force: bool = False,
        layout_rect: dict[str, int] | None = None,
    ) -> LaunchResult:
        self.last_layout_rect = layout_rect
        return LaunchResult(
            ok=True,
            pid=4242,
            project_path="/tmp/project",
            genre=genre,
            godot_path="/tmp/godot",
            message="已启动 Godot 试玩窗口",
            already_running=False,
            window_placed=layout_rect is not None,
            placement_rect=layout_rect,
        )

    def status(self, session_id: str) -> dict[str, object]:
        return {"session_id": session_id, "pid": 4242, "running": True, "project_path": "/tmp/project"}


def test_play_launch_empty_body_backward_compatible(tmp_path: Path, monkeypatch) -> None:
    fake = _FakeLauncher()
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        session_id: str = created.json()["session_id"]
        client.post(
            "/intent/match-genre",
            json={"text": "马里奥闯关", "session_id": session_id},
        )
        with patch("app.routers.play.get_launcher", return_value=fake):
            resp = client.post(f"/sessions/{session_id}/play/launch", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["window_placed"] is False
        assert data["placement_rect"] is None
        assert fake.last_layout_rect is None


def test_play_launch_with_viewport_passes_layout_rect(tmp_path: Path, monkeypatch) -> None:
    fake = _FakeLauncher()
    with _create_client(tmp_path, monkeypatch) as client:
        created = client.post("/sessions")
        session_id: str = created.json()["session_id"]
        client.post(
            "/intent/match-genre",
            json={"text": "马里奥闯关", "session_id": session_id},
        )
        body = {
            "orientation": "landscape",
            "client_viewport": {
                "screen_x": 0,
                "screen_y": 0,
                "screen_w": 1920,
                "screen_h": 1080,
                "devicePixelRatio": 1.0,
                "godot_zone_rect": {"x": 960, "y": 80, "w": 960, "h": 1000},
            },
        }
        with patch("app.routers.play.get_launcher", return_value=fake):
            resp = client.post(f"/sessions/{session_id}/play/launch", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["window_placed"] is True
        assert data["placement_rect"] == {"x": 960, "y": 80, "w": 960, "h": 1000}
        assert fake.last_layout_rect == {"x": 960, "y": 80, "w": 960, "h": 1000}
