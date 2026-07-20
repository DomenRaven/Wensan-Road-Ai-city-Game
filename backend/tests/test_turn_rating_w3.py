"""7.20 W3 · 星级评价落库 + 下一轮注入 previous_turn_user_rating。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.auth_service import clear_auth_store_cache
from app.services.learning_analytics import (
    clear_learning_store_cache,
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
    monkeypatch.setenv("LLM_API_KEY", "test-key-for-inject")
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()


def _make_workspace(session_id: str, settings: Any) -> Path:
    root = settings.workspace_dir / session_id
    (root / "config").mkdir(parents=True)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    cfg = {
        "meta": {"display_name": "测", "genre": "platformer"},
        "theme": {"title": "测"},
        "tuning": {"enabled_skills": []},
    }
    (root / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def test_rating_api_and_revision(client: TestClient) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    store = get_learning_store()
    turn = store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="让主角跳得更高",
        message="已调高跳跃",
        summary="调高跳跃",
        how_to_play=["按空格跳"],
        gate_passed=True,
        genre="platformer",
    )
    r1 = client.post(
        f"/sessions/{sid}/turns/{turn.turn_id}/rating",
        json={"score": 2, "comment": "还是不够高"},
    )
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["score"] == 2
    assert body["label"] == "比较不满意"
    assert body["revision"] == 1

    r2 = client.post(
        f"/sessions/{sid}/turns/{turn.turn_id}/rating",
        json={"score": 4, "comment": "现在好了"},
    )
    assert r2.status_code == 200
    assert r2.json()["score"] == 4
    assert r2.json()["label"] == "比较满意"
    assert r2.json()["revision"] == 2

    got = client.get(f"/sessions/{sid}/turns/{turn.turn_id}/rating")
    assert got.status_code == 200, got.text
    assert got.json()["score"] == 4
    assert got.json()["comment"] == "现在好了"

    payload = store.get_previous_turn_user_rating(sid)
    assert payload is not None
    assert payload["score"] == 4
    assert payload["rated_turn_id"] == turn.turn_id
    assert "跳得更高" in payload["rated_user_request_summary"]
    assert payload["gate_passed"] is True


def test_no_rating_means_no_injection_payload(client: TestClient) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    store = get_learning_store()
    store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="加点特效",
        message="好的",
        summary="特效",
        how_to_play=[],
    )
    assert store.get_previous_turn_user_rating(sid) is None


def test_nl_patch_passes_previous_rating_into_agent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    store = get_learning_store()
    turn = store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="让主角跳得更高",
        message="已调高",
        summary="调高",
        how_to_play=[],
        gate_passed=True,
    )
    store.upsert_turn_rating(turn_id=turn.turn_id, score=2, comment="还不够")

    root = _make_workspace(sid, settings)
    app_store = client.app.state.session_store
    record = app_store.get(sid)
    assert record is not None
    payload = dict(record.payload)
    payload["workspace_path"] = str(root)
    record.payload = payload
    record.genre = "platformer"
    app_store.save(record)

    captured: dict[str, Any] = {}

    def fake_agent(*_a: Any, **kwargs: Any) -> dict[str, Any]:
        captured["previous_turn_user_rating"] = kwargs.get("previous_turn_user_rating")
        return {
            "ok": True,
            "summary": "已继续改",
            "message": "已继续改",
            "changes": [],
            "sandbox_files": [],
            "how_to_play": [],
            "gate_passed": True,
            "partial": False,
            "rolled_back": False,
            "goals": [],
            "applied_capabilities": [],
            "verify_gaps": [],
            "learned_skills": [],
            "agent_rounds": 1,
        }

    monkeypatch.setattr(
        "app.services.creative.llm_patch.run_game_agent",
        fake_agent,
    )

    res = client.post(
        f"/sessions/{sid}/nl-patch",
        json={"text": "再高一点", "history": [], "feedback": ""},
    )
    assert res.status_code == 200, res.text
    rating = captured.get("previous_turn_user_rating")
    assert rating is not None
    assert rating["score"] == 2
    assert rating["label"] == "比较不满意"
    assert "previous_turn_user_rating" not in (res.json().get("message") or "")
    # 注入块键名与需求一致
    assert "rated_turn_id" in rating
