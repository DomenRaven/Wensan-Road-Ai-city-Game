"""7.20 W7 · S2-路B play_launch_mode=local_share 钩子。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
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


def _create_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    play_launch_mode: str = "server",
) -> TestClient:
    templates_dir, workspace_dir, config_dir = _prepare_fixture_tree(tmp_path)
    settings = Settings(
        templates_dir=templates_dir,
        workspace_dir=workspace_dir,
        max_sessions=5,
        allow_memory_fallback=True,
        play_launch_mode=play_launch_mode,  # type: ignore[arg-type]
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    get_settings.cache_clear()
    monkeypatch.setattr(loader, "CONFIG_DIR", config_dir)
    loader.load_creative_template.cache_clear()
    loader.load_code_anchors.cache_clear()
    loader.load_intent_lexicon.cache_clear()
    return TestClient(create_app())


def _seed_workspace(client: TestClient, session_id: str) -> Path:
    settings = client.app.state.settings
    root = settings.workspace_dir / session_id
    (root / "config").mkdir(parents=True)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (root / "config" / "game_config.json").write_text(
        '{"meta":{"genre":"platformer","display_name":"测"},"theme":{"title":"测"},"tuning":{}}',
        encoding="utf-8",
    )
    rec = client.app.state.session_store.get(session_id)
    assert rec is not None
    payload = dict(rec.payload)
    payload["workspace_path"] = str(root)
    rec.payload = payload
    rec.genre = "platformer"
    client.app.state.session_store.save(rec)
    return root


def test_default_play_launch_mode_is_server() -> None:
    get_settings.cache_clear()
    assert get_settings().play_launch_mode == "server"


def test_local_share_does_not_start_server_godot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = MagicMock()
    fake.launch.return_value = LaunchResult(
        ok=True,
        pid=999,
        project_path="/should-not-use",
        genre="platformer",
        godot_path="/godot",
        message="should not run",
    )
    with _create_client(tmp_path, monkeypatch, play_launch_mode="local_share") as client:
        sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
        root = _seed_workspace(client, sid)
        with patch("app.routers.play.get_launcher", return_value=fake) as get_launcher_mock:
            resp = client.post(f"/sessions/{sid}/play/launch", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True
        assert data["launch_mode"] == "local_share"
        assert data["ready_for_local_godot"] is True
        assert data["pid"] is None
        assert data["godot_path"] == ""
        assert Path(data["project_path"]).resolve() == root.resolve()
        assert "服务器不会" in data["message"] or "本机" in data["message"]
        get_launcher_mock.assert_not_called()
        fake.launch.assert_not_called()

        status = client.get(f"/sessions/{sid}/play/status").json()
        assert status["launch_mode"] == "local_share"
        assert status["server_godot"] is False
        assert status["running"] is False
        assert Path(status["project_path"]).resolve() == root.resolve()


def test_server_mode_still_uses_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = MagicMock()
    fake.launch.return_value = LaunchResult(
        ok=True,
        pid=4242,
        project_path="/tmp/project",
        genre="platformer",
        godot_path="/tmp/godot",
        message="已启动",
        already_running=False,
        window_placed=False,
        placement_rect=None,
    )
    with _create_client(tmp_path, monkeypatch, play_launch_mode="server") as client:
        sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
        client.post(
            "/intent/match-genre",
            json={"text": "马里奥闯关", "session_id": sid},
        )
        with patch("app.routers.play.get_launcher", return_value=fake):
            resp = client.post(f"/sessions/{sid}/play/launch", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["launch_mode"] == "server"
        assert data["ready_for_local_godot"] is False
        assert data["pid"] == 4242
        fake.launch.assert_called_once()


def test_local_share_without_workspace_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _create_client(tmp_path, monkeypatch, play_launch_mode="local_share") as client:
        sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
        rec = client.app.state.session_store.get(sid)
        assert rec is not None
        rec.genre = "platformer"
        client.app.state.session_store.save(rec)
        resp = client.post(f"/sessions/{sid}/play/launch", json={})
        assert resp.status_code == 400
        assert "workspace" in resp.json()["detail"].lower() or "制作" in resp.json()["detail"]


def test_health_exposes_play_launch_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _create_client(tmp_path, monkeypatch, play_launch_mode="local_share") as client:
        body = client.get("/health").json()
        assert body["play_launch_mode"] == "local_share"
