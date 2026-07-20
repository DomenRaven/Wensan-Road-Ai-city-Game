"""7.20 W2 · 学情 SQLite · agent_reply_full · release 不删。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.auth_service import clear_auth_store_cache
from app.services.learning_analytics import (
    clear_learning_store_cache,
    compose_agent_reply_full,
    get_learning_store,
)


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
    monkeypatch.setenv("LLM_API_KEY", "")
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()


def test_compose_agent_reply_full_f5_l2() -> None:
    assert compose_agent_reply_full("长文回复", "短摘要", []) == "长文回复"
    assert compose_agent_reply_full("", "短摘要", []) == "短摘要"
    full = compose_agent_reply_full(
        "已加上二段跳",
        "摘要",
        ["按空格跳一次", "空中再按一次"],
    )
    assert "已加上二段跳" in full
    assert "试玩步骤：" in full
    assert "1. 按空格跳一次" in full
    assert "2. 空中再按一次" in full
    # 有 message 时不以 summary 作主文案
    assert "摘要" not in full


def test_record_turn_survives_release(client: TestClient) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    # 无 workspace 时 nl-patch 会 400；直接写学情库验证 release 保留
    store = get_learning_store()
    turn = store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="让角色跳得更高",
        message="好的，我把跳跃高度调高了，并加了落地反馈。",
        summary="调高跳跃",
        how_to_play=["按空格跳跃", "看落地灰尘"],
        provider="stub",
        gate_passed=True,
        genre="platformer",
        display_name="测试游戏",
        creator_name="小创作者",
    )
    assert turn.turn_id.startswith("trn_")
    assert "好的，我把跳跃高度调高了" in turn.agent_reply_full
    assert "试玩步骤：" in turn.agent_reply_full
    assert "1. 按空格跳跃" in turn.agent_reply_full

    release = client.post(f"/sessions/{sid}/release?harvest=false")
    assert release.status_code == 200

    # 会话没了，学情仍在
    assert client.get(f"/sessions/{sid}").status_code == 404
    saved = store.get_turn(turn.turn_id)
    assert saved is not None
    assert saved["user_text"] == "让角色跳得更高"
    assert "落地反馈" in saved["agent_reply_full"]
    assert store.count_turns() >= 1


def test_learning_db_not_under_learned_skills(client: TestClient) -> None:
    settings = get_settings()
    db = Path(settings.learning_analytics_dir) / "learning.db"
    get_learning_store().ensure_play_session(
        session_id="00000000-0000-4000-8000-000000000099",
        user_id=None,
        auth_mode="guest",
    )
    assert db.is_file()
    assert "learned_skills" not in str(db.resolve())
    assert "learning_analytics" in str(db.resolve())
