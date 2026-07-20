"""游戏创作智能体：契约注入 + 写后门禁 + 进度事件 + 多轮再改。

闭环：读契约 → 检索 Skill → 读写会话副本 → validate / assert_apis / assert_claims → 才 done。
templates 只读；无 API Key 时由调用方走离线 stub（有 Key 则只跑本智能体）。
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from app.config import Settings
from app.services.agent_workspace import (
    AgentWorkspaceError,
    align_fragment_newlines,
    assert_full_read_before_rewrite,
    existing_file_requires_replace,
    list_workspace_tree,
    list_workspace_tree_high_signal,
    read_workspace_file,
    read_workspace_file_page,
    replace_workspace_text,
    search_workspace_file,
    serialize_observations_for_followup,
    sha256_text,
    read_text_raw,
    write_workspace_file,
)
from app.services.creative.agent_contracts import (
    PLAYER_PRESENCE_BY_GENRE,
    assert_apis_in_contract,
    assert_feedback_has_real_diff,
    assert_player_presence_health,
    assert_script_structure_fidelity,
    diagnose_workspace,
    dry_run_godot,
    emit_progress,
    extract_symbols_added_from_gd,
    format_diagnose_for_prompt,
    infer_target_funcs_from_patch,
    lint_tscn_godot4,
    load_contract,
    normalize_evidence_list,
    gameplay_critical_paths,
    player_critical_paths,
    restore_last_playable_snapshot,
    run_done_gates,
    save_last_playable_snapshot,
    update_gate_error_streak,
    validate_gdscript,
    validate_player_write_content,
)
from app.services.creative.agent_live_trace import (
    live_trace_enabled,
    trace_done,
    trace_gate,
    trace_llm_round,
    trace_tools,
)
from app.services.creative.genre_context import genre_context_as_system_suffix
from app.services.creative.intent_router import (  # noqa: F401
    is_laser_bomb_drop_request,
    enforce_route_on_actions,
    format_route_for_prompt,
    is_drop_loot_request,
    route_intent,
)
from app.services.creative.learned_skills import (
    LearnedSkillsError,
    bump_skill_counts,
    enable_catalog_skill,
    format_recent_session_writes_for_prompt,
    format_skills_for_prompt,
    read_session_patch_log,
    search_learned_skills,
)
from app.services.creative.reference_skills import (
    format_reference_summary_for_prompt,
    read_reference_skill,
)
from app.services.creative.sandbox_intent import catalog_for_prompt
from app.services.edu_workspace import (
    patch_shmup_mouse_steer_guard,
    refresh_ai_sandbox_bridge,
)

_AGENT_SYSTEM: str = """你是 GameForge K12 展厅的游戏改关助手。对话与推理对齐常见大模型：先听懂本轮、拆解目标，再动手改游戏。

【总原则 · 开放读盘 · 安全最小施工】
- 新需求与用户反馈（例如没生效、外观/手感不对、数值不符）用同一套循环：
  diagnose → list_dir / read_file|search_in_file → 对照用户原话做差分 → replace_text（或小文件 write_file）→ self_check → done
- 优先阅读「本局近期改动」清单中的文件；核对状态是否成对开闭（外观、特效、速度、充能、无敌等）
- Intent / Catalog / playbook / Reference 是可选材料；最终以会话磁盘与用户原话为准
- done 须有真实写入（或诚实说明未改原因）；带条件的需求用会话脚本实现条件本身
- done / self_check 须带 evidence[]：每条含 path、symbol、wired_by（_process / _physics_process / Timer 等）
- 「每过 / 每隔 N 秒」类周期：用 `_process(delta)` 或 Timer 做时间轴，并在 evidence 写明 symbol 与 wired_by
- 「没生效」：先 read 本局近期改动，对照原话列出差分（接线、数值、开闭成对），再最小 patch；本轮 summary 对应真实代码 diff

【对话】
- 本轮用户原话优先级最高；历史只作背景
- done.summary 用自然中文直接回答本轮：做了什么 / 怎么试玩
- 找可操控角色：get_tree().get_nodes_in_group("player") 或 AiSandboxBridge.get_player_node()
  （角色多在 GameRoot/LevelRoot 下；品类细节见接线 playbook）
- 保持角色可玩：根节点保持可见与 group=player；视觉效果作用于 Sprite 并在结束时恢复
- 改 config/game_config.json：先 read_file，再合并字段后写回
- 长期库 / Reference：仅在与本轮原话明显相关时复用

【每轮输出】
1. understanding：一句话复述本轮要什么
2. goals：1～5 条可验收子目标（条件/数值/手感拆开）
3. actions：先读盘再施工，最后 self_check → done
4. summary 覆盖全部 goals；试玩说明含重开与触屏操作
5. evidence 覆盖各 goals（path / symbol / wired_by，供机器核对）

【创作】
- 可写范围：会话 workspace（core/scenes/config/ai_sandbox）
- templates：只读参考
- 桥 API：以契约列表为准；同等效果用会话 GDScript 实现
- 实现用户要的机制本身；声称 ⊆ 磁盘
- 可用 read_reference_skill；仍以会话磁盘为准
- 新增或改写的 GDScript 关键逻辑须带简短中文 # 注释（条件、计数、开关/恢复时机）；整段粘贴须带注释

【读写习惯 · Godot 会 headless 冒烟】
- read_file 支持 offset/limit；仅当返回 eof=false 时用 next_offset 续读，或 search_in_file 定位
- 若见 prompt_truncated=true 但 eof=true：文件已读完；用 content_resume_offset / search_in_file 看未展示段后即可施工，无需再分页
- 已有大 .gd/.tscn（>6k 字符或 >120 行）：默认 replace_text（old_text 唯一命中；expected_sha256 可选）
- replace_text 会自动对齐 CRLF/LF；old_text 唯一命中时陈旧 hash 不挡写入
- write_file 主要用于新文件、小配置，或 goals 标明 rewrite_scope 的完整重构
- preload / ext_resource 只指向已存在或本轮新建的文件
- 只调用目标脚本里真实存在的方法/属性；不确定就先 read_file
- 视口：get_viewport().get_visible_rect() 或 get_window().size
- 取节点：get_node_or_null 并判空
- 改已有 .tscn：保留原有节点，只增不删；复杂结构优先脚本 add_child
- 新建 .tscn：Godot 4 矩形碰撞用 size（勿 extents）；[sub_resource] 须先于 SubResource() 引用；资源头必须闭合 ]
- 新机制优先脚本 new Area2D()/add_child，避免「新建 PackedScene + preload」连环炸
- 报错含 at: res://xxx.gd:NN 时，先读该文件再改

【产品安全边界】
- 可写范围：会话 workspace；templates 只读参考
- 桥 API 以契约列表为准；同等效果用会话 GDScript 实现
- 玩家根保持可见；视觉效果作用于 Sprite 并恢复
- 掉落/拾取才开启：按本品类 playbook 接线真实掉落→拾取→效果链；how_to_play 写清试玩步骤

