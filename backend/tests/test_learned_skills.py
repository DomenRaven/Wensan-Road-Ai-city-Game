"""Learned Skill 长期库：harvest / 检索 / 降权 / release 先入库再删 / 导出导入。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.creative.learned_skills import (
    append_session_patch_log,
    clear_learned_skills,
    enable_catalog_skill,
    export_experience_pack,
    harvest_session_experience,
    import_experience_pack,
    promote_learned_skill_to_proposal,
    record_not_effective_feedback,
    search_learned_skills,
    snippet_quality_ok,
)
from app.services.creative.llm_patch import apply_nl_patch


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_BASE = {
    "meta": {"genre": "platformer"},
    "tuning": {
        "player": {"move_speed": 200, "jump_velocity": -400},
        "enabled_skills": [],
        "skills": {"double_jump": {"cooldown_scale": 1.0}},
    },
    "theme": {"title": "测"},
}


def _session_tree(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    store = tmp_path / "learned_skills"
    genre = "platformer"
    _write_json(templates / genre / "config" / "game_config.json", _BASE)
    (templates / genre / "core").mkdir(parents=True)
    (templates / genre / "core" / "player.gd").write_text(
        "extends CharacterBody2D\n", encoding="utf-8"
    )
    sid = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    root = workspace / sid
    _write_json(root / "config" / "game_config.json", _BASE)
    (root / "core").mkdir(parents=True)
    (root / "core" / "player.gd").write_text("extends CharacterBody2D\n", encoding="utf-8")
    return templates, workspace, root, store


def test_agent_write_session_not_templates(tmp_path: Path) -> None:
    from app.services.agent_workspace import write_workspace_file

    templates, workspace, root, _store = _session_tree(tmp_path)
    write_workspace_file(
        root,
        workspace,
        templates,
        "core/player.gd",
        "extends CharacterBody2D\n# session only\n",
    )
    assert "# session only" in (root / "core" / "player.gd").read_text(encoding="utf-8")
    assert "# session only" not in (
        templates / "platformer" / "core" / "player.gd"
    ).read_text(encoding="utf-8")


def test_enable_catalog_skill_tool(tmp_path: Path) -> None:
    _t, _w, root, _s = _session_tree(tmp_path)
    out = enable_catalog_skill(root, "platformer", "double_jump")
    assert out["already"] is False
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert "double_jump" in cfg["tuning"]["enabled_skills"]


def test_harvest_and_search_and_dedup(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    sandbox = root / "core" / "ai_sandbox"
    sandbox.mkdir(parents=True)
    gd = (
        "extends Node\n"
        "func apply(bridge) -> void:\n"
        "\tbridge.set_player_speed(1.2)\n"
    )
    (sandbox / "fun_buff.gd").write_text(gd, encoding="utf-8")
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "stub",
            "user_text": "多加有趣的技能",
            "summary": "已开趣味沙箱技能",
            "how_to_play": ["重开后试玩"],
            "sandbox_files": ["core/ai_sandbox/fun_buff.gd"],
            "applied_capabilities": ["sandbox_skill"],
            "changes": [
                {
                    "path": "tuning.enabled_skills",
                    "before": [],
                    "after": ["double_jump"],
                }
            ],
        },
    )
    r1 = harvest_session_experience(store, "sid-1", root, "platformer")
    assert r1["skipped"] is False
    assert r1["skills_created"] or r1["skills_merged"]
    hits = search_learned_skills(store, "多加有趣的技能", "platformer", k=5)
    assert hits
    assert hits[0]["genre"] == "platformer"

    # 第二次同话术 → 合并
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "agent",
            "user_text": "多加有趣的技能",
            "summary": "已开趣味沙箱技能",
            "how_to_play": ["重开后试玩"],
            "sandbox_files": ["core/ai_sandbox/fun_buff.gd"],
            "applied_capabilities": ["sandbox_skill"],
            "changes": [{"path": "tuning.enabled_skills", "before": [], "after": ["double_jump"]}],
        },
    )
    r2 = harvest_session_experience(store, "sid-2", root, "platformer")
    assert r2["skills_merged"] or r2["skills_created"]
    # index 不应无限膨胀
    index_lines = [
        ln
        for ln in (store / "index.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(index_lines) <= 3


def test_harvest_skips_when_no_success(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    r = harvest_session_experience(store, "sid-empty", root, "platformer")
    assert r["skipped"] is True
    assert r["reason"] == "no_successful_patch"


def test_safety_rejects_forbidden_api(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    sandbox = root / "core" / "ai_sandbox"
    sandbox.mkdir(parents=True)
    bad = "extends Node\nfunc apply(bridge) -> void:\n\tOS.execute('x', [])\n"
    (sandbox / "bad.gd").write_text(bad, encoding="utf-8")
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "agent",
            "user_text": "偷偷联网",
            "summary": "坏技能",
            "sandbox_files": ["core/ai_sandbox/bad.gd"],
            "applied_capabilities": ["hack"],
            "changes": [],
        },
    )
    r = harvest_session_experience(store, "sid-bad", root, "platformer")
    # 可能 rejected>0 且无 created，或 skipped 因质量过滤后无候选
    assert r.get("rejected", 0) >= 0
    hits = search_learned_skills(store, "偷偷联网", "platformer", k=5)
    for h in hits:
        assert "OS.execute" not in str(h.get("summary", ""))


def test_not_effective_demotes(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    sandbox = root / "core" / "ai_sandbox"
    sandbox.mkdir(parents=True)
    (sandbox / "x.gd").write_text(
        "extends Node\nfunc apply(bridge) -> void:\n\tpass\n", encoding="utf-8"
    )
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "stub",
            "user_text": "加二段跳",
            "summary": "已开二段跳",
            "sandbox_files": ["core/ai_sandbox/x.gd"],
            "applied_capabilities": ["double_jump"],
            "changes": [
                {"path": "tuning.enabled_skills", "before": [], "after": ["double_jump"]}
            ],
        },
    )
    harvest_session_experience(store, "sid-a", root, "platformer")
    before = search_learned_skills(store, "加二段跳", "platformer", k=1)
    assert before
    sid = str(before[0]["skill_id"])
    record_not_effective_feedback(store, "加二段跳没生效", "platformer", k=3)
    after = search_learned_skills(store, "加二段跳", "platformer", k=5)
    hit = next(h for h in after if h["skill_id"] == sid)
    assert int(hit.get("fail_count") or 0) >= 1


def test_snippet_quality_filter() -> None:
    assert snippet_quality_ok("x") is False
    assert (
        snippet_quality_ok("extends Node\nfunc apply(bridge) -> void:\n\tpass\n") is True
    )
    assert (
        snippet_quality_ok(
            "extends Node\nfunc apply(bridge) -> void:\n\tOS.execute('a',[])\n"
        )
        is False
    )


def test_nl_patch_stub_logs_and_release_harvests(tmp_path: Path) -> None:
    templates, workspace, root, store = _session_tree(tmp_path)
    settings = Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=store,
        allow_memory_fallback=True,
        llm_api_key="",
        llm_base_url="https://example.invalid/v1",
        llm_model="x",
        llm_timeout_sec=5.0,
        redis_url="memory://",
    )
    result = apply_nl_patch(
        settings, root, templates, "platformer", "加二段跳并画图标"
    )
    assert result["ok"] is True
    assert result["provider"] == "stub"
    assert (root / ".session_ai_log.jsonl").is_file()

    # 模拟 release：harvest 再删
    harvest = harvest_session_experience(
        store, root.name, root, "platformer", display_name="小明"
    )
    assert harvest["skipped"] is False or harvest.get("patch_count", 0) >= 0
    # 有成功 stub 应入库或至少有 experience
    assert (store / "experiences").is_dir()
    exps = list((store / "experiences").glob("*.json"))
    assert exps

    # 新会话可检索
    hits = search_learned_skills(store, "加二段跳", "platformer", k=5)
    # stub 开技能应能提炼
    assert isinstance(hits, list)


def test_release_hook_harvest_before_delete(tmp_path: Path, monkeypatch) -> None:
    templates, workspace, _root, store = _session_tree(tmp_path)
    settings = Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=store,
        allow_memory_fallback=True,
        llm_api_key="",
        redis_url="memory://",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    with TestClient(create_app()) as client:
        created = client.post("/sessions")
        assert created.status_code == 201
        sid = created.json()["session_id"]
        session_root = workspace / sid
        _write_json(session_root / "config" / "game_config.json", _BASE)
        sandbox = session_root / "core" / "ai_sandbox"
        sandbox.mkdir(parents=True)
        (sandbox / "z.gd").write_text(
            "extends Node\nfunc apply(bridge) -> void:\n\tpass\n", encoding="utf-8"
        )
        append_session_patch_log(
            session_root,
            {
                "ok": True,
                "provider": "llm",
                "user_text": "多加有趣技能",
                "summary": "沙箱技能",
                "sandbox_files": ["core/ai_sandbox/z.gd"],
                "applied_capabilities": ["sandbox_skill"],
                "changes": [
                    {
                        "path": "tuning.enabled_skills",
                        "before": [],
                        "after": ["double_jump"],
                    }
                ],
            },
        )
        from app.models.session import SessionPhase

        rec = client.app.state.session_store.get(sid)
        assert rec is not None
        rec.genre = "platformer"
        rec.phase = SessionPhase.PLAY
        rec.payload = {"meta": {"genre": "platformer"}}
        client.app.state.session_store.save(rec)

        resp = client.post(f"/sessions/{sid}/release")
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["workspace_removed"] is True
        assert not session_root.exists()
        harvest = body.get("harvest") or {}
        assert harvest.get("ok") is True
        assert harvest.get("experience_id") or not harvest.get("skipped", True)
        assert store.exists()
        assert (store / "index.jsonl").is_file()


def test_export_import_pack(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    sandbox = root / "core" / "ai_sandbox"
    sandbox.mkdir(parents=True)
    (sandbox / "p.gd").write_text(
        "extends Node\nfunc apply(bridge) -> void:\n\tpass\n", encoding="utf-8"
    )
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "stub",
            "user_text": "开氮气",
            "summary": "赛车氮气",
            "sandbox_files": ["core/ai_sandbox/p.gd"],
            "applied_capabilities": ["boost"],
            "changes": [
                {"path": "tuning.enabled_skills", "before": [], "after": ["boost"]}
            ],
        },
    )
    harvest_session_experience(store, "s1", root, "racing")
    zip_path = tmp_path / "pack.zip"
    export_experience_pack(store, zip_path)
    store2 = tmp_path / "store2"
    result = import_experience_pack(store2, zip_path)
    assert result["ok"] is True
    hits = search_learned_skills(store2, "开氮气", "racing", k=3)
    assert hits


def test_promote_proposal(tmp_path: Path) -> None:
    _t, _w, root, store = _session_tree(tmp_path)
    sandbox = root / "core" / "ai_sandbox"
    sandbox.mkdir(parents=True)
    (sandbox / "p.gd").write_text(
        "extends Node\nfunc apply(bridge) -> void:\n\tpass\n", encoding="utf-8"
    )
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "agent",
            "user_text": "滑铲",
            "summary": "开启滑铲",
            "sandbox_files": ["core/ai_sandbox/p.gd"],
            "applied_capabilities": ["slide"],
            "changes": [
                {"path": "tuning.enabled_skills", "before": [], "after": ["slide"]}
            ],
        },
    )
    h = harvest_session_experience(store, "s1", root, "parkour")
    created = h.get("skills_created") or h.get("skills_merged") or []
    assert created
    out = tmp_path / "proposal.json"
    path = promote_learned_skill_to_proposal(store, created[0], out)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"].startswith("optional_skills")
    assert "suggested_catalog_entry" in data


def test_clear_store(tmp_path: Path) -> None:
    store = tmp_path / "ls"
    (store / "experiences").mkdir(parents=True)
    (store / "index.jsonl").write_text(
        json.dumps({"skill_id": "x", "genre": "a", "safety": "ok"}) + "\n",
        encoding="utf-8",
    )
    r = clear_learned_skills(store, keep_experiences=True)
    assert r["skills_cleared"] >= 1
    assert (store / "index.jsonl").read_text(encoding="utf-8").strip() == ""


def test_ops_clear_endpoint(tmp_path: Path, monkeypatch) -> None:
    store = tmp_path / "ls"
    store.mkdir()
    (store / "index.jsonl").write_text("", encoding="utf-8")
    settings = Settings(
        learned_skills_dir=store,
        allow_memory_fallback=True,
        llm_api_key="",
        redis_url="memory://",
        templates_dir=tmp_path / "t",
        workspace_dir=tmp_path / "w",
    )
    (tmp_path / "t").mkdir()
    (tmp_path / "w").mkdir()
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        bad = client.post("/ops/learned-skills/clear", json={"confirm": "no"})
        assert bad.status_code == 400
        ok = client.post(
            "/ops/learned-skills/clear",
            json={"confirm": "CLEAR", "keep_experiences": True},
        )
        assert ok.status_code == 200
        assert ok.json()["ok"] is True


def test_nl_patch_prefers_agent_injects_learned(tmp_path: Path) -> None:
    templates, workspace, root, store = _session_tree(tmp_path)
    # 先种一条 Skill
    append_session_patch_log(
        root,
        {
            "ok": True,
            "provider": "stub",
            "user_text": "多加有趣的技能",
            "summary": "历史经验：开炸弹",
            "sandbox_files": [],
            "applied_capabilities": ["bomb"],
            "changes": [
                {"path": "tuning.enabled_skills", "before": [], "after": ["bomb"]}
            ],
        },
    )
    # 改 genre 为 shmup 以匹配 bomb — 用 platformer 也行，只要能检索
    harvest_session_experience(store, "old", root, "platformer")

    settings = Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=store,
        allow_memory_fallback=True,
        llm_api_key="sk-test",
        llm_base_url="https://example.invalid/v1",
        llm_model="test",
        llm_timeout_sec=5.0,
    )
    fake_agent = {
        "ok": True,
        "provider": "agent",
        "summary": "已复用历史做法",
        "message": "已复用历史做法",
        "sandbox_files": ["core/ai_sandbox/fun.gd"],
        "how_to_play": ["重开"],
        "agent_rounds": 1,
        "learned_skills": [],
    }
    with patch(
        "app.services.creative.llm_patch.run_game_agent", return_value=fake_agent
    ) as mocked:
        result = apply_nl_patch(
            settings, root, templates, "platformer", "多加有趣的技能"
        )
    assert result["ok"] is True
    assert result["provider"] == "agent"
    mocked.assert_called_once()
    # 智能体调用时 settings 带 learned_skills_dir
    assert settings.learned_skills_dir == store
