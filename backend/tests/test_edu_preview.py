from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_preview_platformer_game_config(client: TestClient) -> None:
    res = client.get("/edu/preview/platformer/file", params={"rel_path": "config/game_config.json"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["genre"] == "platformer"
    assert body["path"] == "config/game_config.json"
    assert '"tuning"' in body["content"] or '"meta"' in body["content"]


def test_preview_rejects_path_traversal(client: TestClient) -> None:
    res = client.get("/edu/preview/platformer/file", params={"rel_path": "../secrets.txt"})
    assert res.status_code == 400


def test_preview_unknown_genre(client: TestClient) -> None:
    res = client.get("/edu/preview/not_a_genre/file", params={"rel_path": "config/game_config.json"})
    assert res.status_code == 404


def test_preview_scenes_tscn(client: TestClient) -> None:
    settings = get_settings()
    main_tscn = Path(settings.templates_dir) / "platformer" / "scenes" / "main.tscn"
    if not main_tscn.is_file():
        pytest.skip("platformer main.tscn missing")
    res = client.get("/edu/preview/platformer/file", params={"rel_path": "scenes/main.tscn"})
    assert res.status_code == 200
    assert "[gd_scene" in res.json()["content"]
