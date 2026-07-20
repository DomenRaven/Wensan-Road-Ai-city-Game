"""7.20 W1 · 注册/登录、会话归属、workspace 隔离、命名默认。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.auth_service import clear_auth_store_cache, default_work_display_name
from app.services.workspace_guard import copy_template_to_workspace, workspace_root_for_session


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
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
    clear_auth_store_cache()


def _register(client: TestClient, username: str = "xiaoming") -> dict:
    res = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "secret12",
            "nickname": "小明",
            "class_label": "高一(3)班",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_register_login_me_logout(client: TestClient) -> None:
    reg = _register(client)
    assert reg["token"]
    assert reg["user"]["username"] == "xiaoming"
    assert reg["user"]["nickname"] == "小明"

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {reg['token']}"})
    assert me.status_code == 200
    assert me.json()["user"]["id"] == reg["user"]["id"]

    bad = client.post("/auth/login", json={"username": "xiaoming", "password": "wrong"})
    assert bad.status_code == 401

    ok = client.post(
        "/auth/login",
        json={"username": "xiaoming", "password": "secret12"},
    )
    assert ok.status_code == 200
    token = ok.json()["token"]

    client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me2.status_code == 401


def test_guest_session_unchanged_path(client: TestClient, tmp_path: Path) -> None:
    created = client.post("/sessions", json={"auth_mode": "guest"})
    assert created.status_code == 201
    body = created.json()
    assert body["auth_mode"] == "guest"
    assert body["user_id"] is None
    sid = body["session_id"]

    settings = get_settings()
    root = workspace_root_for_session(settings.workspace_dir, sid)
    assert root == (settings.workspace_dir / sid).resolve()


def test_login_session_isolated_workspace_and_403(client: TestClient) -> None:
    a = _register(client, "user_a")
    b = _register(client, "user_b")
    headers_a = {"Authorization": f"Bearer {a['token']}"}
    headers_b = {"Authorization": f"Bearer {b['token']}"}

    sa = client.post("/sessions", json={"auth_mode": "login"}, headers=headers_a)
    assert sa.status_code == 201
    sid_a = sa.json()["session_id"]
    assert sa.json()["auth_mode"] == "login"
    assert sa.json()["creator_name"] == "小明"
    assert sa.json()["user_id"] == a["user"]["id"]

    # B 不可读 A 的会话
    denied = client.get(f"/sessions/{sid_a}", headers=headers_b)
    assert denied.status_code == 403

    settings = get_settings()
    root = workspace_root_for_session(
        settings.workspace_dir, sid_a, user_id=a["user"]["id"]
    )
    assert "users" in root.parts
    assert a["user"]["id"] in root.parts

    # 复制模板应落到隔离路径
    templates = get_settings().templates_dir
    if (templates / "platformer" / "project.godot").is_file():
        copied = copy_template_to_workspace(
            templates,
            settings.workspace_dir,
            "platformer",
            sid_a,
            user_id=a["user"]["id"],
        )
        assert copied == root
        assert (copied / "project.godot").is_file()


def test_single_active_session_takeover(client: TestClient) -> None:
    auth = _register(client, "solo_user")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    first = client.post("/sessions", json={"auth_mode": "login"}, headers=headers)
    assert first.status_code == 201
    sid1 = first.json()["session_id"]

    second = client.post("/sessions", json={"auth_mode": "login"}, headers=headers)
    assert second.status_code == 201
    sid2 = second.json()["session_id"]
    assert sid2 != sid1
    assert second.json()["taken_over_session_id"] == sid1

    gone = client.get(f"/sessions/{sid1}", headers=headers)
    assert gone.status_code == 404


def test_login_creator_name_locked(client: TestClient) -> None:
    auth = _register(client, "lock_user")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    sid = client.post("/sessions", json={"auth_mode": "login"}, headers=headers).json()[
        "session_id"
    ]
    bad = client.patch(
        f"/sessions/{sid}",
        json={"creator_name": "别人"},
        headers=headers,
    )
    assert bad.status_code == 400

    ok = client.patch(
        f"/sessions/{sid}",
        json={"creator_name": "小明"},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["creator_name"] == "小明"


def test_f4n3_default_display_name() -> None:
    name = default_work_display_name("小明", "xiaoming", "街机飞机射击")
    assert name == "小明（xiaoming）的街机飞机射击游戏"


def test_duplicate_username_rejected(client: TestClient) -> None:
    _register(client, "dup_user")
    again = client.post(
        "/auth/register",
        json={"username": "dup_user", "password": "secret12", "nickname": "二号"},
    )
    assert again.status_code == 409
