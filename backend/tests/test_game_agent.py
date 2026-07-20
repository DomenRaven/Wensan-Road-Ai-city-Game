"""会话智能体工作区读写 + nl-patch agent / 无 Key stub。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.agent_workspace import (
    AgentWorkspaceError,
    list_workspace_tree,
    read_workspace_file,
    write_workspace_file,
)
from app.services.creative.learned_skills import enable_catalog_skill
from app.services.creative.llm_patch import apply_nl_patch


def _settings(templates: Path, workspace: Path, api_key: str = "sk-test") -> Settings:
    learned = workspace.parent / "learned_skills_test"
    learned.mkdir(parents=True, exist_ok=True)
    ref = workspace.parent / "reference_skills_test"
    ref.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        reference_skills_dir=ref,
        allow_memory_fallback=True,
        llm_api_key=api_key,
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
        llm_timeout_sec=5.0,
        agent_max_rounds=16,
        agent_soft_extra_rounds=16,
        agent_wall_clock_sec=360.0,
    )


def _mini_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    genre = "platformer"
    cfg = {
        "meta": {"genre": genre},
        "tuning": {
            "player": {"move_speed": 200, "jump_velocity": -400},
            "enabled_skills": [],
        },
        "theme": {"title": "测"},
    }
    (templates / genre / "config").mkdir(parents=True)
    (templates / genre / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    (templates / genre / "core").mkdir(parents=True)
    (templates / genre / "core" / "player.gd").write_text(
        "extends CharacterBody2D\n", encoding="utf-8"
    )
    root = workspace / "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    (root / "core").mkdir(parents=True)
    (root / "core" / "player.gd").write_text("extends CharacterBody2D\n", encoding="utf-8")
    return templates, workspace, root


def test_agent_can_write_session_core_not_templates(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    rel = write_workspace_file(
        root,
        workspace,
        templates,
        "core/player.gd",
        "extends CharacterBody2D\n# agent edit\n",
    )
    assert rel == "core/player.gd"
    assert "agent edit" in (root / "core" / "player.gd").read_text(encoding="utf-8")
    assert "# agent edit" not in (
        templates / "platformer" / "core" / "player.gd"
    ).read_text(encoding="utf-8")
    with pytest.raises(AgentWorkspaceError):
        write_workspace_file(root, workspace, templates, "project.godot", "hack=1\n")


def test_agent_sandbox_new_file_and_list(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    write_workspace_file(
        root,
        workspace,
        templates,
        "core/ai_sandbox/fun_buff.gd",
        "extends Node\nfunc apply(bridge) -> void:\n\tpass\n",
    )
    entries = list_workspace_tree(root, workspace, templates, "core")
    assert any(e.endswith("fun_buff.gd") for e in entries)
    text = read_workspace_file(
        root, workspace, templates, "core/ai_sandbox/fun_buff.gd"
    )
    assert "func apply" in text


def test_nl_patch_agent_with_key_stub_without(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")

    fake_agent = {
        "ok": True,
        "provider": "agent",
        "summary": "已加趣味技能",
        "message": "已加趣味技能",
        "sandbox_files": ["core/ai_sandbox/fun.gd"],
        "how_to_play": ["重开后按技能键"],
        "agent_rounds": 2,
    }
    with patch(
        "app.services.creative.llm_patch.run_game_agent", return_value=fake_agent
    ):
        result = apply_nl_patch(
            settings, root, templates, "platformer", "多加有趣的技能"
        )
    assert result["ok"] is True
    assert result["provider"] == "agent"
    assert "core/ai_sandbox/fun.gd" in result["sandbox_files"]

    settings2 = _settings(templates, workspace, api_key="")
    result2 = apply_nl_patch(
        settings2, root, templates, "platformer", "加二段跳并画图标"
    )
    assert result2["ok"] is True
    assert result2["provider"] == "stub"


def test_named_laser_enters_llm_not_express(tmp_path: Path) -> None:
    """7.19：点名「发射激光」进完整 Agent，禁止 catalog express 秒开。"""
    from app.services.creative.game_agent import run_game_agent

    templates, workspace, root = _mini_tree(tmp_path)
    shmup = templates / "shmup"
    (shmup / "config").mkdir(parents=True, exist_ok=True)
    (shmup / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "meta": {"genre": "shmup"},
                "tuning": {"enabled_skills": [], "player": {"move_speed": 200}},
                "theme": {"title": "测"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "config" / "game_config.json").write_text(
        json.dumps(
            {
                "meta": {"genre": "shmup"},
                "tuning": {"enabled_skills": [], "player": {"move_speed": 200}},
                "theme": {"title": "测"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # HF-10 最小玩家
    (root / "core" / "player_ship.gd").write_text("extends Area2D\n", encoding="utf-8")
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "scenes" / "player.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n'
        '[node name="Player" type="Area2D" groups=["player"]]\n'
        '[node name="Sprite2D" type="Sprite2D" parent="."]\n',
        encoding="utf-8",
    )
    settings = _settings(templates, workspace, api_key="sk-test")
    done_payload = {
        "understanding": "要激光",
        "goals": ["实现激光或按需参考 catalog"],
        "thought": "读盘后施工",
        "actions": [
            {
                "tool": "done",
                "summary": "已按你的要求处理激光，请重开后点屏幕下方按钮试玩",
                "how_to_play": ["请重新启动游戏", "点屏幕下方按钮试用"],
            }
        ],
    }
    with patch(
        "app.services.creative.game_agent._llm_turn",
        return_value=done_payload,
    ) as llm:
        with patch(
            "app.services.creative.game_agent.refresh_ai_sandbox_bridge",
            return_value=True,
        ):
            with patch(
                "app.services.creative.game_agent.run_done_gates",
                return_value=[],
            ):
                out = run_game_agent(
                    settings, root, "shmup", "我想加发射激光", max_rounds=2
                )
    assert out["ok"] is True
    assert out.get("express") is not True
    assert out["agent_rounds"] >= 1
    llm.assert_called()


def test_enable_catalog_skill_writes_config(tmp_path: Path) -> None:
    templates, workspace, root = _mini_tree(tmp_path)
    out = enable_catalog_skill(root, "platformer", "double_jump")
    assert out["skill_id"] == "double_jump"
    cfg = json.loads((root / "config" / "game_config.json").read_text(encoding="utf-8"))
    assert "double_jump" in cfg["tuning"]["enabled_skills"]


def test_salvage_bugfix_rollback_does_not_claim_playable(tmp_path: Path) -> None:
    """HF-9：故障局回滚不得声称「能正常玩」。"""
    from app.services.creative.game_agent import _salvage_agent_return

    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")
    # 本轮「写坏」了脚本，dry_run 会失败 → 走回滚分支
    bad = root / "core" / "player.gd"
    bad.write_text("extends CharacterBody2D\nfunc _ready():\n\tbroken(\n", encoding="utf-8")
    with patch(
        "app.services.creative.game_agent.dry_run_godot",
        return_value={"ok": False, "skipped": False, "errors": ["Node not found: ../Player"]},
    ):
        out = _salvage_agent_return(
            settings,
            root,
            "platformer",
            route={"intent": "B", "skill_ids": [], "recipe_id": "运行时显示/启动故障"},
            written=["core/player.gd"],
            catalog_changed=False,
            pre_turn_snapshot={"core/player.gd": b"extends CharacterBody2D\n"},
            last_summary="",
            last_how=[],
            last_understanding="人物消失需要修节点路径",
            plan_goals=["修玩家可见"],
            progress_events=[],
            rounds_used=3,
            reason='dry_run: Node not found: "../Player"',
            bugfix=True,
        )
    assert out["ok"] is True
    assert out.get("partial") is True
    assert out.get("playability_suspect") is True
    msg = out["message"]
    assert "能正常玩" not in msg
    assert "没弄坏" not in msg
    assert (
        "原先" in msg
        or "可能还在" in msg
        or "人物仍有问题" in msg
        or "专修" in msg
    )


def test_llm_bad_json_salvages_inside_agent(tmp_path: Path) -> None:
    """HF-9：Agent 内 LLM 坏 JSON 应 salvage，不抛到入口上锁。"""
    from app.services.creative.game_agent import run_game_agent

    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")
    with patch(
        "app.services.creative.game_agent._llm_turn",
        side_effect=json.JSONDecodeError("Expecting ',' delimiter", "bad", 10),
    ):
        with patch(
            "app.services.creative.game_agent._can_catalog_express",
            return_value=False,
        ):
            out = run_game_agent(
                settings,
                root,
                "platformer",
                "人物消失不见了",
                max_rounds=2,
            )
    assert out["ok"] is True
    assert out.get("partial") is True
    assert "没改成" not in out["message"]
    assert "换个说法" not in out["message"]


def test_hf11_intent_b_color_not_playability_critical() -> None:
    """HF-11：颜色反馈可走 Intent B，但不因 B 打成可玩性危急窄路径。"""
    from app.services.creative.agent_contracts import load_contract
    from app.services.creative.game_agent import (
        _is_bugfix_turn,
        _is_playability_critical_turn,
    )
    from app.services.creative.intent_router import route_intent

    text = "发完大力球，之后球还是红色，颜色没有恢复"
    route = route_intent(text, load_contract("pingpong"))
    assert route["intent"] == "B"
    assert _is_playability_critical_turn(text, "") is False
    # 仍可标反馈修盘（没恢复），但不等于「只修玩家可见」
    assert _is_bugfix_turn(text, "", route) is True
    assert _is_bugfix_turn("开氮气", "", route) is False


def test_hf12_playability_white_screen_tip_urges_write() -> None:
    """HF-12：白屏可玩性提示须催写盘，避免只读空转。"""
    from app.services.creative.game_agent import (
        _AGENT_SYSTEM,
        _is_playability_critical_turn,
    )

    assert _is_playability_critical_turn("白屏了，人看不见", "") is True
    assert "prompt_truncated" in _AGENT_SYSTEM
    assert "content_resume_offset" in _AGENT_SYSTEM
    assert "无需再分页" in _AGENT_SYSTEM
    assert "ensure_player_visibility" in _AGENT_SYSTEM


def test_hf12_write_file_blocks_existing_player_critical(tmp_path: Path) -> None:
    """已有玩家核心文件禁止 write_file 整文件重建。"""
    from app.services.creative.game_agent import _run_action

    templates, workspace, root = _mini_tree(tmp_path)
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "core" / "player_runner.gd").write_text(
        "extends CharacterBody2D\n\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (root / "scenes" / "player.tscn").write_text(
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n',
        encoding="utf-8",
    )
    settings = _settings(templates, workspace)
    with pytest.raises(Exception) as ei:
        _run_action(
            settings,
            root,
            "parkour",
            {
                "tool": "write_file",
                "path": "core/player_runner.gd",
                "content": "extends CharacterBody2D\n# stub rebuild\n",
            },
            {},
            [],
        )
    assert "replace_text" in str(ei.value)
    assert "关键玩法" in str(ei.value) or "ensure_player_visibility" in str(ei.value)


def test_hf12_write_file_blocks_gameplay_chain_and_restores(
    tmp_path: Path,
) -> None:
    """关键玩法链（非玩家脚本）缺失时：从模板恢复并拒绝 stub 整写。"""
    from app.services.creative.game_agent import _run_action

    templates, workspace, root = _mini_tree(tmp_path)
    genre = "pingpong"
    gdir = templates / genre / "core"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "ball.gd").write_text(
        "extends Area2D\n"
        "signal scored(side: String)\n"
        "func _try_paddle_bounce(p, d) -> bool:\n\treturn true\n"
        "func _apply_paddle_bounce(p, d) -> void:\n\tpass\n"
        "func _check_scoring() -> void:\n\tpass\n"
        "func reset_to_center() -> void:\n\tpass\n"
        "func halt() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    # 会话内故意缺失 ball.gd
    settings = _settings(templates, workspace)
    with pytest.raises(Exception) as ei:
        _run_action(
            settings,
            root,
            genre,
            {
                "tool": "write_file",
                "path": "core/ball.gd",
                "content": "extends Area2D\nfunc start():\n\tpass\n",
            },
            {},
            [],
        )
    assert "模板恢复" in str(ei.value) or "replace_text" in str(ei.value)
    assert (root / "core" / "ball.gd").is_file()
    restored = (root / "core" / "ball.gd").read_text(encoding="utf-8")
    assert "_try_paddle_bounce" in restored


def test_hf12_schedule_actions_keeps_ensure_and_done() -> None:
    """读盘工具再多，也不应挤掉 ensure_player_visibility / done。"""
    from app.services.creative.game_agent import _schedule_actions_for_round

    actions = [{"tool": "diagnose_workspace"}]
    actions += [{"tool": "search_in_file", "path": "core/a.gd", "query": f"q{i}"} for i in range(12)]
    actions += [
        {"tool": "ensure_player_visibility"},
        {"tool": "self_check", "summary": "x", "how_to_play": ["重开"]},
        {"tool": "done", "summary": "已加固可见性", "how_to_play": ["重开后查看"]},
    ]
    scheduled = _schedule_actions_for_round(actions, max_total=10)
    tools = [a["tool"] for a in scheduled]
    assert "ensure_player_visibility" in tools
    assert "done" in tools
    assert tools.index("ensure_player_visibility") < tools.index("done")
    assert sum(1 for t in tools if t == "search_in_file") <= 5


def test_hf12_ensure_player_visibility_restores_missing_from_template(
    tmp_path: Path,
) -> None:
    """玩家核心缺失时从 templates 恢复，而不是让 LLM 瞎编 stub。"""
    from app.services.creative.game_agent import _run_ensure_player_visibility

    templates, workspace, root = _mini_tree(tmp_path)
    genre = "parkour"
    (templates / genre / "core").mkdir(parents=True, exist_ok=True)
    (templates / genre / "scenes").mkdir(parents=True, exist_ok=True)
    (templates / genre / "core" / "player_runner.gd").write_text(
        "extends CharacterBody2D\n\nfunc _ready() -> void:\n\tpass\n",
        encoding="utf-8",
    )
    (templates / genre / "scenes" / "player.tscn").write_text(
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n',
        encoding="utf-8",
    )
    # 会话内故意缺失
    (root / "core" / "player_runner.gd").unlink(missing_ok=True)
    settings = _settings(templates, workspace)
    out = _run_ensure_player_visibility(settings, root, genre)
    assert out.get("ok") is True
    assert (root / "core" / "player_runner.gd").is_file()
    assert "core/player_runner.gd" in (out.get("written") or [])


def test_hf12_ensure_player_visibility_hardens_parkour(tmp_path: Path) -> None:
    """HF-12：ensure_player_visibility 对玩家场景/脚本做最小可见性加固。"""
    from app.services.creative.game_agent import _run_ensure_player_visibility

    templates, workspace, root = _mini_tree(tmp_path)
    # 按 parkour 契约路径布置最小玩家文件
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "scenes" / "player.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://core/player_runner.gd" id="1"]\n\n'
        '[node name="Player" type="CharacterBody2D" groups=["player"]]\n'
        "script = ExtResource(\"1\")\n\n"
        '[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]\n',
        encoding="utf-8",
    )
    (root / "core" / "player_runner.gd").write_text(
        "extends CharacterBody2D\n\n"
        "func _ready() -> void:\n"
        "\tglobal_position = Vector2(100, 300)\n",
        encoding="utf-8",
    )
    settings = _settings(templates, workspace)
    out = _run_ensure_player_visibility(settings, root, "parkour")
    assert out.get("ok") is True
    written = out.get("written") or []
    assert "scenes/player.tscn" in written
    assert "core/player_runner.gd" in written
    scene = (root / "scenes" / "player.tscn").read_text(encoding="utf-8")
    script = (root / "core" / "player_runner.gd").read_text(encoding="utf-8")
    assert "visible = true" in scene
    assert "modulate = Color(1, 1, 1, 1)" in scene
    assert "visible = true" in script
    assert "modulate = Color(1, 1, 1, 1)" in script
    # 幂等：再跑仍 ok，且 noop（无新写入）
    out2 = _run_ensure_player_visibility(settings, root, "parkour")
    assert out2.get("ok") is True
    assert out2.get("noop") is True
    assert out2.get("written") == []


def test_hf11_salvage_empty_write_has_no_footstep_lore(tmp_path: Path) -> None:
    from app.services.creative.game_agent import _salvage_agent_return

    templates, workspace, root = _mini_tree(tmp_path)
    settings = _settings(templates, workspace, api_key="sk-test")
    out = _salvage_agent_return(
        settings,
        root,
        "pingpong",
        route={"intent": "B", "skill_ids": []},
        written=[],
        catalog_changed=False,
        pre_turn_snapshot={},
        last_summary="",
        last_how=[],
        last_understanding="球色没有恢复",
        plan_goals=["恢复球色"],
        progress_events=[],
        rounds_used=3,
        reason="门禁多次未通过: 没有任何有效写入或 catalog 变更，不能 done",
        bugfix=True,
    )
    msg = out["message"]
    assert "脚步" not in msg
    assert "没改" in msg or "没动" in msg
    assert out.get("sandbox_files") == []


def test_hf11_llm_facing_prompts_are_affirmative() -> None:
    """给 LLM 的主提示/品类 playbook/轮次注入：正向工作法，无窄化劫持。"""
    from app.services.creative.game_agent import (
        _AGENT_SYSTEM,
        _BUGFIX_REREAD_TIP,
        _OPEN_READ_WORK_TIP,
        _PLAYABILITY_WORK_TIP,
        _PRESENTATION_WORK_TIP,
        _SHMUP_DROP_LOOT_TIP,
        _TIME_CYCLE_WORK_TIP,
    )
    from app.services.creative.genre_context import _GENRE_PLAYBOOK
    from app.services.creative.intent_router import format_route_for_prompt

    bad_tokens = (
        "脚步",
        "只修玩家",
        "不要假设",
        "故障·强制",
        "禁止空 done",
        "只能改玩家",
        "严禁",
        "反模式",
        "勿因",
        "不要写已修好",
        "不够过门禁",
        "打敌机→捡掉落",  # 仅允许出现在 shmup 门控材料，不进全局 system
    )
    blobs: list[str] = [
        _AGENT_SYSTEM,
        *[p for p in _GENRE_PLAYBOOK.values()],
        _OPEN_READ_WORK_TIP,
        _PLAYABILITY_WORK_TIP,
        _SHMUP_DROP_LOOT_TIP,
        _TIME_CYCLE_WORK_TIP,
        _PRESENTATION_WORK_TIP,
        _BUGFIX_REREAD_TIP,
    ]
    route_txt = format_route_for_prompt(
        {
            "intent": "B",
            "recipe_id": "t",
            "hint": "先读盘再写",
            "skill_ids": [],
            "stop": False,
        }
    )
    blobs.append(route_txt)
    joined = "\n".join(blobs)
    for tok in bad_tokens:
        # shmup playbook / 掉落 tip 可保留品类试玩句；全局 system 与通用 tip 不得含
        if tok == "打敌机→捡掉落":
            assert tok not in _AGENT_SYSTEM
            assert tok not in _OPEN_READ_WORK_TIP
            assert tok not in _PLAYABILITY_WORK_TIP
            continue
        assert tok not in joined, tok
    assert "开放读盘" in _AGENT_SYSTEM or "读盘" in _AGENT_SYSTEM
    assert "禁止" not in _AGENT_SYSTEM
    assert "core/ball.gd" not in _AGENT_SYSTEM
    assert "laser_beam" not in _AGENT_SYSTEM
    assert "本品类玩家或玩法脚本" in _AGENT_SYSTEM
    assert "ensure_player_visibility" in _PLAYABILITY_WORK_TIP
    assert "apply_shmup_drop_loot_chain" in _SHMUP_DROP_LOOT_TIP
    assert "wired_by" in _TIME_CYCLE_WORK_TIP
    assert "evidence" in _TIME_CYCLE_WORK_TIP
    assert "wired_by" in _BUGFIX_REREAD_TIP
    # 通用 tip / system：场景泛化，不点名单品类机制或示例脚本
    for blob in (_AGENT_SYSTEM, _TIME_CYCLE_WORK_TIP, _PRESENTATION_WORK_TIP, _BUGFIX_REREAD_TIP, _OPEN_READ_WORK_TIP):
        assert "_update_god_mode" not in blob
        assert "god_mode" not in blob
        assert "player_ship.gd" not in blob
        assert "禁止" not in blob
    for playbook in _GENRE_PLAYBOOK.values():
        assert "禁止" not in playbook

def test_hf11_recent_writes_prompt(tmp_path: Path) -> None:
    from app.services.creative.learned_skills import (
        append_session_patch_log,
        format_recent_session_writes_for_prompt,
    )

    root = tmp_path / "ws"
    root.mkdir()
    append_session_patch_log(
        root,
        {
            "ok": True,
            "user_text": "大力扣杀",
            "summary": "已实现扣杀",
            "sandbox_files": ["core/ball.gd", "core/paddle.gd"],
        },
    )
    block = format_recent_session_writes_for_prompt(root)
    assert "core/ball.gd" in block
    assert "开放读盘" in block or "近期改动" in block
    assert "最小 write_file" in block or "成对开闭" in block
    assert "禁止" not in block
    assert "空 done" not in block
