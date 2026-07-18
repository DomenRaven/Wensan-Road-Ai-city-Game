from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.creative import loader
from app.services.creative.llm_patch import (
    NL_PATCH_CLAMP_PERCENT,
    NlPatchError,
    apply_nl_patch,
    numeric_tuning_paths,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_BASE_CONFIG = {
    "meta": {"genre": "platformer", "display_name": "测试跳跳"},
    "tuning": {
        "player": {"move_speed": 200, "jump_velocity": -400},
        "enemy": {"patrol_speed": 50},
        "scoring": {"coin": 10},
        "lives": {"max": 3, "invincible_sec": 1.5},
        "enabled_skills": [],
    },
    "theme": {"title": "测试跳跳"},
}


def _prepare_tree(tmp_path: Path) -> tuple[Path, Path]:
    templates_dir = tmp_path / "templates"
    workspace_dir = tmp_path / "workspace"
    _write_json(templates_dir / "platformer" / "config" / "game_config.json", _BASE_CONFIG)
    return templates_dir, workspace_dir


def _settings(tmp_path: Path, *, api_key: str = "") -> Settings:
    templates_dir, workspace_dir = _prepare_tree(tmp_path)
    return Settings(
        templates_dir=templates_dir,
        workspace_dir=workspace_dir,
        allow_memory_fallback=True,
        llm_api_key=api_key,
    )


def _make_workspace(workspace_dir: Path, session_id: str) -> Path:
    root = workspace_dir / session_id
    _write_json(root / "config" / "game_config.json", _BASE_CONFIG)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    return root


def test_numeric_tuning_paths_excludes_skills() -> None:
    paths = numeric_tuning_paths(_BASE_CONFIG)
    assert "tuning.player.move_speed" in paths
    assert "tuning.scoring.coin" in paths
    assert "tuning.enabled_skills" not in paths


def test_apply_nl_patch_empty_text_raises(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    root = _make_workspace(settings.workspace_dir, "s1")
    with pytest.raises(NlPatchError):
        apply_nl_patch(settings, root, settings.templates_dir, "platformer", "   ")


def test_apply_nl_patch_stub_changes_config(tmp_path: Path) -> None:
    settings = _settings(tmp_path, api_key="")  # 无 Key → 必须 stub，绝不假装 llm
    root = _make_workspace(settings.workspace_dir, "s1")
    result = apply_nl_patch(settings, root, settings.templates_dir, "platformer", "跳得更高一点")
    assert result["ok"] is True
    assert result["provider"] == "stub"
    assert result["changes"]
    # 白名单内 jump 相关旋钮被调整
    changed_paths = {c["path"] for c in result["changes"]}
    assert any("jump" in p for p in changed_paths)


def test_apply_nl_patch_clamps_within_15_percent(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    root = _make_workspace(settings.workspace_dir, "s1")
    apply_nl_patch(settings, root, settings.templates_dir, "platformer", "让主角跑得超级快")
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    move_speed = cfg["tuning"]["player"]["move_speed"]
    high = round(200 * (1 + NL_PATCH_CLAMP_PERCENT / 100.0))
    low = round(200 * (1 - NL_PATCH_CLAMP_PERCENT / 100.0))
    # 钳制在 ±15% 边界内（整数四舍五入容 1 的误差）
    assert low - 1 <= move_speed <= high + 1
    assert move_speed != 200


def test_nl_patch_route_stub(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        created = client.post("/sessions")
        session_id = created.json()["session_id"]
        client.post("/intent/match-genre", json={"text": "马里奥闯关", "session_id": session_id})
        # nl-patch 不依赖 payload.workspace_path，直接读 workspace/{id}/config
        _make_workspace(settings.workspace_dir, session_id)
        resp = client.post(f"/sessions/{session_id}/nl-patch", json={"text": "敌人慢一点"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "stub"
        assert data["ok"] is True


def test_webgame_config_route(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        created = client.post("/sessions")
        session_id = created.json()["session_id"]
        client.post("/intent/match-genre", json={"text": "马里奥闯关", "session_id": session_id})
        _make_workspace(settings.workspace_dir, session_id)
        resp = client.get(f"/sessions/{session_id}/webgame-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["genre"] == "platformer"
        assert "player" in data["tuning"]