每轮只返回 JSON：
{
  "understanding": "一句话复述本轮需求",
  "goals": ["子目标1", "子目标2"],
  "thought": "本步计划（对应哪几条 goals）",
  "actions": [
    {"tool":"diagnose_workspace"},
    {"tool":"list_dir","path":"core"},
    {"tool":"read_file","path":"core/<本品类玩家或玩法脚本>","offset":0,"limit":8000},
    {"tool":"search_in_file","path":"core/<本品类玩家或玩法脚本>","query":"_ready","max_hits":5},
    {"tool":"replace_text","path":"core/<本品类玩家或玩法脚本>","old_text":"...","new_text":"...","expected_sha256":"..."},
    {"tool":"search_learned_skills","query":"...","k":3},
    {"tool":"read_reference_skill","which":"genre"},
    {"tool":"enable_catalog_skill","skill_id":"<契约 catalog_skills 的 id>"},
    {"tool":"refresh_ai_sandbox_bridge"},
    {"tool":"write_file","path":"core/custom_mechanic.gd","content":"..."},
    {"tool":"validate_gdscript","path":"core/custom_mechanic.gd"},
    {"tool":"self_check","summary":"草稿回复","how_to_play":["重开后点…"],"evidence":[{"goal":"子目标1","path":"core/<脚本>.gd","symbol":"_update_xxx","wired_by":"_process"}]},
    {"tool":"ensure_player_visibility"},
    {"tool":"emit_progress","stage":"write_changes","detail":"..."},
    {"tool":"done","summary":"自然中文回复本轮原话（覆盖各 goals）","how_to_play":["试玩1","试玩2"],"evidence":[{"goal":"子目标1","path":"core/<脚本>.gd","symbol":"_update_xxx","wired_by":"_process","note":"可选说明"}]}
  ]
}
工具：diagnose_workspace | list_dir | read_file | search_in_file | replace_text | write_file | apply_shmup_drop_loot_chain | ensure_player_visibility | enable_catalog_skill | patch_mouse_steer_guard | refresh_ai_sandbox_bridge | ensure_touch_skill_buttons | search_learned_skills | read_reference_skill | validate_gdscript | self_check | emit_progress | done
"""

# HF-11/14：注入 LLM 的工作法提示（正向·品类泛化；品类窄句仅门控后附加）
_OPEN_READ_WORK_TIP: str = (
    "【开放读盘·本轮工作法】以用户原话为验收标准；"
    "先 diagnose + read_file（优先本局近期改动路径）；"
    "核对相关状态是否成对开闭；用 replace_text 最小 patch 后再 done。"
)
_TIME_CYCLE_WORK_TIP: str = (
    "【时间周期·接线证据】用户要「每过/每隔 N 秒」或冷却循环时："
    "用 delta 累加或 Timer 实现更新函数，并在 _process / _physics_process 中调用；"
    "done.evidence 写清 path、symbol（更新函数名）、wired_by（_process 或 Timer）；"
    "HUD/开关与更新函数同一机制闭环后再 done。"
)
_PRESENTATION_WORK_TIP: str = (
    "【UI 可见·表现验收】goals 含进度条/冷却条/图标显示时："
    "场景须有对应 Control 节点，并在 _process/_physics_process/Timer 路径写入 "
    "ProgressBar.value（或 ratio）或 TextureRect.texture（或可见占位）；"
    "done 时机器会核对可见驱动，请与 evidence 一并说明接线。"
)
_BUGFIX_REREAD_TIP: str = (
    "【没生效·真差分】先 read 上轮改过的脚本与 config，"
    "对照用户原话核对：符号是否已定义、是否在 _process/_physics_process/Timer 被调用、"
    "相关状态是否成对开闭；本轮用 replace_text 写出可核对的代码 diff，"
    "done.evidence 写明 path/symbol/wired_by，summary 与磁盘一致。"
)
_PLAYABILITY_WORK_TIP: str = (
    "【可玩性提示】本轮描述像白屏或角色看不见："
    "先 diagnose + 读玩家脚本/场景与本局近期改动；"
    "用 search_in_file 查 visible / modulate / hide。"
    "定位到缺陷后立刻 replace_text；"
    "若未见隐藏/透明问题或需快速加固：优先调用 ensure_player_visibility，"
    "再 self_check→done。"
    "summary 只陈述磁盘上已完成的改动。"
)
_SHMUP_DROP_LOOT_TIP: str = (
    "【掉落物施工】本轮优先调用工具 apply_shmup_drop_loot_chain "
    "（一次写齐 powerup_types + player_ship.apply_powerup 拾取解锁）。"
    "若手写：须同时改 core/player_ship.gd 的 apply_powerup，"
    "以及 powerup_pickup / enemy_spawner 的掉落管道。"
    "开局 tuning.enabled_skills 保持空列表；"
    "laser_beam/bomb 仅在拾取后写入 config。"
)
_MULTI_GOALS_WORK_TIP: str = (
    "【多目标建议】本轮 goals 较多时，可先完成 2～3 条并 self_check→done，"
    "其余目标用户可下一轮继续；请在 evidence/summary 与磁盘一致后再宣称完成。"
)


_BUGFIX_HINTS: re.Pattern[str] = re.compile(
    r"没生效|不发射|没反应|不能用|只有.?键|人物.*消失|不显示|白屏|黑屏|"
    r"打不开|没法.*启动|闪退|报错|修复"
)
_TIME_CYCLE_HINTS: re.Pattern[str] = re.compile(
    r"每过\s*\d+\s*秒|每隔\s*\d+\s*秒|每\s*\d+\s*秒|"
    r"冷却\s*\d+|cd\s*\d+|N\s*秒后|秒后(进入|触发|开启)|"
    r"计时|倒计时|周期"
)
_PRESENTATION_HINTS: re.Pattern[str] = re.compile(
    r"进度条|冷却条|充能条|ProgressBar|"
    r"图标|命数图标|血量图标|生命图标|LivesDisplay"
)
_PLAYABILITY_CRITICAL: re.Pattern[str] = re.compile(
    r"人物.*消失|角色.*消失|人不显示|看不见.*人|人没了|角色没了|"
    r"白屏|黑屏|看不到画|没有画面|没法.*启动|无法启动|打不开|闪退"
)
_NEEDS_LLM_CREATE: re.Pattern[str] = re.compile(
    r"Boss|关卡编辑|新敌人|自己写|前所未有|改引擎|联机|存档"
)


def _can_catalog_express(route: dict[str, Any], user_text: str, feedback: str) -> bool:
    """7.19 / 总纲：有 Key 主路径禁止 catalog 秒开。保留函数供单测断言恒 False。"""
    _ = (route, user_text, feedback)
    return False


def _restore_critical_from_template(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    rel: str,
) -> bool:
    """会话内关键文件缺失时，从 templates/{genre}/ 拷回（不改冻结源）。"""
    import shutil

    rel_n = rel.replace("\\", "/")
    src = settings.templates_dir / genre / rel_n
    if not src.is_file():
        return False
    dst = workspace_root / rel_n
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.is_file()


def _run_ensure_player_visibility(
    settings: Settings,
    workspace_root: Path,
    genre: str,
) -> dict[str, Any]:
    """可玩性危急：对玩家场景根 + 脚本 _ready 做最小可见性加固（七品类通用）。"""
    cfg = PLAYER_PRESENCE_BY_GENRE.get(genre) or {}
    script_rel = str(cfg.get("script") or "").replace("\\", "/")
    scene_rel = str(cfg.get("scene") or "scenes/player.tscn").replace("\\", "/")
    scene_node = str(cfg.get("scene_node") or "Player")
    written: list[str] = []
    notes: list[str] = []

    # 缺失时先从模板恢复，禁止 LLM 整文件瞎编玩家核心
    for rel in (script_rel, scene_rel):
        if not rel:
            continue
        target = workspace_root / rel
        if not target.is_file():
            if _restore_critical_from_template(settings, workspace_root, genre, rel):
                written.append(rel)
                notes.append(f"{rel} 已从模板恢复")
            else:
                raise AgentWorkspaceError(
                    f"ensure_player_visibility：缺少 {rel} 且模板中也不存在"
                )

    scene_path = workspace_root / scene_rel
    if scene_path.is_file():
        text = read_text_raw(scene_path)
        # 节点行可能含 groups=["player"]；兼容 \r\n
        node_re = re.compile(
            rf'(\[node name="{re.escape(scene_node)}"[^\r\n]*\]\r?\n)',
            re.M,
        )
        m = node_re.search(text)
        if m:
            start = m.end()
            rest = text[start:]
            next_node = re.search(r"\r?\n\[node ", rest)
            block = rest[: next_node.start()] if next_node else rest
            nl = "\r\n" if "\r\n" in text else "\n"
            new_block = block
            changed = False
            if re.search(r"(?m)^visible\s*=\s*false\s*$", new_block):
                new_block = re.sub(
                    r"(?m)^visible\s*=\s*false\s*$", "visible = true", new_block
                )
                changed = True
            elif not re.search(r"(?m)^visible\s*=", new_block):
                new_block = f"visible = true{nl}" + new_block
                changed = True
            if not re.search(r"(?m)^modulate\s*=", new_block):
                new_block = f"modulate = Color(1, 1, 1, 1){nl}" + new_block
                changed = True
            if changed:
                suffix = rest[next_node.start() :] if next_node else ""
                new_text = text[:start] + new_block + suffix
                write_workspace_file(
                    workspace_root,
                    settings.workspace_dir,
                    settings.templates_dir,
                    scene_rel,
                    new_text,
                )
                written.append(scene_rel)
                notes.append(f"{scene_rel} 根节点可见性已加固")

    if script_rel:
        script_path = workspace_root / script_rel
        if script_path.is_file():
            text = read_text_raw(script_path)
            has_vis = bool(
                re.search(r"(?m)^\s*visible\s*=\s*true\s*$", text)
            ) and bool(
                re.search(
                    r"(?m)^\s*modulate\s*=\s*Color\s*\(\s*1\s*,\s*1\s*,\s*1\s*,\s*1\s*\)\s*$",
                    text,
                )
            )
            if not has_vis:
                ready = re.search(
                    r"(func\s+_ready\s*\([^)]*\)\s*(?:->\s*void)?\s*:\s*\r?\n)",
                    text,
                )
                if ready:
                    nl = "\r\n" if "\r\n" in text else "\n"
                    insert = (
                        f"\tvisible = true{nl}"
                        f"\tmodulate = Color(1, 1, 1, 1){nl}"
                    )
                    new_text = text[: ready.end()] + insert + text[ready.end() :]
                    player_errs = validate_player_write_content(
                        script_rel, new_text, genre
                    )
                    if player_errs:
                        raise AgentWorkspaceError(
                            "玩家健康写入拦截: " + "; ".join(player_errs)
                        )
                    syn = validate_gdscript(new_text)
                    if syn:
                        raise AgentWorkspaceError(
                            "可见性加固语法未过: " + "; ".join(syn)
                        )
                    write_workspace_file(
                        workspace_root,
                        settings.workspace_dir,
                        settings.templates_dir,
                        script_rel,
                        new_text,
                    )
                    written.append(script_rel)
                    notes.append(f"{script_rel} _ready 可见性已加固")

    if not written:
        # 已加固：诚实 noop
        return {
            "tool": "ensure_player_visibility",
            "ok": True,
            "written": [],
            "noop": True,
            "notes": ["玩家场景/脚本已具备可见性加固，无需再改"],
            "summary": "玩家可见性已就绪，无需再改",
        }
    return {
        "tool": "ensure_player_visibility",
        "ok": True,
        "written": list(dict.fromkeys(written)),
        "noop": False,
        "notes": notes,
        "summary": "已加固玩家可见性：" + "；".join(notes),
    }


def _ensure_express_touch_pathway(
    workspace_root: Path,
    templates_dir: Path,
    genre: str,
) -> list[str]:
    """快车道补触屏接线：刷桥 + 若缺则拷贝品类 touch overlay（不改 templates 源）。"""
    written: list[str] = []
    if refresh_ai_sandbox_bridge(workspace_root, templates_dir):
        written.append("core/ai_sandbox_bridge.gd")
    overlay_name = f"{genre}_touch_overlay.gd"
    src = templates_dir / "_edu" / overlay_name
    dst = workspace_root / "core" / overlay_name
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file() or dst.read_bytes() != src.read_bytes():
            dst.write_bytes(src.read_bytes())
            written.append(f"core/{overlay_name}")
    return written


def _run_catalog_express(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    user_text: str,
    route: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """enable catalog + 刷桥/触屏，一次返回（provider=agent，非 stub）。"""
    emit_progress(workspace_root, "understand", user_text[:80] or "开预制技能")
    skill_ids = [str(s) for s in (route.get("skill_ids") or []) if str(s).strip()][:2]
    written: list[str] = []
    labels: list[str] = []
    goals = [f"开启预制技能 {sid}" for sid in skill_ids]

    emit_progress(workspace_root, "write_changes", "catalog 快车道：" + "、".join(skill_ids))
    for sid in skill_ids:
        try:
            out = enable_catalog_skill(workspace_root, genre, sid)
            written.append("config/game_config.json")
            labels.append(str(out.get("label") or sid))
        except LearnedSkillsError as exc:
            emit_progress(workspace_root, "validate", f"{sid} 未开成：{exc}")
            raise ValueError(f"catalog 快车道失败: {exc}") from exc

    written.extend(
        _ensure_express_touch_pathway(
            workspace_root, settings.templates_dir, genre
        )
    )

    label_txt = "、".join(labels) if labels else "、".join(skill_ids)
    summary = f"已为你开启「{label_txt}」。请重新启动游戏，点屏幕下方对应按钮试玩。"
    how_to_play = [
        "重要：必须重新启动游戏后新技能才会生效",
        f"点屏幕下方「{label_txt}」按钮试玩（触屏）",
    ]
    gate_errors = list(
        run_done_gates(
            workspace_root,
            written_paths=list(dict.fromkeys(written)),
            summary=summary,
            how_to_play=how_to_play,
            genre=genre,
            contract=contract,
            catalog_changed=True,
            user_text=user_text,
        )
    )
    # 快车道：缺触屏接线类错误不改走多轮 LLM（已尽量补 overlay/桥）
    soft_markers = ("runtime 未接线", "仅 L1：", "runtime 不完整")
    hard_errors = [
        e for e in gate_errors if not any(m in e for m in soft_markers)
    ]
    if hard_errors:
        raise ValueError("catalog 快车道门禁未过: " + "; ".join(hard_errors[:4]))

    emit_progress(workspace_root, "done", summary[:80])
    return {
        "ok": True,
        "provider": "agent",
        "summary": summary,
        "message": summary,
        "changes": [],
        "sandbox_files": list(dict.fromkeys(written)),
        "how_to_play": how_to_play,
        "applied_capabilities": skill_ids,
        "needs_relaunch": True,
        "verify_gaps": [],
        "repaired": False,
        "agent_rounds": 0,
        "agent_thought": "catalog express",
        "understanding": f"用户要开预制技能：{label_txt}",
        "goals": goals,
        "learned_skills": [],
        "progress": [{"stage": "done"}],
        "gate_passed": True,
        "dry_run": {},
        "intent_route": route,
        "diagnose": {},
        "express": True,
    }


_UNLOCK_HELPER_GD: str = """
func _unlock_catalog_skill(skill_id: String) -> void:
	## 掉落拾取后解锁 catalog 技能（写内存 GameConfig）
	var gc: Node = get_node_or_null("/root/GameConfig")
	if gc != null and gc.has_method("get_tuning"):
		var tuning: Dictionary = gc.call("get_tuning") as Dictionary
		var skills: Array = tuning.get("enabled_skills", []) as Array
		if skill_id not in skills:
			skills.append(skill_id)
			tuning["enabled_skills"] = skills
	var sandbox: Node = get_node_or_null("/root/AiSandboxBridge")
	if sandbox != null and sandbox.has_method("ensure_touch_skill_buttons"):
		sandbox.call("ensure_touch_skill_buttons")
