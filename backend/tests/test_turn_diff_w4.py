"""7.20 W4 · 回合 Diff 快照、持久化、release 后可回看。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.auth_service import clear_auth_store_cache
from app.services.learning_analytics import clear_learning_store_cache, get_learning_store
from app.services.turn_diff import compute_turn_diff, snapshot_workspace_texts


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


def test_compute_turn_diff_add_modify_delete() -> None:
    before = {
        "core/a.gd": "line1\nkeep\n",
        "core/gone.gd": "bye\n",
    }
    after = {
        "core/a.gd": "line1\nkeep\nnew\n",
        "core/new.gd": "hello\n",
    }
    payload = compute_turn_diff(before, after, overview_note="已加上新逻辑")
    assert payload["file_count"] == 3
    by_path = {f["path"]: f for f in payload["files"]}
    assert by_path["core/new.gd"]["change_type"] == "added"
    assert "+" in by_path["core/new.gd"]["diff_text"]
    assert by_path["core/gone.gd"]["change_type"] == "deleted"
    assert by_path["core/a.gd"]["change_type"] == "modified"
    assert "已加上新逻辑" in payload["overview_note"]


def test_snapshot_and_persist_survives_release(client: TestClient, tmp_path: Path) -> None:
    sid = client.post("/sessions", json={"auth_mode": "guest"}).json()["session_id"]
    settings = get_settings()
    root = settings.workspace_dir / sid
    (root / "core").mkdir(parents=True)
    (root / "core" / "player.gd").write_text("jump = 1\n", encoding="utf-8")

    before = snapshot_workspace_texts(root)
    (root / "core" / "player.gd").write_text("jump = 2\n", encoding="utf-8")
    after = snapshot_workspace_texts(root)

    store = get_learning_store()
    turn = store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="跳得更高",
        message="已把跳跃调高，请重开游戏试玩。",
        summary="调高跳跃",
        how_to_play=["按空格跳"],
        gate_passed=True,
    )
    diff = compute_turn_diff(
        before,
        after,
        overview_note=turn.agent_reply_full,
    )
    store.save_turn_diff(turn.turn_id, diff)

    got = client.get(f"/sessions/{sid}/turns/{turn.turn_id}/diff")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["file_count"] >= 1
    assert any(f["path"] == "core/player.gd" for f in body["files"])
    player = next(f for f in body["files"] if f["path"] == "core/player.gd")
    assert "jump = 2" in player["after_text"]
    assert player["diff_text"].startswith("---") or "+" in player["diff_text"]
    assert "跳跃" in body["overview_note"]

    # release 后会话没了，游客仍可用 session_id+turn_id 回看
    assert client.post(f"/sessions/{sid}/release?harvest=false").status_code == 200
    assert client.get(f"/sessions/{sid}").status_code == 404
    again = client.get(f"/sessions/{sid}/turns/{turn.turn_id}/diff")
    assert again.status_code == 200
    assert again.json()["turn_id"] == turn.turn_id
    blob = Path(settings.learning_analytics_dir) / "blobs" / turn.turn_id / "diff.json"
    assert blob.is_file()
    assert "learned_skills" not in str(blob.resolve())


def test_no_fake_diff_when_unchanged() -> None:
    snap = {"config/game_config.json": '{"a":1}\n'}
    payload = compute_turn_diff(snap, snap)
    assert payload["file_count"] == 0
    assert "无净变更" in payload["overview_note"]
