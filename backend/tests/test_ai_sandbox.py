"""AI 沙箱严格测试 · 路径红线 / 脚本边界 / nl-patch 镜像 / release 销毁。

默认全部离线（mock LLM）；不消耗百炼额度。
可选：RUN_LIVE_LLM=1 pytest -m live 才打真实阿里云。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.ai_sandbox import (
    AI_SANDBOX_REL,
    AiSandboxError,
    assert_sandbox_write_allowed,
    changes_to_overrides_patch,
    destroy_ai_sandbox,
    list_sandbox_files,
    validate_gdscript_content,
    validate_svg_content,
    write_modifier_gdscript,
    write_overrides_json,
    write_sandbox_asset,
    write_sandbox_file,
)
from app.services.creative.llm_patch import apply_nl_patch
from app.services.workspace_guard import remove_workspace


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_BASE = {
    "meta": {"genre": "platformer"},
    "tuning": {
        "player": {"move_speed": 200, "jump_velocity": -400},
        "enemy": {"patrol_speed": 50},
        "lives": {"max": 3, "invincible_sec": 1.5},
        "enabled_skills": [],
        "skills": {
            "double_jump": {"cooldown_scale": 1.0},
            "ground_pound": {"cooldown_scale": 1.0},
        },
    },
    "theme": {"title": "测"},
}


@pytest.fixture
def tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    """templates/, workspace/, session root（含冻结 core 拷贝）。"""
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    genre = "platformer"
    _write_json(templates / genre / "config" / "game_config.json", _BASE)
    (templates / genre / "core").mkdir(parents=True)
    (templates / genre / "core" / "player_platformer.gd").write_text(
        "extends CharacterBody2D\n", encoding="utf-8"
    )
    (templates / genre / "core" / "game_manager.gd").write_text(
        "extends Node\n", encoding="utf-8"
    )
    root = workspace / "s1"
    _write_json(root / "config" / "game_config.json", _BASE)
    (root / "core").mkdir(parents=True)
    (root / "core" / "player_platformer.gd").write_text(
        "extends CharacterBody2D\n", encoding="utf-8"
    )
    (root / "core" / "game_manager.gd").write_text("extends Node\n", encoding="utf-8")
    return templates, workspace, root


def _settings(templates: Path, workspace: Path, api_key: str = "") -> Settings:
    learned = workspace.parent / "learned_skills_test"
    learned.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        allow_memory_fallback=True,
        llm_api_key=api_key,
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model="qwen-plus",
        llm_timeout_sec=45.0,
    )


# ── 路径红线 ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rel",
    [
        "core/player_platformer.gd",
        "core/game_manager.gd",
        "config/game_config.json",
        "scenes/main.tscn",
        "project.godot",
        "core/skills/double_jump.gd",
        "README.md",
        "",
        "core/ai_sandbox",
        "core/ai_sandbox/",
        "core/ai_sandbox/../player_platformer.gd",
        "core/ai_sandbox/foo/../../game_manager.gd",
        "../templates/platformer/core/x.gd",
        "core\\ai_sandbox\\..\\player_platformer.gd",
        "/etc/passwd",
        "C:/Windows/System32/x.gd",
    ],
)
def test_reject_forbidden_paths(tree: tuple[Path, Path, Path], rel: str) -> None:
    templates, workspace, root = tree
    with pytest.raises(AiSandboxError):
        assert_sandbox_write_allowed(root, workspace, templates, "platformer", rel)


def test_reject_when_template_already_has_sandbox_file(tree: tuple[Path, Path, Path]) -> None:
    """若模板误含 ai_sandbox 同名文件，也禁止写入（防覆盖模板）。"""
    templates, workspace, root = tree
    planted = templates / "platformer" / AI_SANDBOX_REL / "overrides.json"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("{}", encoding="utf-8")
    with pytest.raises(AiSandboxError, match="拒绝覆盖模板"):
        assert_sandbox_write_allowed(
            root, workspace, templates, "platformer", f"{AI_SANDBOX_REL}/overrides.json"
        )


def test_allow_sandbox_nested_file(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    target = assert_sandbox_write_allowed(
        root, workspace, templates, "platformer", f"{AI_SANDBOX_REL}/mods/a.gd"
    )
    assert target.name == "a.gd"
    assert "ai_sandbox" in target.as_posix()


# ── GDScript 校验边界 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "filename,content,match",
    [
        ("Evil.gd", "extends RefCounted\n", "非法脚本名"),
        ("1bad.gd", "extends RefCounted\n", "非法脚本名"),
        ("bad-name.gd", "extends RefCounted\n", "非法脚本名"),
        ("ok.gd", "func apply(b):\n\tpass\n", "extends"),
        (
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tOS.execute('x', [])\n",
            "禁止调用",
        ),
        (
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tOS.create_process('x', [])\n",
            "禁止调用",
        ),
        (
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tOS.shell_open('http://x')\n",
            "禁止调用",
        ),
        (
            "ok.gd",
            'extends RefCounted\nfunc apply(b):\n\tvar f=FileAccess.open("res://core/x.gd", FileAccess.READ)\n',
            "禁止调用",
        ),
        (
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tvar f=FileAccess.open('user://a', FileAccess.WRITE)\n",
            "FileAccess WRITE",
        ),
        (
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tDirAccess.remove('res://x')\n",
            "禁止调用",
        ),
    ],
)
def test_gdscript_validation_rejects(
    filename: str, content: str, match: str
) -> None:
    with pytest.raises(AiSandboxError, match=match):
        validate_gdscript_content(filename, content)


def test_gdscript_rejects_oversized() -> None:
    with pytest.raises(AiSandboxError, match="脚本过大"):
        validate_gdscript_content("ok.gd", "extends RefCounted\n" + ("x" * 50_000))


def test_gdscript_validation_accepts_apply_script() -> None:
    text = validate_gdscript_content(
        "jump_feel.gd",
        "extends RefCounted\n\nfunc apply(bridge) -> void:\n\tpass\n",
    )
    assert "extends RefCounted" in text


def test_write_modifier_then_list_and_destroy(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    rel = write_modifier_gdscript(
        root,
        workspace,
        templates,
        "platformer",
        "jump_feel.gd",
        "extends RefCounted\nfunc apply(bridge):\n\tpass\n",
    )
    assert rel == f"{AI_SANDBOX_REL}/jump_feel.gd"
    files = list_sandbox_files(root)
    assert rel in files
    assert destroy_ai_sandbox(root) is True
    assert list_sandbox_files(root) == []
    assert (root / "core" / "player_platformer.gd").is_file()


# ── overrides 合并 ────────────────────────────────────────────────────────────


def test_overrides_deep_merge(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    write_overrides_json(
        root, workspace, templates, "platformer", {"tuning": {"player": {"move_speed": 210}}}
    )
    write_overrides_json(
        root, workspace, templates, "platformer", {"tuning": {"player": {"jump_velocity": -420}}}
    )
    data = json.loads((root / AI_SANDBOX_REL / "overrides.json").read_text(encoding="utf-8"))
    assert data["tuning"]["player"]["move_speed"] == 210
    assert data["tuning"]["player"]["jump_velocity"] == -420


def test_changes_to_overrides_patch_nested() -> None:
    patch = changes_to_overrides_patch(
        [
            {"path": "tuning.player.move_speed", "after": 220},
            {"path": "theme.title", "after": "新标题"},
        ]
    )
    assert patch["tuning"]["player"]["move_speed"] == 220
    assert patch["theme"]["title"] == "新标题"


# ── nl-patch stub / mock LLM ─────────────────────────────────────────────────


def test_nl_patch_stub_mirrors_sandbox_keeps_frozen_core(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    frozen = root / "core" / "player_platformer.gd"
    before = frozen.read_text(encoding="utf-8")
    settings = _settings(templates, workspace, api_key="")
    result = apply_nl_patch(settings, root, templates, "platformer", "跳得更高一点")
    assert result["ok"] is True
    assert result["provider"] == "stub"
    assert any("overrides.json" in p for p in result["sandbox_files"])
    assert frozen.read_text(encoding="utf-8") == before
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert cfg["tuning"]["player"]["jump_velocity"] != -400


def test_nl_patch_with_key_uses_agent_not_legacy_llm(
    tree: tuple[Path, Path, Path],
) -> None:
    """有 API Key 时只走 run_game_agent，不再掉进旧 _call_llm。"""
    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="sk-test")
    fake_agent = {
        "ok": True,
        "provider": "agent",
        "summary": "已加快移速",
        "message": "已加快移速",
        "how_to_play": ["请重新启动游戏后点屏幕下方按钮试玩"],
        "sandbox_files": [f"{AI_SANDBOX_REL}/speed_mod.gd"],
        "changes": [],
        "applied_capabilities": [],
        "verify_gaps": [],
        "gate_passed": True,
        "goals": ["加快移速"],
        "understanding": "用户要跑更快",
    }
    with patch(
        "app.services.creative.llm_patch.run_game_agent", return_value=fake_agent
    ) as mocked:
        with patch("app.services.creative.llm_patch._call_llm") as legacy:
            result = apply_nl_patch(
                settings, root, templates, "platformer", "让主角跑得更快"
            )
    assert result["ok"] is True
    assert result["provider"] == "agent"
    mocked.assert_called()
    legacy.assert_not_called()


def test_nl_patch_agent_failure_does_not_degrade_to_stub_llm(
    tree: tuple[Path, Path, Path],
) -> None:
    """Agent 失败时诚实失败，禁止降级成 llm/stub 空话。"""
    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="sk-test")
    with patch(
        "app.services.creative.llm_patch.run_game_agent",
        side_effect=ValueError("done 门禁多次失败"),
    ):
        with patch("app.services.creative.llm_patch._call_llm") as legacy:
            with patch("app.services.creative.llm_patch._stub_changes") as stub:
                result = apply_nl_patch(
                    settings, root, templates, "platformer", "人物消失不显示"
                )
    assert result["provider"] == "agent"
    assert result["ok"] is False
    assert "智能体" in result["message"] or "没改成" in result["message"]
    legacy.assert_not_called()
    stub.assert_not_called()


def test_nl_patch_sanitize_rejects_evil_via_helpers() -> None:
    """路径 sanitize 丢弃越狱名；OS.execute 在写沙箱时被拒。"""
    from app.services.ai_sandbox import AiSandboxError, write_modifier_gdscript
    from app.services.creative.llm_patch import _sanitize_new_files

    files = _sanitize_new_files(
        [
            {
                "filename": "speed_mod.gd",
                "content": "extends RefCounted\nfunc apply(bridge):\n\tpass\n",
            },
            {"filename": "../hack.gd", "content": "extends RefCounted\n"},
        ]
    )
    names = {f["filename"] for f in files}
    assert "speed_mod.gd" in names
    assert not any("hack" in n for n in names)

    # OS.execute 内容：写盘层拒绝（不依赖已废弃的旧 llm 路径）
    with pytest.raises(AiSandboxError):
        # 用临时路径形状校验片段扫描即可
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td) / "ws" / "sid"
            root.mkdir(parents=True)
            (root / "core").mkdir()
            write_modifier_gdscript(
                root,
                Path(td) / "ws",
                Path(td) / "templates",
                "platformer",
                "evil.gd",
                "extends RefCounted\nfunc apply(b):\n\tOS.execute('x',[])\n",
            )


def test_nl_patch_never_writes_outside_sandbox_even_if_llm_lies(
    tree: tuple[Path, Path, Path],
) -> None:
    """sanitize 后同名文件只能落 ai_sandbox，不能盖掉会话 core。"""
    from app.services.creative.llm_patch import _sanitize_new_files, _mirror_to_sandbox

    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="")
    frozen = (root / "core" / "player_platformer.gd").read_text(encoding="utf-8")
    files = _sanitize_new_files(
        [
            {
                "filename": "player_platformer.gd",
                "content": "extends RefCounted\nfunc apply(b):\n\tpass\n",
            }
        ]
    )
    mirrored = _mirror_to_sandbox(settings, root, "platformer", [], files)
    assert frozen.startswith("extends CharacterBody2D")
    assert (root / "core" / "player_platformer.gd").read_text(encoding="utf-8") == frozen
    assert any(p.endswith("player_platformer.gd") for p in mirrored)
    assert (root / AI_SANDBOX_REL / "player_platformer.gd").is_file()


def test_sanitize_skills_rejects_unknown_and_core_path(
    tree: tuple[Path, Path, Path],
) -> None:
    """技能白名单仍过滤未知 id；new_files 越狱路径被丢弃（不依赖旧 llm 路径）。"""
    from app.services.creative.llm_patch import (
        _sanitize_changes,
        _sanitize_new_files,
        _mirror_to_sandbox,
    )

    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="")
    frozen = (root / "core" / "player_platformer.gd").read_text(encoding="utf-8")
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    base = json.loads(
        (templates / "platformer" / "config" / "game_config.json").read_text(encoding="utf-8")
    )
    changes = _sanitize_changes(
        {
            "tuning.enabled_skills": ["double_jump", "ground_pound", "hack_skill"],
            "tuning.lives.invincible_sec": 2.0,
        },
        cfg,
        base,
        "platformer",
    )
    skills = next(c for c in changes if c["path"] == "tuning.enabled_skills")
    assert skills["after"] == ["double_jump", "ground_pound"]
    assert "hack_skill" not in skills["after"]

    files = _sanitize_new_files(
        [
            {
                "filename": "icons/double_jump.svg",
                "content": (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                    '<circle cx="32" cy="32" r="20" fill="#0ea5e9"/></svg>'
                ),
            },
            {
                "filename": "../skills/double_jump.gd",
                "content": "extends RefCounted\n",
            },
        ]
    )
    mirrored = _mirror_to_sandbox(settings, root, "platformer", changes, files)
    assert any(p.endswith("icons/double_jump.svg") for p in mirrored)
    assert not any("skills/double_jump" in p for p in mirrored)
    assert (root / "core" / "player_platformer.gd").read_text(encoding="utf-8") == frozen


# ── HTTP：release 销毁 ────────────────────────────────────────────────────────


def test_session_release_destroys_sandbox(tree: tuple[Path, Path, Path], monkeypatch) -> None:
    templates, workspace, root = tree
    settings = _settings(templates, workspace)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    # 预写沙箱
    write_overrides_json(
        root, workspace, templates, "platformer", {"tuning": {"player": {"move_speed": 211}}}
    )
    assert (root / AI_SANDBOX_REL / "overrides.json").is_file()

    with TestClient(create_app()) as client:
        created = client.post("/sessions")
        assert created.status_code == 201
        sid = created.json()["session_id"]
        # 把预写沙箱挪到真实 session 目录名
        session_root = workspace / sid
        session_root.mkdir(parents=True, exist_ok=True)
        _write_json(session_root / "config" / "game_config.json", _BASE)
        (session_root / "core" / AI_SANDBOX_REL).mkdir(parents=True, exist_ok=True)
        (session_root / "core" / AI_SANDBOX_REL / "overrides.json").write_text(
            '{"tuning":{}}\n', encoding="utf-8"
        )
        (session_root / "core" / "player_platformer.gd").write_text(
            "extends CharacterBody2D\n", encoding="utf-8"
        )

        released = client.post(f"/sessions/{sid}/release")
        assert released.status_code == 200
        body = released.json()
        assert body["deleted"] is True
        assert "harvest" in body
        assert not session_root.exists()


def test_remove_workspace_wipes_sandbox(tmp_path: Path) -> None:
    import uuid

    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    sid = str(uuid.uuid4())
    _write_json(templates / "platformer" / "config" / "game_config.json", _BASE)
    root = workspace / sid
    root.mkdir(parents=True)
    write_overrides_json(
        root, workspace, templates, "platformer", {"theme": {"title": "临时"}}
    )
    assert (root / AI_SANDBOX_REL / "overrides.json").is_file()
    assert remove_workspace(workspace, sid) is True
    assert not root.exists()


# ── 直接写盘边界 ──────────────────────────────────────────────────────────────


def test_write_sandbox_file_bytes(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    rel = write_sandbox_file(
        root,
        workspace,
        templates,
        "platformer",
        f"{AI_SANDBOX_REL}/note.txt",
        b"hello-sandbox",
    )
    assert (root / rel).read_bytes() == b"hello-sandbox"


def test_destroy_idempotent(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    assert destroy_ai_sandbox(root) is False
    write_overrides_json(root, workspace, templates, "platformer", {"a": 1})
    assert destroy_ai_sandbox(root) is True
    assert destroy_ai_sandbox(root) is False


@pytest.mark.parametrize(
    "rel",
    [
        "core/ai_sandbox/../../core/player_platformer.gd",
        "core/ai_sandbox/mods/../../../templates/x.gd",
        "core/AI_SANDBOX/x.gd",  # 大小写敏感：必须精确前缀
        "core/ai_sandbox%2f../x.gd",
        "core/ai_sandbox\x00.gd",
        "core/ai_sandbox/./x.gd",  # 含 . 段视为非法（.. 规则扩展：split 含空/.）
    ],
)
def test_reject_extra_path_tricks(tree: tuple[Path, Path, Path], rel: str) -> None:
    templates, workspace, root = tree
    with pytest.raises(AiSandboxError):
        assert_sandbox_write_allowed(root, workspace, templates, "platformer", rel)


def test_reject_empty_and_whitespace_gdscript() -> None:
    with pytest.raises(AiSandboxError, match="extends"):
        validate_gdscript_content("ok.gd", "")
    with pytest.raises(AiSandboxError, match="extends"):
        validate_gdscript_content("ok.gd", "   \n\t\n")


def test_reject_javascript_bridge_and_user_load() -> None:
    with pytest.raises(AiSandboxError, match="禁止调用"):
        validate_gdscript_content(
            "ok.gd",
            "extends RefCounted\nfunc apply(b):\n\tJavaScriptBridge.eval('1')\n",
        )
    with pytest.raises(AiSandboxError, match="禁止调用"):
        validate_gdscript_content(
            "ok.gd",
            'extends RefCounted\nfunc apply(b):\n\tload("user://secret.gd")\n',
        )


def test_overrides_corrupt_json_then_replace(tree: tuple[Path, Path, Path]) -> None:
    """已有损坏 overrides.json 时，合并应当作空对象重建。"""
    templates, workspace, root = tree
    ensure = root / AI_SANDBOX_REL
    ensure.mkdir(parents=True, exist_ok=True)
    bad = ensure / "overrides.json"
    bad.write_text("{not-json", encoding="utf-8")
    write_overrides_json(root, workspace, templates, "platformer", {"tuning": {"x": 1}})
    data = json.loads(bad.read_text(encoding="utf-8"))
    assert data == {"tuning": {"x": 1}}


def test_write_non_gd_json_note_allowed(tree: tuple[Path, Path, Path]) -> None:
    """沙箱允许非 .gd 文本（如 note.json），但路径仍须在 ai_sandbox 下。"""
    templates, workspace, root = tree
    rel = write_sandbox_file(
        root,
        workspace,
        templates,
        "platformer",
        f"{AI_SANDBOX_REL}/note.json",
        '{"ok": true}\n',
    )
    assert rel.endswith("note.json")
    assert (root / AI_SANDBOX_REL / "note.json").is_file()


def test_write_skill_svg_icon(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" fill="#38bdf8"/></svg>'
    )
    rel = write_sandbox_asset(
        root, workspace, templates, "platformer", "icons/double_jump.svg", svg
    )
    assert rel.endswith("icons/double_jump.svg")
    assert (root / AI_SANDBOX_REL / "icons" / "double_jump.svg").is_file()
    with pytest.raises(AiSandboxError, match="禁止"):
        validate_svg_content("<svg><script>alert(1)</script></svg>")


def test_compile_intent_double_jump_and_coin(tree: tuple[Path, Path, Path]) -> None:
    from app.services.creative.sandbox_intent import (
        compile_user_intent,
        verify_against_request,
    )

    templates, workspace, root = tree
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    dj = compile_user_intent("加二段跳并画图标", "platformer", cfg)
    assert "double_jump" in dj["applied_capabilities"]
    assert "skill_icon" in dj["applied_capabilities"]
    assert any(c["path"] == "tuning.enabled_skills" for c in dj["changes"])
    assert any(f["filename"].endswith("double_jump.svg") for f in dj["new_files"])
    assert not verify_against_request("加二段跳并画图标", dj["applied_capabilities"])

    coin = compile_user_intent(
        "每吃到5个金币进入无敌并加速，有特效和倒计时", "platformer", cfg
    )
    assert "coin_streak_buff" in coin["applied_capabilities"]
    assert any(c["path"] == "sandbox_rules.coin_every" for c in coin["changes"])
    assert not verify_against_request(
        "每吃到5个金币进入无敌并加速，有特效和倒计时",
        coin["applied_capabilities"],
    )


def test_vague_more_skills_fills_shmup_catalog(tree: tuple[Path, Path, Path]) -> None:
    """截图用例：飞机技能太少 / 多加有趣技能 → 开满 shmup 目录技能。"""
    templates, workspace, root = tree
    # 复用 tree 的 platformer 骨架，但 nl-patch 用真实 templates 目录更稳
    from app.config import get_settings
    from app.services.workspace_guard import copy_template_to_workspace, remove_workspace
    from app.services.edu_workspace import apply_edu_workspace_patch
    import uuid

    live = get_settings()
    settings = live.model_copy(
        update={
            "templates_dir": live.templates_dir,
            "workspace_dir": workspace,
            "llm_api_key": "",
            "allow_memory_fallback": True,
        }
    )
    sid = str(uuid.uuid4())
    session_root = copy_template_to_workspace(
        settings.templates_dir, workspace, "shmup", sid
    )
    apply_edu_workspace_patch(
        session_root, "shmup", settings.templates_dir, workspace
    )
    result = apply_nl_patch(
        settings,
        session_root,
        settings.templates_dir,
        "shmup",
        "飞机技能太少了。多加有趣的技能",
    )
    assert result["ok"] is True
    assert "bomb" in result["applied_capabilities"]
    assert "laser_beam" in result["applied_capabilities"]
    skills = next(c for c in result["changes"] if c["path"] == "tuning.enabled_skills")
    assert set(skills["after"]) >= {"bomb", "laser_beam"}
    assert result["how_to_play"]
    remove_workspace(workspace, sid)


def test_dialogue_feedback_reapplies_without_api_key(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="")
    first = apply_nl_patch(
        settings, root, templates, "platformer", "加二段跳并帮我绘制图标"
    )
    assert first["ok"] is True
    assert "double_jump" in first["applied_capabilities"]
    assert first["how_to_play"]
    assert first["needs_relaunch"] is True

    second = apply_nl_patch(
        settings,
        root,
        templates,
        "platformer",
        "加二段跳并帮我绘制图标",
        history=[
            {"role": "user", "content": "加二段跳并帮我绘制图标"},
            {"role": "assistant", "content": first["message"]},
        ],
        feedback="没生效，再改一次",
    )
    assert second["ok"] is True
    assert "double_jump" in second.get("applied_capabilities", [])
    assert second["how_to_play"]


def test_stub_enables_double_jump_and_icon(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="")
    frozen = (root / "core" / "player_platformer.gd").read_text(encoding="utf-8")
    result = apply_nl_patch(
        settings, root, templates, "platformer", "给我开二段跳，并画一个技能图标"
    )
    assert result["ok"] is True
    assert result["provider"] == "stub"
    paths = {c["path"] for c in result["changes"]}
    assert "tuning.enabled_skills" in paths
    skills_change = next(c for c in result["changes"] if c["path"] == "tuning.enabled_skills")
    assert "double_jump" in skills_change["after"]
    assert any("icons/double_jump.svg" in p for p in result["sandbox_files"])
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert "double_jump" in cfg["tuning"]["enabled_skills"]
    assert (root / "core" / "player_platformer.gd").read_text(encoding="utf-8") == frozen


def test_stub_coin_streak_writes_sandbox_script(tree: tuple[Path, Path, Path]) -> None:
    templates, workspace, root = tree
    settings = _settings(templates, workspace, api_key="")
    frozen = (root / "core" / "player_platformer.gd").read_text(encoding="utf-8")
    result = apply_nl_patch(
        settings,
        root,
        templates,
        "platformer",
        "每吃到5个金币进入无敌时间，人物速度加快并且有特效。有倒计时显示",
    )
    assert result["ok"] is True
    paths = {c["path"] for c in result["changes"]}
    assert "sandbox_rules.coin_every" in paths
    assert any("coin_streak_buff.gd" in p for p in result["sandbox_files"])
    ov = json.loads((root / AI_SANDBOX_REL / "overrides.json").read_text(encoding="utf-8"))
    assert ov.get("sandbox_rules", {}).get("coin_every") == 5
    assert (root / "core" / "player_platformer.gd").read_text(encoding="utf-8") == frozen


def test_genre_context_mentions_bridge_api() -> None:
    from app.config import get_settings
    from app.services.creative.genre_context import build_genre_llm_context

    settings = get_settings()
    text = build_genre_llm_context(settings.templates_dir, "platformer")
    assert "core/" in text or "player_platformer" in text
    assert "templates" in text
    assert "现场实现" in text or "会话" in text
    # 桥仍是捷径选项（契约里），不要求正文必提 AiSandboxBridge 类名
    assert "幻想" in text or "add_method" in text


@pytest.mark.live
def test_live_dashscope_nl_patch_optional(tree: tuple[Path, Path, Path]) -> None:
    """仅当 RUN_LIVE_LLM=1 且 .env 有 Key 时执行（网络不稳时自动重试）。"""
    import os
    import time

    if os.environ.get("RUN_LIVE_LLM") != "1":
        pytest.skip("set RUN_LIVE_LLM=1 to hit DashScope")
    from app.config import get_settings

    get_settings.cache_clear()
    live = get_settings()
    if not live.llm_api_key.strip():
        pytest.skip("no LLM_API_KEY in env")

    templates, workspace, root = tree
    settings = live.model_copy(
        update={
            "templates_dir": templates,
            "workspace_dir": workspace,
            "allow_memory_fallback": True,
            "llm_timeout_sec": 60.0,
        }
    )
    result: dict = {}
    last_err = ""
    for attempt in range(3):
        result = apply_nl_patch(settings, root, templates, "platformer", "让主角跳得更高一点")
        if result.get("provider") == "agent" and result.get("ok"):
            break
        last_err = str(result.get("llm_error") or result.get("message") or "")
        time.sleep(1.5 * (attempt + 1))
    if result.get("provider") != "agent":
        if any(tok in last_err for tok in ("SSL", "urlopen", "timeout", "Timeout", "Connection")):
            pytest.skip(f"DashScope 网络/SSL 不稳定，离线套件已通过；跳过 live: {last_err[:160]}")
        pytest.fail(f"after retries llm_error={last_err!r}")
    assert result["ok"] is True
    assert result["provider"] == "agent"
