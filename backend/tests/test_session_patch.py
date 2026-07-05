"""Tests for PATCH /sessions/{session_id} creator_name persistence."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_patch_creator_name(client: TestClient) -> None:
    create = client.post("/sessions")
    assert create.status_code == 201
    session_id = create.json()["session_id"]

    patch = client.patch(
        f"/sessions/{session_id}",
        json={"creator_name": "小明"},
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["creator_name"] == "小明"

    get = client.get(f"/sessions/{session_id}")
    assert get.status_code == 200
    assert get.json()["creator_name"] == "小明"


def test_patch_creator_name_rejects_empty(client: TestClient) -> None:
    session_id = client.post("/sessions").json()["session_id"]

    patch = client.patch(
        f"/sessions/{session_id}",
        json={"creator_name": "   "},
    )
    assert patch.status_code == 400


def test_patch_creator_name_rejects_invalid_chars(client: TestClient) -> None:
    session_id = client.post("/sessions").json()["session_id"]

    patch = client.patch(
        f"/sessions/{session_id}",
        json={"creator_name": "小@明"},
    )
    assert patch.status_code == 400


def test_patch_display_name_unchanged_behavior(client: TestClient) -> None:
    session_id = client.post("/sessions").json()["session_id"]

    patch = client.patch(
        f"/sessions/{session_id}",
        json={"display_name": "赛车之王"},
    )
    assert patch.status_code == 200
    assert patch.json()["display_name"] == "赛车之王"