"""

_LOOT_MATCH_ARMS: str = """
		"laser", "laser_beam":
			_unlock_catalog_skill("laser_beam")
		"bomb":
			_unlock_catalog_skill("bomb")
"""


def _patch_shmup_apply_powerup_loot(player_src: str) -> str:
    """在 apply_powerup 中追加 laser/bomb 解锁；已有则原样返回。"""
    has_helper = bool(re.search(r"func\s+_unlock_catalog_skill\s*\(", player_src))
    has_arms = bool(re.search(r'["\'](?:laser|bomb|laser_beam)["\']\s*:', player_src))
    if has_helper and has_arms:
        return player_src
    patched = player_src
    if not has_arms:
        m = re.search(
            r'("shield":\s*\n(?:\t.*\n)*?\t\t\t_shield_sprite\.visible\s*=\s*true\n)',
            patched,
        )
        if m:
            patched = patched.replace(m.group(1), m.group(1) + _LOOT_MATCH_ARMS, 1)
        else:
            m2 = re.search(
                r"(func\s+apply_powerup[\s\S]*?match\s+powerup_name:\n)([\s\S]*?)(\n\nfunc\s+)",
                patched,
            )
            if m2:
                patched = (
                    patched[: m2.start(2)]
                    + m2.group(2).rstrip()
                    + "\n"
                    + _LOOT_MATCH_ARMS
                    + m2.group(3)
                )
    if not re.search(r"func\s+_unlock_catalog_skill\s*\(", patched):
        m3 = re.search(
            r"(func\s+apply_powerup[\s\S]*?)(\nfunc\s+_consume_shield|\nfunc\s+)",
            patched,
        )
        if m3:
            patched = (
                patched[: m3.end(1)] + "\n" + _UNLOCK_HELPER_GD + patched[m3.start(2) :]
            )
        else:
            patched = patched.rstrip() + "\n" + _UNLOCK_HELPER_GD
    return patched


def _run_shmup_drop_loot_express(
    settings: Settings,
    workspace_root: Path,
    user_text: str,
    route: dict[str, Any],
    contract: dict[str, Any],
    *,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """shmup 掉落物确定性落地：powerup_types + apply_powerup 拾取解锁。

    HF-12：保留实现能力，供 LLM 工具调用；不再作为 pre-LLM 入口快车道。
    """
    emit_progress(workspace_root, "understand", user_text[:80] or "掉落才开")
    emit_progress(
        workspace_root, "write_changes", "掉落物链：powerup_types + apply_powerup"
    )
    written: list[str] = []
    want = {str(s).strip() for s in (skills or ["laser_beam", "bomb"]) if str(s).strip()}
    if not want:
        want = {"laser_beam", "bomb"}

    cfg_path = workspace_root / "config" / "game_config.json"
    cfg: dict[str, Any] = json.loads(cfg_path.read_text(encoding="utf-8"))
    tuning_raw = cfg.get("tuning")
    tuning: dict[str, Any] = tuning_raw if isinstance(tuning_raw, dict) else {}
    cfg["tuning"] = tuning
    types_raw = tuning.get("powerup_types")
    types: list[Any] = list(types_raw) if isinstance(types_raw, list) else []
    names = {
        str(x.get("name", "")).strip() for x in types if isinstance(x, dict)
    }
    if ("laser_beam" in want or "laser" in want) and "laser" not in names:
        types.append({"name": "laser", "frame": 14})
    if "bomb" in want and "bomb" not in names:
        types.append({"name": "bomb", "frame": 15})
    tuning["powerup_types"] = types
    tuning["enabled_skills"] = []
    write_workspace_file(
        workspace_root,
        settings.workspace_dir,
        settings.templates_dir,
        "config/game_config.json",
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
    )
    written.append("config/game_config.json")

    player_rel = "core/player_ship.gd"
    player_path = workspace_root / player_rel
    if not player_path.is_file():
        raise ValueError("掉落物链失败：缺少 core/player_ship.gd")
    raw = player_path.read_text(encoding="utf-8")
    patched = _patch_shmup_apply_powerup_loot(raw)
    if patched != raw:
        write_workspace_file(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            player_rel,
            patched,
        )
        written.append(player_rel)

    refresh_ai_sandbox_bridge(workspace_root, settings.templates_dir)
    written.append("core/ai_sandbox_bridge.gd")

    summary = (
        "已把激光和炸弹改成敌机掉落物：开局没有技能按钮，"
        "打掉敌机捡到对应道具后才会解锁激光/炸弹。"
    )
    how_to_play = [
        "重要：必须重新启动游戏后改动才会生效",
        "触屏移动飞机，击落敌机，飞过去捡掉落的激光/炸弹道具",
        "捡到后屏幕下方才会出现对应按钮，再点按使用",
    ]
    gate_errors = list(
        run_done_gates(
            workspace_root,
            written_paths=list(dict.fromkeys(written)),
            summary=summary,
            how_to_play=how_to_play,
            genre="shmup",
            contract=contract,
            catalog_changed=False,
            user_text=user_text,
        )
    )
    if gate_errors:
        raise ValueError("掉落物链门禁失败: " + "; ".join(gate_errors[:4]))

    emit_progress(workspace_root, "done", summary[:80])
    return {
        "ok": True,
        "provider": "agent",
        "summary": summary,
        "message": summary,
        "changes": [],
        "sandbox_files": list(dict.fromkeys(written)),
        "how_to_play": how_to_play,
        "applied_capabilities": ["drop_loot_laser", "drop_loot_bomb"],
        "needs_relaunch": True,
        "verify_gaps": [],
        "repaired": False,
        "agent_rounds": 1,
        "agent_thought": "apply_shmup_drop_loot_chain",
        "understanding": "把激光和炸弹做成敌机掉落，捡到才解锁",
        "goals": [
            "powerup_types 含 laser/bomb",
            "apply_powerup 拾取解锁",
            "开局 enabled_skills 为空",
        ],
        "learned_skills": [],
        "progress": [{"stage": "done"}],
        "gate_passed": True,
        "dry_run": {},
        "intent_route": route,
        "diagnose": {},
        "express": False,
        "tool": "apply_shmup_drop_loot_chain",
        "path": "core/player_ship.gd",
        "written": list(dict.fromkeys(written)),
    }


def _chat_url(base_url: str) -> str:
    return base_url.strip().rstrip("/") + "/chat/completions"


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("智能体未返回 JSON")
    parsed = json.loads(m.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("智能体 JSON 不是对象")
    return parsed


def _llm_turn(
    settings: Settings,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
        "X-API-Key": settings.llm_api_key,
    }
    body = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        _chat_url(settings.llm_base_url),
        json=body,
        headers=headers,
        timeout=max(45.0, float(settings.llm_timeout_sec)),
    )
    if resp.status_code >= 400:
        raise ValueError(f"LLM HTTP {resp.status_code}: {resp.text[:300]}")
    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("LLM 无 choices")
    content = str(choices[0].get("message", {}).get("content", "")).strip()
    if not content:
        raise ValueError("LLM 内容为空")
    return _extract_json(content)


def _goals_allow_full_rewrite(plan_goals: list[str] | None) -> bool:
    blob = " ".join(plan_goals or [])
    return bool(
        re.search(r"rewrite_scope|整体重构|全文重写|完整重写|整文件重构", blob, re.I)
    )


_READISH_TOOLS: frozenset[str] = frozenset(
    {
        "diagnose_workspace",
        "list_dir",
        "read_file",
        "search_in_file",
        "search_learned_skills",
        "read_reference_skill",
        "validate_gdscript",
        "emit_progress",
    }
)
_MUTATE_TOOLS: frozenset[str] = frozenset(
    {
        "replace_text",
        "write_file",
        "apply_shmup_drop_loot_chain",
        "ensure_player_visibility",
        "enable_catalog_skill",
        "patch_mouse_steer_guard",
        "refresh_ai_sandbox_bridge",
        "ensure_touch_skill_buttons",
        "self_check",
        "done",
    }
)


def _schedule_actions_for_round(
    actions: list[Any], *, max_total: int = 10
) -> list[dict[str, Any]]:
    """读盘与施工分池：避免大量 search/read 把 ensure/done 挤出本轮窗口。"""
    reads: list[dict[str, Any]] = []
    mutates: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for raw in actions:
        if not isinstance(raw, dict):
            continue
        tool = str(raw.get("tool", "")).strip()
        if tool in _READISH_TOOLS:
            reads.append(raw)
        elif tool in _MUTATE_TOOLS:
            mutates.append(raw)
        else:
            other.append(raw)
    # 确定性施工工具靠前，避免被零散 replace/write 挤掉
    _prio = ("ensure_player_visibility", "apply_shmup_drop_loot_chain")
    mutates.sort(
        key=lambda a: (
            0 if str(a.get("tool", "")).strip() in _prio else 1
        )
    )
    mutate_cap = min(6, max(2, max_total - 2))
    picked_mut = mutates[:mutate_cap]
    remain = max_total - len(picked_mut)
    picked_read = reads[: min(5, max(0, remain - min(1, len(other))))]
    remain -= len(picked_read)
    picked_other = other[: max(0, remain)]
    return picked_read + picked_other + picked_mut


def _run_action(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    action: dict[str, Any],
    contract: dict[str, Any],
    progress_events: list[dict[str, Any]],
    *,
    written_paths: list[str] | None = None,
    catalog_changed: bool = False,
    user_text: str = "",
    read_eof_by_path: dict[str, bool] | None = None,
    plan_goals: list[str] | None = None,
    pre_turn_snapshot: dict[str, bytes | None] | None = None,
) -> dict[str, Any]:
    tool = str(action.get("tool", "")).strip()
    eof_map = read_eof_by_path if read_eof_by_path is not None else {}
    allow_rewrite = _goals_allow_full_rewrite(plan_goals)
    if tool == "diagnose_workspace":
        diag = diagnose_workspace(workspace_root, genre, contract)
        return {"tool": tool, **diag, "prompt": format_diagnose_for_prompt(diag)}
    if tool == "list_dir":
        path = str(action.get("path", "") or "")
        entries = list_workspace_tree(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
        )
        return {"tool": tool, "path": path, "entries": entries}
    if tool == "read_file":
        path = str(action.get("path", "")).strip()
        offset = int(action.get("offset") or 0)
        limit = int(action.get("limit") or 8000)
        page = read_workspace_file_page(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
            offset=offset,
            limit=limit,
        )
        if page.get("eof"):
            eof_map[str(page.get("path") or path).replace("\\", "/")] = True
        elif path:
            # 分片读过但未 EOF：显式标记，便于后续拦截整写
            eof_map.setdefault(path.replace("\\", "/"), False)
        return {"tool": tool, **page}
    if tool == "search_in_file":
        path = str(action.get("path", "")).strip()
        query = str(action.get("query", "") or "")
        max_hits = int(action.get("max_hits") or 8)
        context_lines = int(action.get("context_lines") or 2)
        result = search_workspace_file(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
            query,
            max_hits=max_hits,
            context_lines=context_lines,
        )
        return {"tool": tool, **result}
    if tool == "replace_text":
        path = str(action.get("path", "")).strip()
        old_text = str(action.get("old_text", ""))
        new_text = str(action.get("new_text", ""))
        expected = str(action.get("expected_sha256", "") or "").strip() or None
        if not path:
            raise AgentWorkspaceError("replace_text 需要 path")
        # 先在内存生成候选，再跑玩家健康 / 语法 / API，再落盘
        target = workspace_root / path.replace("\\", "/")
        if not target.is_file():
            raise AgentWorkspaceError(f"文件不存在: {path}")
        before = read_text_raw(target)
        # Win 模板 CRLF vs LLM LF：对齐后再判命中/保真
        old_aligned = align_fragment_newlines(old_text, before)
        new_aligned = align_fragment_newlines(new_text, before)
        count = before.count(old_aligned)
        if count == 0:
            raise AgentWorkspaceError(
                "replace_text 零命中: old_text 未在文件中找到"
                "（已自动尝试 CRLF/LF 对齐；请用 search_in_file 核对原文）"
            )
        if count > 1:
            raise AgentWorkspaceError(
                f"replace_text 多命中({count}): old_text 须唯一；请扩大上下文"
            )
        candidate = before.replace(old_aligned, new_aligned, 1)
        player_errs = validate_player_write_content(path, candidate, genre)
        if player_errs:
            raise AgentWorkspaceError(
                "玩家健康写入拦截: " + "; ".join(player_errs)
            )
        if path.endswith(".gd"):
            syn = validate_gdscript(candidate)
            api = assert_apis_in_contract(candidate, contract)
            if syn or api:
                raise AgentWorkspaceError(
                    "写入前校验失败: " + "; ".join(syn + api)
                )
        if path.replace("\\", "/").endswith(".tscn"):
            tscn_errs = lint_tscn_godot4(candidate)
            if tscn_errs:
                raise AgentWorkspaceError(
                    "场景写入前校验失败: " + "; ".join(tscn_errs)
                )
        hints = infer_target_funcs_from_patch(old_aligned, before)
        fidelity = assert_script_structure_fidelity(
            path,
            before,
            candidate,
            genre=genre,
            allow_rewrite=allow_rewrite,
            target_func_hints=hints or None,
        )
        if fidelity:
            raise AgentWorkspaceError(
                "结构保真门禁未过: " + "; ".join(fidelity)
            )
        result = replace_workspace_text(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
            old_aligned,
            new_aligned,
            expected_sha256=expected,
        )
        # 替换后磁盘已变，清除 eof 缓存，迫使后续再读
        eof_map.pop(path.replace("\\", "/"), None)
        symbols_added = extract_symbols_added_from_gd(new_aligned)
        return {"tool": tool, **result, "symbols_added": symbols_added}
    if tool == "write_file":
        path = str(action.get("path", "")).strip()
        content = str(action.get("content", ""))
        if not path or not content.strip():
            raise AgentWorkspaceError("write_file 需要 path 与 content")
        rel = path.replace("\\", "/")
        existing: str | None = None
        existing_path = workspace_root / rel
        if existing_path.is_file():
            try:
                existing = read_text_raw(existing_path)
            except OSError:
                existing = None
        # 玩法/玩家关键路径：禁止 LLM 整写 stub（缺失时从模板恢复，再要求 replace_text）
        critical = {p.replace("\\", "/") for p in gameplay_critical_paths(genre)}
        if rel in critical:
            if existing is None:
                if _restore_critical_from_template(
                    settings, workspace_root, genre, rel
                ):
                    raise AgentWorkspaceError(
                        f"关键玩法文件 {rel} 缺失，已从模板恢复；"
                        "请用 replace_text 做最小修改，勿 write_file 整文件重建"
                    )
                raise AgentWorkspaceError(
                    f"关键玩法文件 {rel} 缺失且模板中不存在，无法恢复"
                )
            raise AgentWorkspaceError(
                f"关键玩法文件 {rel}：请用 replace_text"
                "（玩家可见性可用 ensure_player_visibility）"
            )
        if existing_file_requires_replace(
            rel, existing, allow_full_rewrite=allow_rewrite
        ):
            raise AgentWorkspaceError(
                f"已有大文件 {rel} 默认请用 replace_text；"
                "若需整写请在 goals 标明 rewrite_scope 并先完整 read_file 到 eof"
            )
        assert_full_read_before_rewrite(
            rel,
            content,
            eof_map,
            existing_text=existing,
            allow_full_rewrite=allow_rewrite,
        )
        player_errs = validate_player_write_content(path, content, genre)
        if player_errs:
            raise AgentWorkspaceError(
                "玩家健康写入拦截: " + "; ".join(player_errs)
            )
        if path.endswith(".gd"):
            syn = validate_gdscript(content)
            api = assert_apis_in_contract(content, contract)
            if syn or api:
                raise AgentWorkspaceError(
                    "写入前校验失败: " + "; ".join(syn + api)
                )
        if rel.endswith(".tscn"):
            tscn_errs = lint_tscn_godot4(content)
            if tscn_errs:
                raise AgentWorkspaceError(
                    "场景写入前校验失败: " + "; ".join(tscn_errs)
                    + "；或改用脚本 new Area2D()/add_child 实现新机制"
                )
        if existing is not None and rel.endswith((".gd", ".tscn")):
            fidelity = assert_script_structure_fidelity(
                rel,
                existing,
                content,
                genre=genre,
                allow_rewrite=allow_rewrite,
            )
            if fidelity:
                raise AgentWorkspaceError(
                    "结构保真门禁未过: " + "; ".join(fidelity)
                )
        written = write_workspace_file(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
            content,
        )
        eof_map.pop(rel, None)
        return {"tool": tool, "path": written, "bytes": len(content.encode("utf-8"))}
    if tool == "enable_catalog_skill":
        if is_laser_bomb_drop_request(user_text or ""):
            raise AgentWorkspaceError(
                "掉落物需求请改会话 powerup_types/apply_powerup "
                "或调用 apply_shmup_drop_loot_chain（本路径走拾取链）"
            )
        skill_id = str(action.get("skill_id", "")).strip()
        if not skill_id:
            raise AgentWorkspaceError("enable_catalog_skill 需要 skill_id")
        try:
            return enable_catalog_skill(workspace_root, genre, skill_id)
        except LearnedSkillsError as exc:
            raise AgentWorkspaceError(str(exc)) from exc
    if tool == "apply_shmup_drop_loot_chain":
        if genre != "shmup":
            raise AgentWorkspaceError("apply_shmup_drop_loot_chain 仅用于 shmup")
        skills_raw = action.get("skills")
        skills: list[str]
        if isinstance(skills_raw, list):
            skills = [str(x) for x in skills_raw if str(x).strip()]
        else:
            skills = ["laser_beam", "bomb"]
        try:
            result = _run_shmup_drop_loot_express(
                settings,
                workspace_root,
                user_text or "掉落才开",
                {"intent": "C", "skill_ids": skills},
                contract,
                skills=skills,
            )
        except ValueError as exc:
            raise AgentWorkspaceError(str(exc)) from exc
        return {
            "tool": tool,
            "ok": True,
            "path": "core/player_ship.gd",
            "written": list(result.get("written") or result.get("sandbox_files") or []),
            "summary": result.get("summary"),
            "how_to_play": result.get("how_to_play"),
        }
    if tool == "ensure_player_visibility":
        return _run_ensure_player_visibility(settings, workspace_root, genre)
    if tool == "patch_mouse_steer_guard":
        ok = patch_shmup_mouse_steer_guard(workspace_root)
        return {
            "tool": tool,
            "ok": ok,
            "path": "core/player_ship.gd" if ok else "",
            "detail": (
                "已注入鼠标跟机守卫"
                if ok
                else "未能补丁 player_ship（文件缺失或已是其它结构）"
            ),
        }
    if tool == "refresh_ai_sandbox_bridge":
        ok = refresh_ai_sandbox_bridge(workspace_root, settings.templates_dir)
        return {
            "tool": tool,
            "ok": ok,
            "path": "core/ai_sandbox_bridge.gd" if ok else "",
            "detail": "已用最新 _edu 桥覆盖会话" if ok else "覆盖桥失败",
        }
    if tool == "ensure_touch_skill_buttons":
        refreshed = refresh_ai_sandbox_bridge(workspace_root, settings.templates_dir)
        return {
            "tool": tool,
            "ok": True,
            "refreshed_bridge": refreshed,
            "detail": "已刷新会话桥；重开后 ensure_touch_skill_buttons 挂技能键",
        }
    if tool == "search_learned_skills":
        query = str(action.get("query", "") or "").strip()
        k = int(action.get("k") or 5)
        hits = search_learned_skills(
            settings.learned_skills_dir, query or "技能", genre, k=max(1, min(k, 8))
        )
        return {
            "tool": tool,
            "query": query,
            "hits": [
                {
                    "skill_id": h.get("skill_id"),
                    "title": h.get("title"),
                    "summary": h.get("summary"),
                    "trigger_phrases": h.get("trigger_phrases"),
                    "how_to_play": h.get("how_to_play"),
                    "score": h.get("_score"),
                    "verified_gate": h.get("verified_gate"),
                }
                for h in hits
            ],
        }
    if tool == "read_reference_skill":
        which = str(action.get("which") or "genre").strip()
        payload = read_reference_skill(
            settings.reference_skills_dir, genre, which=which
        )
        return {"tool": tool, **payload}
    if tool == "validate_gdscript":
        path = str(action.get("path", "")).strip()
        content = str(action.get("content", "") or "")
        if path and not content:
            content = read_workspace_file(
                workspace_root,
                settings.workspace_dir,
                settings.templates_dir,
                path,
            )
        if not content.strip():
            raise AgentWorkspaceError("validate_gdscript 需要 path 或 content")
        syn = validate_gdscript(content)
        api = assert_apis_in_contract(content, contract)
        ok = not syn and not api
        return {
            "tool": tool,
            "path": path,
            "ok": ok,
            "errors": syn + api,
        }
    if tool == "self_check":
        summary = str(action.get("summary", "") or "").strip() or "自检草稿"
        how_to_play = [
            str(x) for x in (action.get("how_to_play") or []) if str(x).strip()
        ][:6]
        if not how_to_play:
            how_to_play = ["请重新启动游戏后点屏幕下方按钮试玩"]
        evidence = normalize_evidence_list(action.get("evidence"))
        require_evidence = any(
            str(p).replace("\\", "/").endswith(".gd") for p in (written_paths or [])
        )
        errs = run_done_gates(
            workspace_root,
            written_paths=list(dict.fromkeys(written_paths or [])),
            summary=summary,
            how_to_play=how_to_play,
            genre=genre,
            contract=contract,
            catalog_changed=catalog_changed,
            user_text=user_text,
            evidence=evidence,
            require_evidence=require_evidence,
            goals=plan_goals,
            pre_turn_snapshot=pre_turn_snapshot,
        )
        return {
            "tool": tool,
            "ok": not errs,
            "errors": errs,
            "evidence": evidence,
            "detail": (
                "门禁通过，可以 done"
                if not errs
                else "完成条件尚未齐备，请按 errors 继续改后再 done"
            ),
        }
    if tool == "emit_progress":
        stage = str(action.get("stage", "write_changes")).strip() or "write_changes"
        detail = str(action.get("detail", "") or "")
        ev = emit_progress(workspace_root, stage, detail)
        progress_events.append(ev)
        return {"tool": tool, **ev}
    if tool == "done":
        return {
            "tool": "done",
            "summary": str(action.get("summary", "")).strip(),
            "how_to_play": [
                str(x) for x in (action.get("how_to_play") or []) if str(x).strip()
            ][:6],
            "evidence": normalize_evidence_list(action.get("evidence")),
        }
    raise AgentWorkspaceError(f"未知工具: {tool}")


def _rollback_snapshot(
    workspace_root: Path, snapshot: dict[str, bytes | None]
) -> list[str]:
    """把本轮改过的文件恢复到回合前状态；返回已回滚的相对路径。"""
    rolled: list[str] = []
    for rel, original in snapshot.items():
        target = workspace_root / rel
        try:
            if original is None:
                if target.is_file():
                    target.unlink()
                    rolled.append(rel)
            else:
                if (not target.is_file()) or target.read_bytes() != original:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(original)
                    rolled.append(rel)
        except OSError:
            pass
    return rolled


def _is_playability_critical_turn(user_text: str, feedback: str) -> bool:
    """白屏/人物消失/打不开等可玩性危急（HF-11：仅此类附加可见性软提示）。"""
    blob = f"{user_text or ''}\n{feedback or ''}"
    return bool(_PLAYABILITY_CRITICAL.search(blob))


def _is_bugfix_turn(user_text: str, feedback: str, route: dict[str, Any] | None = None) -> bool:
    """反馈/修盘局：salvage 须承认可能未修好；HF-11：不再因 Intent B 一律打标。

    仍识别「没生效」等反馈，与创作共用开放读盘循环；可玩性危急另见
    `_is_playability_critical_turn`。
    """
    blob = f"{user_text or ''}\n{feedback or ''}"
    if _PLAYABILITY_CRITICAL.search(blob):
        return True
    if re.search(
        r"没生效|不发射|没反应|不能用|只有.?键|点了没反应|"
        r"二段跳没用|技能没用|没有恢复|没恢复|还是红|还是.*色|"
        r"修好|坏了|报错|修复",
        blob,
    ):
        return True
    if route and "运行故障" in str(route.get("recipe_id") or ""):
        return True
    # HF-11：Intent B（调参/修盘建议）不再自动等同 bugfix
    return False


def _salvage_agent_return(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    *,
    route: dict[str, Any],
    written: list[str],
    catalog_changed: bool,
    pre_turn_snapshot: dict[str, bytes | None],
    last_summary: str,
    last_how: list[str],
    last_understanding: str,
    plan_goals: list[str],
    progress_events: list[dict[str, Any]],
    rounds_used: int,
    reason: str,
    bugfix: bool = False,
) -> dict[str, Any]:
    """轮次耗尽/门禁多次未过时的兜底：尽力交付本轮已改内容，绝不上锁、绝不把游戏改到打不开。

    - 若磁盘能加载（或无代码改动）：返回本轮改动 = 诚实的"尽力而为、可能不完美、可继续"。
    - 若磁盘已被改到打不开：回滚本轮改动，保持可加载；故障局须诚实说「原先问题可能还在」。
    """
    written_unique = list(dict.fromkeys(written))
    code_touched = any(str(p).endswith((".gd", ".tscn")) for p in written_unique)

    dry: dict[str, Any] = {}
    loads_ok = True
    if code_touched:
        dry = dry_run_godot(workspace_root, settings.godot_path, timeout_sec=30.0)
        if dry and not dry.get("skipped") and not dry.get("ok"):
            loads_ok = False

    base_how = [h for h in (last_how or []) if str(h).strip()]
    playability_suspect = bool(bugfix)
    health_errs = assert_player_presence_health(
        workspace_root, genre, written_paths=written_unique
    )
    restored_playable: list[str] = []

    def _try_restore_playable() -> None:
        nonlocal restored_playable, health_errs, playability_suspect
        restored_playable = restore_last_playable_snapshot(workspace_root, genre)
        if restored_playable:
            health_errs = assert_player_presence_health(workspace_root, genre)
            playability_suspect = True

    # 能加载但仍把玩家改坏 → 不交付坏盘，优先恢复 last_playable
    if loads_ok and health_errs and (written_unique or catalog_changed):
        _try_restore_playable()
        if health_errs:
            # 快照也救不了则回滚本轮
            _rollback_snapshot(workspace_root, pre_turn_snapshot)
            health_errs = assert_player_presence_health(workspace_root, genre)
            if health_errs:
                _try_restore_playable()
        summary = (
            "这轮改动会让人物看不见或操控不了，我已经撤回/恢复到上一版还能玩的角色。"
            "请再说一次你想要的效果，我换更安全的改法继续做。"
        )
        trace_done(
            workspace_root,
            round_idx=max(0, rounds_used - 1),
            summary=summary,
            gate_passed=False,
            rolled_back=True,
            written=written_unique,
            enabled=live_trace_enabled(settings),
        )
        return {
            "ok": True,
            "provider": "agent",
            "summary": summary,
            "message": summary,
            "changes": [],
            "sandbox_files": [],
            "how_to_play": [
                "人物应已恢复可见可操控；请重开游戏确认",
                "可继续描述想要的改动，我接着改",
            ],
            "applied_capabilities": [],
            "needs_relaunch": True,
            "verify_gaps": [
                f"玩家健康未过已拦截: {'; '.join(health_errs[:3]) or reason}"
            ],
            "repaired": False,
            "agent_rounds": rounds_used,
            "understanding": last_understanding,
            "goals": plan_goals,
            "progress": progress_events,
            "gate_passed": False,
            "partial": True,
            "playability_suspect": True,
            "restored_playable": restored_playable,
            "intent_route": route,
            "dry_run": dry,
        }

    if loads_ok and (written_unique or catalog_changed):
        # HF-12：gate 未过默认回滚 pending，不交成功 sandbox_files
        rolled = _rollback_snapshot(workspace_root, pre_turn_snapshot)
        health_errs = assert_player_presence_health(workspace_root, genre)
        if health_errs or playability_suspect:
            _try_restore_playable()
        if last_summary.strip():
            summary = last_summary.strip()
            if not re.search(r"可能|再|继续|不满意|如果|尚未|一部分", summary):
                summary += "（这轮尚未验收通过，改动已撤回；请继续说明，我接着改。）"
        else:
            head = last_understanding.strip() or "按你说的尝试改了这局游戏"
            summary = (
                f"{head}。本轮未过门禁，已撤回尝试改动"
                f"（曾尝试：{'、'.join(written_unique[:6]) or '本局配置'}）。"
                "请再补充细节，我继续改。"
            )
        if playability_suspect and not re.search(r"可能还|原先|消失|看不见", summary):
            summary += "若人物/画面仍有问题，直接再说一次，我继续专修。"
        how = base_how or ["请重新启动游戏后确认；可继续对话让我接着改"]
        if not any("重开" in h or "启动" in h or "重新" in h for h in how):
            how.append("重要：重新启动游戏后才能看到最新可玩状态")
        trace_done(
            workspace_root,
            round_idx=max(0, rounds_used - 1),
            summary=summary,
            gate_passed=False,
            rolled_back=bool(rolled),
            written=written_unique,
            enabled=live_trace_enabled(settings),
        )
        return {
            "ok": True,
            "provider": "agent",
            "summary": summary,
            "message": summary,
            "changes": [],
            "sandbox_files": [],
            "attempted_paths": written_unique,
            "how_to_play": how,
            "applied_capabilities": list(route.get("skill_ids") or []),
            "needs_relaunch": True,
            "verify_gaps": [f"未在限定轮次内彻底完成：{reason}"],
            "repaired": False,
            "agent_rounds": rounds_used,
            "understanding": last_understanding,
            "goals": plan_goals,
            "progress": progress_events,
            "gate_passed": False,
            "partial": True,
            "playability_suspect": playability_suspect,
            "rolled_back": rolled,
            "restored_playable": restored_playable,
            "intent_route": route,
            "dry_run": dry,
        }

    # 改动会让游戏打不开 → 回滚保持可加载；仍不上锁
    if not loads_ok:
        rolled = _rollback_snapshot(workspace_root, pre_turn_snapshot)
        health_errs = assert_player_presence_health(workspace_root, genre)
        if health_errs or playability_suspect:
            _try_restore_playable()
        if playability_suspect or restored_playable or health_errs:
            summary = (
                "这次的改法会让游戏打不开，我已经把这次改动撤回"
                + ("，并恢复了上一版还能看见的角色" if restored_playable else "")
                + "。"
                "若人物仍有问题请再说一次，我继续专修（回滚不会自动修好更早埋下的故障，除非已有可玩快照）。"
            )
            how = [
                "请重开游戏看人物是否恢复",
                "原先的问题若还在，直接再说一次即可",
            ]
            gaps = [
                f"本轮改动被回滚（会导致无法加载）：{reason}",
                "playability_suspect：已尽量恢复 last_playable",
            ]
        else:
            summary = (
                "这次的改法会让游戏打不开，我已经把这次改动撤回、游戏还能加载。"
                "你可以再把想要的效果多说一点，我接着试。"
            )
            how = ["游戏保持可加载，可继续试玩；想要的改动可以再说一次"]
            gaps = [f"本轮改动被回滚（会导致无法加载）：{reason}"]
        return {
            "ok": True,
            "provider": "agent",
            "summary": summary,
            "message": summary,
            "changes": [],
            "sandbox_files": [],
            "how_to_play": how,
            "applied_capabilities": [],
            "needs_relaunch": bool(restored_playable),
            "verify_gaps": gaps,
            "repaired": False,
            "agent_rounds": rounds_used,
            "understanding": last_understanding,
            "goals": plan_goals,
            "progress": progress_events,
            "gate_passed": False,
            "partial": True,
            "playability_suspect": playability_suspect or bool(health_errs),
            "rolled_back": rolled,
            "restored_playable": restored_playable,
            "intent_route": route,
            "dry_run": dry,
        }

    # 本轮没有任何改动 → 温和邀请继续读盘写盘（HF-11：禁错品类「脚步」范例）
    if playability_suspect:
        if health_errs:
            _try_restore_playable()
        summary = (
            (last_understanding.strip() + "。" if last_understanding.strip() else "")
            + "这轮还没把问题修好，游戏文件我先没改。"
            + ("（已尝试恢复可玩角色快照）" if restored_playable else "")
            + "请直接再说一次现象，或补充出现时机；我会先读本局改过的文件再改。"
        )
        how = ["问题可能还在；直接再说一次即可，我会继续读盘修复"]
    else:
        summary = (
            (last_understanding.strip() + "。" if last_understanding.strip() else "")
            + "我还在定位怎么改，这轮先没动磁盘。"
            + "请再发一次需求或补充细节；我会先读本局近期改动再写。"
        )
        how = ["游戏保持原样，可继续试玩；再说一次我会继续改"]
    return {
        "ok": True,
        "provider": "agent",
        "summary": summary,
        "message": summary,
        "changes": [],
        "sandbox_files": [],
        "how_to_play": how,
        "applied_capabilities": [],
        "needs_relaunch": bool(restored_playable),
        "verify_gaps": [f"本轮未产出改动：{reason}"],
        "repaired": False,
        "agent_rounds": rounds_used,
        "understanding": last_understanding,
        "goals": plan_goals,
        "progress": progress_events,
        "gate_passed": False,
        "partial": True,
        "playability_suspect": playability_suspect,
        "restored_playable": restored_playable,
        "intent_route": route,
        "dry_run": {},
    }


def run_game_agent(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    user_text: str,
    history: list[dict[str, str]] | None = None,
    feedback: str = "",
    max_rounds: int | None = None,
    *,
    run_dry_run: bool = False,
    previous_turn_user_rating: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行智能体；成功返回 ok/provider=agent。

    轮次耗尽 / 门禁多次未过 / LLM 坏 JSON / 墙钟超时 → **不再抛异常上锁**，而是尽力交付
    （见 `_salvage_agent_return`）；只有无 Key / 网络类错误才向上抛供入口重试。
    """
    if not settings.llm_api_key.strip():
        raise ValueError("无 LLM_API_KEY，无法启动智能体")

    if max_rounds is None:
        max_rounds = max(1, int(getattr(settings, "agent_max_rounds", 16) or 16))
    else:
        max_rounds = max(1, int(max_rounds))
    soft_extra: int = max(0, int(getattr(settings, "agent_soft_extra_rounds", 16) or 0))
    wall_clock_sec: float = float(getattr(settings, "agent_wall_clock_sec", 360.0) or 0.0)
    absolute_max: int = max_rounds + soft_extra
    started_monotonic: float = time.monotonic()

    contract = load_contract(genre)
    progress_events: list[dict[str, Any]] = []
    bugfix = _is_bugfix_turn(user_text, feedback, None)
    emit_progress(workspace_root, "understand", user_text[:80] or "读懂需求")
    progress_events.append({"stage": "understand"})

    route = route_intent(user_text or feedback, contract)
    bugfix = _is_bugfix_turn(user_text, feedback, route)
    playability_critical = _is_playability_critical_turn(user_text, feedback)
    # 开局若玩家健康，先存可玩快照（供后续 salvage 从「已坏可加载」救回）
    save_last_playable_snapshot(workspace_root, genre)

    # 7.19：catalog express 恒关闭；保留调用点但不进入（_can_catalog_express→False）
    if (not bugfix) and _can_catalog_express(route, user_text, feedback):
        try:
            return _run_catalog_express(
                settings, workspace_root, genre, user_text, route, contract
            )
        except ValueError:
            emit_progress(workspace_root, "read_contract", "catalog 快车道未过，改走智能体")

    # HF-12：shmup 掉落物改为 LLM 可调用工具，禁止 pre-LLM return

    route_block = (
        "【意图建议·仅供参考，你可自主决策】\n" + format_route_for_prompt(route)
    )

    genre_ctx = genre_context_as_system_suffix(settings.templates_dir, genre)
    recent_writes_block = format_recent_session_writes_for_prompt(workspace_root)
    # 从近期改动文案提取路径供树置顶
    recent_paths = re.findall(
        r"(?:^|[\s、：:])((?:core|scenes|config)/[A-Za-z0-9_./\-]+\.(?:gd|tscn|json))",
        recent_writes_block or "",
    )
    tree_preview = list_workspace_tree_high_signal(
        workspace_root,
        settings.workspace_dir,
        settings.templates_dir,
        recent_writes=recent_paths,
        max_entries=40,
    )
    diag = diagnose_workspace(workspace_root, genre, contract)
    diag_block = format_diagnose_for_prompt(diag)

    emit_progress(workspace_root, "search_skills", "检索长期库与策展参考")
    learned_hits = search_learned_skills(
        settings.learned_skills_dir,
        user_text or feedback,
        genre,
        k=5,
    )
    learned_block = format_skills_for_prompt(learned_hits)
    reference_block = format_reference_summary_for_prompt(
        settings.reference_skills_dir, genre
    )

    emit_progress(workspace_root, "read_contract", f"品类={genre} · 意图建议={route.get('intent')}")
    progress_events.append({"stage": "read_contract"})

    # 7.19：不再因 Intent A 预开 catalog；一律交 LLM 多工具循环
    written: list[str] = []
    catalog_changed = False
    # 回合前快照：本轮首次改某文件前记录其原内容，兜底回滚（绝不把游戏改到打不开）
    pre_turn_snapshot: dict[str, bytes | None] = {}
    allow_soft_extension = False
    # HF-12：跟踪各文件是否已读到 EOF（整写大文件门禁）
    read_eof_by_path: dict[str, bool] = {}

    # 路由 goals 种子：仅作提示，不预 enable
    plan_goals: list[str] = []
    if route.get("intent") == "C" and route.get("skill_ids"):
        # 条件需求：catalog 仅材料，goals 强调条件本身
        plan_goals = [
            str(route.get("hint") or "按用户条件实现机制")[:100]
        ]
        for sid in (route.get("skill_ids") or [])[:3]:
            plan_goals.append(f"可参考 catalog 材料:{sid}")
    elif route.get("intent") == "A" and route.get("skill_ids"):
        plan_goals = [
            f"实现目标能力（可参考 catalog:{sid}）"
            for sid in route.get("skill_ids") or []
        ][:5]
    elif str(route.get("hint") or "").strip():
        plan_goals = [str(route.get("hint")).strip()[:80]]

    # HF-12：路由 actions 只作为 LLM 材料，不在首轮 LLM 前预执行任何写盘动作。

    if route.get("stop"):
        # 不硬劝退：幻想 API 请求改为「用会话 GDScript 实现同等效果」，继续跑 LLM
        emit_progress(workspace_root, "read_contract", "幻想 API → 改会话自由实现")
        route = {
            **route,
            "stop": False,
            "advisory": True,
            "intent": "C",
            "hint": (
                str(route.get("hint") or "")
                + "；请在会话 core/scenes 用 GDScript 实现用户想要的效果"
            ).strip("；"),
        }
        route_block = format_route_for_prompt(route)

    # 预执行补丁后刷新诊断
    diag = diagnose_workspace(workspace_root, genre, contract)
    diag_block = format_diagnose_for_prompt(diag)

    # 聊天式组装：历史轮次 + 本轮原话置顶；施工上下文放附录
    turn_text = user_text.strip()
    if feedback.strip() and feedback.strip() != turn_text:
        turn_text = f"{turn_text}\n（补充：{feedback.strip()}）"
    context_bits: list[str] = [
        "---",
        "施工上下文（非用户原话，供改游戏用）",
        f"品类: {genre}",
        diag_block,
        route_block,
        "当前会话文件（部分）:",
        *[f"- {p}" for p in tree_preview],
        catalog_for_prompt(genre, contract),
    ]
    if learned_block:
        context_bits.append(learned_block)
    if reference_block:
        context_bits.append(reference_block)
    if recent_writes_block:
        context_bits.append(recent_writes_block)
    # HF-11：统一开放读盘；可玩性危急 / shmup 掉落仅门控附加正向提示
    if bugfix or recent_writes_block:
        context_bits.append(_OPEN_READ_WORK_TIP)
    if bugfix:
        context_bits.append(_BUGFIX_REREAD_TIP)
    blob_for_tips = f"{user_text or ''}\n{feedback or ''}"
    if _TIME_CYCLE_HINTS.search(blob_for_tips):
        context_bits.append(_TIME_CYCLE_WORK_TIP)
    if _PRESENTATION_HINTS.search(blob_for_tips):
        context_bits.append(_PRESENTATION_WORK_TIP)
    if playability_critical:
        context_bits.append(_PLAYABILITY_WORK_TIP)
    if genre == "shmup" and is_laser_bomb_drop_request(user_text or feedback):
        context_bits.append(_SHMUP_DROP_LOOT_TIP)
    if len(plan_goals) >= 4:
        context_bits.append(_MULTI_GOALS_WORK_TIP)
    # HF-14：反馈轮注入上轮 summary / evidence（若有）
    prev_log_rows = read_session_patch_log(workspace_root)
    prev_summary_for_feedback = ""
    if prev_log_rows:
        last_ok = next(
            (r for r in reversed(prev_log_rows) if r.get("ok")),
            prev_log_rows[-1],
        )
        prev_summary_for_feedback = str(last_ok.get("summary") or "").strip()
        prev_ev = last_ok.get("evidence")
        if bugfix and (prev_summary_for_feedback or prev_ev):
            context_bits.append(
                "【上轮交付·系统注入·对照读盘】\n"
                + json.dumps(
                    {
                        "previous_summary": prev_summary_for_feedback[:240],
                        "previous_sandbox_files": list(last_ok.get("sandbox_files") or [])[:12],
                        "previous_evidence": normalize_evidence_list(prev_ev)[:8],
                    },
                    ensure_ascii=False,
                )
                + "\n本轮反馈「没生效」时：先 read 上述路径，核对 wiring 与数值，"
                "用 replace_text 补齐后 done，并附新 evidence（相对上轮须有代码 diff）。"
            )
    if previous_turn_user_rating:
        # F3：结构化注入，非用户原话；低星优先澄清不满点
        rating_json = json.dumps(
            {"previous_turn_user_rating": previous_turn_user_rating},
            ensure_ascii=False,
        )
        context_bits.append(
            "【上轮用户星级评价·系统注入·按结构化字段处理】\n"
            + rating_json
            + "\n"
            "若 score≤2：优先澄清不满点并复读盘再改；"
            "若 score≥4：可在摘要中简短确认方向后继续。"
        )
    context_bits.append(
        "请先给出 understanding + goals，再读盘施工；"
        "一条话里的多个要求都要进 goals 并尽量落地。"
        "带条件的需求用会话逻辑实现条件；"
        "done.summary 用自然中文覆盖各 goals；"
        "done 附带 evidence[]（path/symbol/wired_by）。"
    )
    user_blob = turn_text + "\n\n" + "\n".join(context_bits)

    # HF-12：system 只放稳定工作法 + 品类摘要；Reference/Learned 仅进 user。
    system_content = _AGENT_SYSTEM + "\n\n" + genre_ctx

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
    ]
    for turn in (history or [])[-10:]:
        role = str(turn.get("role", ""))
        content = str(turn.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:1200]})
    messages.append({"role": "user", "content": user_blob})

    summary = ""
    how_to_play: list[str] = []
    last_thought = ""
    last_understanding = ""
    # plan_goals 可能已由路由种子；勿清空
    learned_skill_ids_used: list[str] = [
        str(h.get("skill_id")) for h in learned_hits if h.get("skill_id")
    ]
    searched_ids: list[str] = []
    gate_failures = 0
    dry_run_result: dict[str, Any] | None = None
    last_error_sig = ""
    error_sig_streak = 0
    last_gate_error_keys: frozenset[str] = frozenset()
    gate_error_streak = 0

    for _round in range(absolute_max):
        # 软续杯：越过首段 max_rounds 前须已有写盘进展
        if _round >= max_rounds:
            if soft_extra <= 0 or not allow_soft_extension:
                break
            if _round == max_rounds:
                emit_progress(
                    workspace_root,
                    "write_changes",
                    f"首段 {max_rounds} 轮有进展，软续杯 +{soft_extra} 轮继续完成…",
                )
        if wall_clock_sec > 0 and (time.monotonic() - started_monotonic) >= wall_clock_sec:
            return _salvage_agent_return(
                settings,
                workspace_root,
                genre,
                route=route,
                written=written,
                catalog_changed=catalog_changed,
                pre_turn_snapshot=pre_turn_snapshot,
                last_summary=summary,
                last_how=how_to_play,
                last_understanding=last_understanding,
                plan_goals=plan_goals,
                progress_events=progress_events,
                rounds_used=_round + 1,
                reason=f"墙钟超时（{int(wall_clock_sec)}s），已尽量保留可玩进度",
                bugfix=bugfix,
            )
        budget_label = absolute_max if allow_soft_extension else max_rounds
        emit_progress(
            workspace_root,
            "write_changes" if _round > 0 else "read_contract",
            f"智能体第 {_round + 1}/{budget_label} 轮思考中…",
        )
        _trace_on = live_trace_enabled(settings)
        try:
            parsed = _llm_turn(settings, messages)
            trace_llm_round(
                workspace_root,
                round_idx=_round,
                messages=messages,
                parsed=parsed,
                enabled=_trace_on,
            )
        except (requests.RequestException, TimeoutError):
            # 网络类交给入口重试
            raise
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
            # 坏 JSON / 缺字段：不上锁，回灌后继续；末轮走 salvage
            err = str(exc).strip()[:240]
            trace_llm_round(
                workspace_root,
                round_idx=_round,
                messages=messages,
                parsed=None,
                error=err,
                enabled=_trace_on,
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"上一轮回复无法解析（{err}）。请只返回合法 JSON 对象，"
                        "含 understanding、goals、actions。"
                    ),
                }
            )
            last_budget = absolute_max if allow_soft_extension else max_rounds
            if _round >= max(1, last_budget) - 1:
                return _salvage_agent_return(
                    settings,
                    workspace_root,
                    genre,
                    route=route,
                    written=written,
                    catalog_changed=catalog_changed,
                    pre_turn_snapshot=pre_turn_snapshot,
                    last_summary=summary,
                    last_how=how_to_play,
                    last_understanding=last_understanding,
                    plan_goals=plan_goals,
                    progress_events=progress_events,
                    rounds_used=_round + 1,
                    reason=f"LLM 回复无法解析: {err}",
                    bugfix=bugfix,
                )
            continue
        last_thought = str(parsed.get("thought", "")).strip()
        understanding = str(parsed.get("understanding", "") or "").strip()
        if understanding:
            last_understanding = understanding
        raw_goals = parsed.get("goals")
        if isinstance(raw_goals, list) and raw_goals:
            plan_goals = [str(g).strip() for g in raw_goals if str(g).strip()][:5]
            emit_progress(
                workspace_root,
                "understand",
                "拆解：" + "；".join(plan_goals[:3]),
            )
        actions = parsed.get("actions")
        if not isinstance(actions, list) or not actions:
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(parsed, ensure_ascii=False)[:4000],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": "缺少 actions 数组。请给出可执行的 actions（含工具调用或 done）。",
                }
            )
            continue

        # 首轮或尚未拆解：要求先产出 goals，避免跳过理解直接乱写
        has_mutate = any(
            isinstance(a, dict)
            and str(a.get("tool", ""))
            in (
                "write_file",
                "replace_text",
                "apply_shmup_drop_loot_chain",
                "ensure_player_visibility",
                "enable_catalog_skill",
                "done",
            )
            for a in actions
        )
        if has_mutate and not plan_goals:
            messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)[:4000]})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "请先拆解：返回 understanding（一句话）和 goals（1～5条可验收子目标），"
                        "再给出对应施工 actions。本轮用户原话："
                        + user_text.strip()[:300]
                    ),
                }
            )
            continue

        route_errs = enforce_route_on_actions(
            route, [a for a in actions if isinstance(a, dict)]
        )
        observations: list[dict[str, Any]] = []
        if route_errs:
            observations.append(
                {
                    "tool": "intent_route",
                    "advice": "路由建议（非硬挡）",
                    "notes": route_errs,
                }
            )

        pending_done: dict[str, Any] | None = None
        round_self_check_ok: bool | None = None
        round_self_check_errors: list[str] = []

        for raw in _schedule_actions_for_round(actions, max_total=10):
            if not isinstance(raw, dict):
                continue
            tool_name = str(raw.get("tool", "")).strip()
            if tool_name == "done":
                pending_done = raw
                continue
            if tool_name in (
                "write_file",
                "replace_text",
                "apply_shmup_drop_loot_chain",
                "ensure_player_visibility",
            ):
                emit_progress(
                    workspace_root,
                    "write_changes",
                    str(raw.get("path", "") or tool_name)[:60],
                )
            # 改文件前先快照原内容（本轮首次），供兜底回滚
            _snap_targets: list[str] = []
            if tool_name in ("write_file", "replace_text"):
                _p = str(raw.get("path", "")).strip().replace("\\", "/")
                if _p:
                    _snap_targets.append(_p)
            elif tool_name == "apply_shmup_drop_loot_chain":
                _snap_targets.extend(
                    ["config/game_config.json", "core/player_ship.gd", "core/ai_sandbox_bridge.gd"]
                )
            elif tool_name == "ensure_player_visibility":
                _pcfg = PLAYER_PRESENCE_BY_GENRE.get(genre) or {}
                for _key in ("script", "scene"):
                    _rel = str(_pcfg.get(_key) or "").replace("\\", "/")
                    if _rel:
                        _snap_targets.append(_rel)
            elif tool_name == "enable_catalog_skill":
                _snap_targets.append("config/game_config.json")
            elif tool_name == "patch_mouse_steer_guard":
                _snap_targets.append("core/player_ship.gd")
            elif tool_name in ("refresh_ai_sandbox_bridge", "ensure_touch_skill_buttons"):
                _snap_targets.append("core/ai_sandbox_bridge.gd")
            action_snapshot: dict[str, bytes | None] = {}
            for _st in _snap_targets:
                _sp = workspace_root / _st
                try:
                    action_snapshot[_st] = _sp.read_bytes() if _sp.is_file() else None
                except OSError:
                    action_snapshot[_st] = None
                if _st not in pre_turn_snapshot:
                    pre_turn_snapshot[_st] = action_snapshot[_st]
            try:
                obs = _run_action(
                    settings,
                    workspace_root,
                    genre,
                    raw,
                    contract,
                    progress_events,
                    written_paths=written,
                    catalog_changed=catalog_changed,
                    user_text=user_text,
                    read_eof_by_path=read_eof_by_path,
                    plan_goals=plan_goals,
                    pre_turn_snapshot=pre_turn_snapshot,
                )
            except (AgentWorkspaceError, OSError, ValueError) as exc:
                obs = {"tool": raw.get("tool"), "error": str(exc)}

            if obs.get("tool") == "self_check":
                round_self_check_ok = bool(obs.get("ok"))
                round_self_check_errors = list(obs.get("errors") or [])

            # HF-12：每次代码 mutation 后立即跑 Godot；失败则恢复本动作前版本。
            action_written: list[str] = []
            if not obs.get("error"):
                if obs.get("tool") in ("write_file", "replace_text") and obs.get("path"):
                    action_written.append(str(obs["path"]))
                elif obs.get("tool") in (
                    "apply_shmup_drop_loot_chain",
                    "ensure_player_visibility",
                ):
                    action_written.extend(str(p) for p in (obs.get("written") or []))
                elif obs.get("tool") in (
                    "patch_mouse_steer_guard",
                    "refresh_ai_sandbox_bridge",
                    "ensure_touch_skill_buttons",
                ):
                    path_w = str(obs.get("path") or "")
                    if path_w:
                        action_written.append(path_w)
                    elif obs.get("refreshed_bridge"):
                        action_written.append("core/ai_sandbox_bridge.gd")
            action_code_touched = any(
                p.replace("\\", "/").endswith((".gd", ".tscn"))
                for p in action_written
            )
            if action_code_touched:
                action_dry = dry_run_godot(
                    workspace_root, settings.godot_path, timeout_sec=30.0
                )
                if (
                    action_dry
                    and not action_dry.get("skipped")
                    and not action_dry.get("ok")
                ):
                    rolled = _rollback_snapshot(workspace_root, action_snapshot)
                    obs = {
                        "tool": raw.get("tool"),
                        "error": (
                            "动作后 Godot 校验尚未通过；已恢复本动作前版本："
                            + "; ".join(
                                str(e)
                                for e in (
                                    action_dry.get("errors")
                                    or ["headless 校验失败"]
                                )[:4]
                            )
                        ),
                        "attempted_paths": action_written,
                        "rolled_back": rolled,
                        "dry_run": action_dry,
                    }
                else:
                    obs["dry_run"] = action_dry
            observations.append(obs)
            if obs.get("tool") in ("write_file", "replace_text") and obs.get("path") and not obs.get("error"):
                written.append(str(obs["path"]))
                allow_soft_extension = True
            if (
                obs.get("tool") in ("apply_shmup_drop_loot_chain", "ensure_player_visibility")
                and obs.get("ok")
                and not obs.get("error")
            ):
                for wp in obs.get("written") or []:
                    written.append(str(wp))
                allow_soft_extension = True
            if obs.get("tool") == "enable_catalog_skill" and not obs.get("error"):
                written.append("config/game_config.json")
                catalog_changed = True
                allow_soft_extension = True
            if obs.get("tool") in (
                "patch_mouse_steer_guard",
                "refresh_ai_sandbox_bridge",
                "ensure_touch_skill_buttons",
            ) and obs.get("ok"):
                path_w = str(obs.get("path") or "")
                if path_w:
                    written.append(path_w)
                    allow_soft_extension = True
                elif obs.get("refreshed_bridge"):
                    written.append("core/ai_sandbox_bridge.gd")
                    allow_soft_extension = True
            if obs.get("tool") == "search_learned_skills":
                for hit in obs.get("hits") or []:
                    sid = str(hit.get("skill_id") or "")
                    if sid and sid not in searched_ids:
                        searched_ids.append(sid)

        trace_tools(
            workspace_root,
            round_idx=_round,
            observations=observations,
            enabled=_trace_on,
        )

        if pending_done is not None:
            emit_progress(workspace_root, "validate", "校验脚本与声称")
            summary = str(pending_done.get("summary") or last_thought or "已按你的话改好游戏")
            how_to_play = [
                str(x) for x in (pending_done.get("how_to_play") or []) if str(x).strip()
            ][:6]
            if not how_to_play:
                how_to_play = ["请重新启动游戏后再试玩刚才的改动"]
            elif not any("重开" in h or "启动" in h or "重新" in h for h in how_to_play):
                how_to_play.append("重要：重新启动游戏后新改动才会生效")
            evidence = normalize_evidence_list(pending_done.get("evidence"))
            code_written = any(
                str(p).replace("\\", "/").endswith(".gd") for p in written
            )
            require_evidence = bool(code_written)

            # 7.19：done 前不再强制 enable catalog；由 LLM actions 显式决定
            gate_errors = list(
                run_done_gates(
                    workspace_root,
                    written_paths=list(dict.fromkeys(written)),
                    summary=summary,
                    how_to_play=how_to_play,
                    genre=genre,
                    contract=contract,
                    catalog_changed=catalog_changed,
                    user_text=user_text,
                    evidence=evidence,
                    require_evidence=require_evidence,
                    goals=plan_goals,
                    pre_turn_snapshot=pre_turn_snapshot,
                )
            )
            # HF-15.1 H5：同轮 self_check 未过则 done 不得假装过关
            if round_self_check_ok is False and round_self_check_errors:
                gate_errors = list(
                    dict.fromkeys(round_self_check_errors + gate_errors)
                )
            # HF-14 S3：反馈轮无真 diff / summary 近亲复读 → 硬回灌
            if bugfix:
                gate_errors.extend(
                    assert_feedback_has_real_diff(
                        workspace_root,
                        written_paths=list(dict.fromkeys(written)),
                        pre_turn_snapshot=pre_turn_snapshot,
                        summary=summary,
                        previous_summary=prev_summary_for_feedback,
                    )
                )
            # 多 goals 时：summary 不能近乎为空（防只完成一条就空话交差）。
            # 仅在 summary 过短时才拦——避免对合法长 summary 的 token 命中误伤，浪费自愈轮次。
            # 声称是否⊆磁盘由 assert_claims + dry_run 严格把关，这里只挡"空 done"。
            if len(plan_goals) >= 2 and len(summary.strip()) < 20:
                gate_errors.append(
                    "summary 过于简短：请说明本轮各 goals 各自做了什么（覆盖："
                    + "；".join(plan_goals[:3])
                    + "）"
                )

            # 改了会话 .gd/.tscn（新机制/新场景）→ 强制 headless 冒烟，把 parse/script
            # error 回灌给 LLM 自愈；仅改 config/enabled_skills 的快改不必每次拉起 Godot。
            code_touched = any(
                str(p).endswith((".gd", ".tscn")) for p in written
            )
            if (run_dry_run or code_touched) and not gate_errors and written:
                dry_run_result = dry_run_godot(
                    workspace_root, settings.godot_path, timeout_sec=30.0
                )
                if (
                    dry_run_result
                    and not dry_run_result.get("skipped")
                    and not dry_run_result.get("ok")
                ):
                    gate_errors.extend(
                        [f"dry_run: {e}" for e in dry_run_result.get("errors") or ["headless 失败"]]
                    )

            if gate_errors:
                gate_failures += 1
                gate_error_streak, last_gate_error_keys = update_gate_error_streak(
                    gate_error_streak,
                    last_gate_error_keys,
                    gate_errors,
                )
                trace_gate(
                    workspace_root,
                    round_idx=_round,
                    gate_errors=gate_errors,
                    evidence=evidence,
                    enabled=_trace_on,
                )
                observations.append(
                    {
                        "tool": "done",
                        "error": "完成条件尚未齐备，请按 gate_errors 继续施工",
                        "gate_errors": gate_errors,
                        "evidence": evidence,
                    }
                )
                tool_report = serialize_observations_for_followup(
                    observations,
                    total_budget=12000,
                    per_item_budget=5000,
                )
                messages.append(
                    {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)}
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "本轮工具结果：\n"
                            + tool_report
                            + "\n完成条件尚未齐备，请按下列说明继续施工：\n"
                            + json.dumps(gate_errors, ensure_ascii=False)
                            + (
                                "\n本轮 goals：" + "；".join(plan_goals)
                                if plan_goals
                                else ""
                            )
                            + "\n请读取相关脚本（尤其近期改过的路径），"
                            "用 replace_text 最小 patch 完成目标，"
                            "done 须带可核对的 evidence[]（path/symbol/wired_by）后再提交。"
                        ),
                    }
                )
                if gate_error_streak >= 3:
                    return _salvage_agent_return(
                        settings,
                        workspace_root,
                        genre,
                        route=route,
                        written=written,
                        catalog_changed=catalog_changed,
                        pre_turn_snapshot=pre_turn_snapshot,
                        last_summary=summary,
                        last_how=how_to_play,
                        last_understanding=last_understanding,
                        plan_goals=plan_goals,
                        progress_events=progress_events,
                        rounds_used=_round + 1,
                        reason=(
                            "连续三次相同门禁失败，已停止空转: "
                            + "; ".join(gate_errors[:4])
                        ),
                        bugfix=bugfix,
                    )
                if gate_failures >= 6:
                    # 不上锁：尽力交付本轮已改内容（能加载就给，坏了就回滚保可加载）
                    return _salvage_agent_return(
                        settings,
                        workspace_root,
                        genre,
                        route=route,
                        written=written,
                        catalog_changed=catalog_changed,
                        pre_turn_snapshot=pre_turn_snapshot,
                        last_summary=summary,
                        last_how=how_to_play,
                        last_understanding=last_understanding,
                        plan_goals=plan_goals,
                        progress_events=progress_events,
                        rounds_used=_round + 1,
                        reason="门禁多次未通过: " + "; ".join(gate_errors[:4]),
                        bugfix=bugfix,
                    )
                continue

            # 门禁通过
            gate_error_streak = 0
            last_gate_error_keys = frozenset()
            emit_progress(workspace_root, "done", summary[:80])
            used_ids = list(dict.fromkeys(learned_skill_ids_used + searched_ids))
            if used_ids:
                bump_skill_counts(
                    settings.learned_skills_dir,
                    used_ids,
                    used=True,
                    success=True,
                    failed=False,
                )
            save_last_playable_snapshot(workspace_root, genre)
            trace_done(
                workspace_root,
                round_idx=_round,
                summary=summary,
                gate_passed=True,
                rolled_back=False,
                written=list(dict.fromkeys(written)),
                evidence=evidence,
                enabled=_trace_on,
            )
            return {
                "ok": True,
                "provider": "agent",
                "summary": summary,
                "message": summary,
                "changes": [],
                "sandbox_files": list(dict.fromkeys(written)),
                "how_to_play": how_to_play,
                "evidence": evidence,
                "applied_capabilities": list(route.get("skill_ids") or []),
                "needs_relaunch": True,
                "verify_gaps": [],
                "repaired": False,
                "agent_rounds": _round + 1,
                "agent_thought": last_thought,
                "understanding": last_understanding,
                "goals": plan_goals,
                "learned_skills": used_ids,
                "progress": progress_events,
                "gate_passed": True,
                "intent_route": route,
                "dry_run": dry_run_result or {},
            }

        elif round_self_check_ok is False and round_self_check_errors:
            gate_error_streak, last_gate_error_keys = update_gate_error_streak(
                gate_error_streak,
                last_gate_error_keys,
                round_self_check_errors,
            )
            if gate_error_streak >= 3:
                return _salvage_agent_return(
                    settings,
                    workspace_root,
                    genre,
                    route=route,
                    written=written,
                    catalog_changed=catalog_changed,
                    pre_turn_snapshot=pre_turn_snapshot,
                    last_summary=summary or last_thought,
                    last_how=how_to_play or ["请重新启动游戏后再试玩"],
                    last_understanding=last_understanding,
                    plan_goals=plan_goals,
                    progress_events=progress_events,
                    rounds_used=_round + 1,
                    reason=(
                        "连续三次相同门禁失败，已停止空转: "
                        + "; ".join(round_self_check_errors[:4])
                    ),
                    bugfix=bugfix,
                )

        follow = (
            "工具结果:\n"
            + serialize_observations_for_followup(observations)
        )
        if plan_goals:
            follow += "\n本轮 goals：" + "；".join(plan_goals) + "（未完成的请继续）"
        # 未读完的文件提醒 continuation
        pending_reads = [
            f"{p}(next_offset 续读)"
            for p, eof in read_eof_by_path.items()
            if eof is False
        ]
        if pending_reads:
            follow += (
                "\n尚未读到 EOF 的文件："
                + "、".join(pending_reads[:6])
                + "；改这些大文件请用 replace_text 或先续读到 eof。"
            )
        # HF-12 Live：可玩性危急局读盘空转 → 催写盘；优先确定性工具
        if playability_critical and not written and not catalog_changed:
            follow += (
                "\n【可玩性催写】已读盘但尚未写入。"
                "请立刻调用 ensure_player_visibility（一次加固玩家可见性），"
                "然后 self_check → done；"
                "也可手写 replace_text。done 须有真实写入。"
            )
        # 掉落探针：读盘空转时催专用工具（与 ensure 同级，非 Intent 特例堆叠）
        if (
            genre == "shmup"
            and is_laser_bomb_drop_request(user_text or feedback)
            and not written
            and not catalog_changed
        ):
            follow += (
                "\n【掉落催写】已读盘但尚未写入。"
                "请立刻调用 apply_shmup_drop_loot_chain，"
                "然后 self_check → done。"
            )
        # 通用：多轮仍无落盘 → 催 replace（换行已自动对齐，hash 可省略）
        mutate_failed = any(
            isinstance(o, dict)
            and o.get("error")
            and str(o.get("tool") or "") in ("replace_text", "write_file")
            for o in observations
        )
        if (
            not written
            and not catalog_changed
            and _round >= 2
            and (mutate_failed or _round >= 4)
        ):
            follow += (
                "\n【施工催写】尚未成功写入磁盘。"
                "请立刻 replace_text：old_text 从最近 read/search 原文复制（可省略 expected_sha256）；"
                "系统会自动对齐 CRLF/LF。成功写入后再 self_check → done。"
            )
        # HF-13：同错连击 → 换路（禁重复 write_file 同一坏场景）
        err_bits = [
            f"{o.get('tool')}:{str(o.get('error'))[:100]}"
            for o in observations
            if isinstance(o, dict) and o.get("error")
        ]
        err_sig = "|".join(err_bits)
        if err_sig:
            if err_sig == last_error_sig:
                error_sig_streak += 1
            else:
                last_error_sig = err_sig
                error_sig_streak = 1
        elif any(
            isinstance(o, dict)
            and o.get("tool") in ("replace_text", "write_file")
            and o.get("path")
            and not o.get("error")
            for o in observations
        ):
            last_error_sig = ""
            error_sig_streak = 0
        if error_sig_streak >= 3:
            follow += (
                "\n【换路催写】连续多轮同一写入/校验错误未消除，请换策略："
                "1) read_file 失败路径后用 replace_text 修具体报错行"
                "（Godot 4 矩形碰撞用 size；[sub_resource] 先于 SubResource 引用）；"
                "2) 新机制优先脚本 new Area2D()/add_child；"
                "3) 同一文件优先 replace_text 做最小 patch。"
            )
        follow += "\n请继续；改完后 actions 含 done（须过门禁）。"
        messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
        messages.append({"role": "user", "content": follow})

    # 轮次耗尽仍无 done：不上锁，尽力交付本轮已改内容
    return _salvage_agent_return(
        settings,
        workspace_root,
        genre,
        route=route,
        written=written,
        catalog_changed=catalog_changed,
        pre_turn_snapshot=pre_turn_snapshot,
        last_summary=summary,
        last_how=how_to_play,
        last_understanding=last_understanding,
        plan_goals=plan_goals,
        progress_events=progress_events,
        rounds_used=max(1, absolute_max if allow_soft_extension else max_rounds),
        reason="未在限定轮次内完成",
        bugfix=bugfix,
    )
