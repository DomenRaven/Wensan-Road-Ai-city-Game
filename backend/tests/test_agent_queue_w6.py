"""7.20 W6 · S4 Agent 并发帽与排队。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.agent_queue import AgentQueueError, get_agent_queue, reset_agent_queue_for_tests
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
    monkeypatch.setenv("MAX_CONCURRENT_AGENTS", "1")
    monkeypatch.setenv("AGENT_QUEUE_WAIT_SEC", "0.2")
    monkeypatch.setenv("MAX_SESSIONS", "70")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()
    reset_agent_queue_for_tests()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_agent_queue_for_tests()
    get_settings.cache_clear()
    clear_auth_store_cache()
    clear_learning_store_cache()


def _seed(session_id: str) -> Path:
    settings = get_settings()
    root = settings.workspace_dir / session_id
    (root / "config").mkdir(parents=True)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (root / "config" / "game_config.json").write_text(
        '{"meta":{"genre":"platformer","display_name":"测"},"theme":{"title":"测"},"tuning":{}}',
        encoding="utf-8",
    )
    return root


def test_max_sessions_configurable(client: TestClient) -> None:
    assert get_settings().max_sessions >= 70
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["max_sessions"] >= 70
    assert body["max_concurrent_agents"] == 1
    assert "active_agents" in body


def test_session_busy_rejects_second_inflight() -> None:
    reset_agent_queue_for_tests()
    gate = get_agent_queue()
    entered = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with gate.acquire("s1", max_concurrent=2, wait_sec=0.1):
            entered.set()
            release.wait(timeout=2.0)

    t = threading.Thread(target=holder, daemon=True)
    t.start()
    assert entered.wait(timeout=1.0)
    with pytest.raises(AgentQueueError) as ei:
        with gate.acquire("s1", max_concurrent=2, wait_sec=0.1):
            pass
    assert ei.value.code == "session_busy"
    release.set()
    t.join(timeout=2.0)
    reset_agent_queue_for_tests()


def test_queue_full_after_wait(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    sid_a = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    sid_b = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    root_b = _seed(sid_b)
    store = client.app.state.session_store
    rec = store.get(sid_b)
    assert rec is not None
    payload = dict(rec.payload)
    payload["workspace_path"] = str(root_b)
    rec.payload = payload
    rec.genre = "platformer"
    store.save(rec)

    # 直接占住 Agent 槽，避免 TestClient 多线程并发踩坑
    release = threading.Event()
    entered = threading.Event()

    def holder() -> None:
        with get_agent_queue().acquire(sid_a, max_concurrent=1, wait_sec=0.2):
            entered.set()
            release.wait(timeout=5.0)

    t = threading.Thread(target=holder, daemon=True)
    t.start()
    assert entered.wait(timeout=1.0)

    monkeypatch.setattr(
        "app.services.creative.llm_patch.run_game_agent",
        lambda *_a, **_k: {
            "ok": True,
            "summary": "ok",
            "message": "ok",
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
        },
    )

    res_b = client.post(
        f"/sessions/{sid_b}/nl-patch",
        json={"text": "再快点", "history": [], "feedback": ""},
    )
    assert res_b.status_code == 503, res_b.text
    detail = res_b.json()["detail"]
    assert detail["code"] == "agent_queue_full"
    assert "人数已满" in detail["message"]

    release.set()
    t.join(timeout=3.0)
    reset_agent_queue_for_tests()


def test_health_exposes_agent_queue(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["max_concurrent_agents"] == 1
    assert body["active_agents"] == 0
    assert body["agent_queue_waiting"] == 0
