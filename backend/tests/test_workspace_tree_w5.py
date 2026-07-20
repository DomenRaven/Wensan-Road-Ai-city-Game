"""7.20 W5 · workspace/tree + scenes 可读 + 证书门闩标记。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.auth_service import clear_auth_store_cache
from app.services.learning_analytics import clear_learning_store_cache


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    analytics = tmp_path / "learning_analytics"
    workspace = tmp_path / "workspace"
    analytics.mkdir()
    workspace.mkdir()
    monkeypatch.setenv("LEARNING_ANALYTICS_DIR", str(analytics))
    monkeypatch.setenv("WORKSPACE_DIR", str(workspace))
    monkeypatch.setenv("ALLOW_MEMORY_FALLBACK", "true")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()


def _seed_workspace(session_id: str) -> Path:
    settings = get_settings()
    root = settings.workspace_dir / session_id
    (root / "config").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "scenes").mkdir(parents=True)
    (root / "assets").mkdir(parents=True)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (root / "config" / "game_config.json").write_text(
        '{"meta":{"genre":"platformer"}}',
        encoding="utf-8",
    )
    (root / "core" / "player.gd").write_text("extends CharacterBody2D\n", encoding="utf-8")
    (root / "scenes" / "main.tscn").write_text("[gd_scene]\n", encoding="utf-8")
    (root / "assets" / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return root


def test_tree_and_scenes_file(client: TestClient) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    _seed_workspace(sid)
    store = client.app.state.session_store
    rec = store.get(sid)
    assert rec is not None
    rec.genre = "platformer"
    store.save(rec)

    tree = client.get(f"/sessions/{sid}/workspace/tree")
    assert tree.status_code == 200, tree.text
    body = tree.json()
    names = {n["name"] for n in body["tree"]}
    assert "config" in names
    assert "core" in names
    assert "scenes" in names
    assert "assets" in names

    scenes = client.get(
        f"/sessions/{sid}/workspace/file",
        params={"rel_path": "scenes/main.tscn"},
    )
    assert scenes.status_code == 200
    assert "[gd_scene]" in scenes.json()["content"]
    assert scenes.json().get("annotation")  # platformer or default

    assets = client.get(
        f"/sessions/{sid}/workspace/file",
        params={"rel_path": "assets/hero.png"},
    )
    assert assets.status_code == 400

    trav = client.get(
        f"/sessions/{sid}/workspace/file",
        params={"rel_path": "../secrets.txt"},
    )
    assert trav.status_code == 400


def test_certificate_saved_flag(client: TestClient) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    _seed_workspace(sid)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    put = client.put(
        f"/sessions/{sid}/certificate",
        content=png,
        headers={"Content-Type": "image/png"},
    )
    assert put.status_code == 200, put.text
    got = client.get(f"/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["payload"].get("certificate_saved") is True
