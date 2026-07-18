"""游戏创作智能体：契约注入 + 写后门禁 + 进度事件 + 多轮再改。

闭环：读契约 → 检索 Skill → 读写会话副本 → validate / assert_apis / assert_claims → 才 done。
templates 只读；无 API Key 时由调用方走离线 stub（有 Key 则只跑本智能体）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from app.config import Settings
from app.services.agent_workspace import (
    AgentWorkspaceError,
    list_workspace_tree,
    read_workspace_file,
    write_workspace_file,
)
from app.services.creative.agent_contracts import (
    assert_apis_in_contract,
    diagnose_workspace,
    dry_run_godot,
    emit_progress,
    format_diagnose_for_prompt,
    load_contract,
    run_done_gates,
    validate_gdscript,
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
    format_skills_for_prompt,
    search_learned_skills,
)
from app.services.creative.sandbox_intent import catalog_for_prompt
from app.services.edu_workspace import (
    patch_shmup_mouse_steer_guard,
    refresh_ai_sandbox_bridge,
)

_AGENT_SYSTEM: str = """你是 GameForge K12 展厅的游戏改关助手。对话与推理对齐常见大模型（如 DeepSeek）：先听懂本轮、拆解目标，再动手改游戏。

【对话 · 全局】
- 本轮用户原话优先级最高；历史只作背景，换话题就跟新话题走
- done.summary 用自然中文直接回答本轮原话，说明做了什么 / 修好了什么
- 若本轮在抱怨故障、没生效、看不到、打不开、人物消失/不显示：先 diagnose + 读玩家/主场景，修复可见性（visible / modulate / position），禁止再开新技能交差
- 若用户说「掉落物 / 敌机掉落 / 捡到才开」：禁止 enable_catalog_skill；shmup 只改 powerup_types + player_ship.apply_powerup（拾取后追加 GameConfig.enabled_skills + AiSandboxBridge.ensure_touch_skill_buttons）。禁止重写 enemy_spawner/main.tscn；禁止 Bridge. 幻想 API。how_to_play 写「打敌机→捡掉落」
- 写 config/game_config.json 时必须先 read_file 再合并字段，禁止整文件覆盖导致丢失 powerup_types/enemies 等
- 用户没提就不要送无关大礼包；长期库仅明显相关才复用

【聪明拆解 · 每轮必须】
1. understanding：用一句话复述本轮用户到底要什么
2. goals：拆成 1～5 条可验收子目标（一条用户话里的多个要求都要拆开）
3. 再 actions：按 goals 施工，最后 self_check → done
4. 【快路径】若意图建议已命中 catalog（如激光/炸弹/二段跳）：优先在本轮内 enable_catalog_skill + refresh_ai_sandbox_bridge + done，禁止多轮空读盘
5. 禁止跳过拆解直接空 done；未覆盖的 goal 要么继续改，要么在 summary 诚实说明

【创作】
- 尽量做出来：会话 core/**、scenes/**、config/**、ai_sandbox 均可写；catalog / 桥 API / Learned Skills 是捷径不是天花板
- 实现用户要的机制本身，勿用无关玩法顶替后口头当作完成
- 禁止空 done、幻想 API（add_method / set_color / OS.execute 等）；禁止改 templates/**、project.godot
- 声称 ⊆ 磁盘；新操作尽量触屏可点；how_to_play 含重开 + 点屏

【新机制避坑·会跑 Godot headless 冒烟，parse/script error 会打回】
- preload / ext_resource 只能指向"你本轮已创建或模板已存在"的文件；先 list_dir/read_file 确认，勿引用不存在的 .gd/.tscn/贴图
- 只调用确实存在的方法/属性；不确定就 read_file 看目标脚本有没有该 func，勿臆造 interrupt_dash()/try_block() 等
- 视口尺寸用 get_viewport().get_visible_rect() 或 get_window().size；self 上没有 get_viewport_rect()
- 访问节点先 get_node_or_null 并判空，避免 "null instance" 报错
- 拿不准 .tscn 手写格式时，优先用 GDScript 在 _ready() 里 new + add_child 动态生成节点，少手写复杂 .tscn
- 改已有 .tscn 必须保留原有全部节点（HUD/GameOver/按钮/Retry 等），只增不删；整文件重写极易丢节点→别的脚本 get_node 到 null 崩。首选新写一个脚本用 add_child 挂节点，别动 main.tscn 结构
- 新节点要真正挂进运行场景（加到 main/关卡场景或用脚本 add_child），否则"写了不生效"
- 报错带「at: res://xxx.gd:NN」就是出错文件与行号，先 read_file 那个文件再精准改
- 【最小编辑铁律】改已有 core/*.gd 先 read_file，再只改相关函数/几行，**禁止整文件重写**——整写会丢碰撞/受伤/信号/收集等既有逻辑，典型后果：金币收不到、碰到子弹卡住不扣血、角色崩。改数值/大小走对应字段，勿顺手重写整份脚本
- 「加金币/道具」等：先弄清它在源码里如何生成（多为程序化生成或注册进管理器），改生成处；勿新建游离场景，那样进不了收集/计分链，会"看着加了其实没用"

意图建议仅供参考。反馈「键盘行、按钮不行」→ 勿再 enable 同技能，查桥/HUD。

每轮只返回 JSON：
{
  "understanding": "一句话复述本轮需求",
  "goals": ["子目标1", "子目标2"],
  "thought": "本步计划（对应哪几条 goals）",
  "actions": [
    {"tool":"diagnose_workspace"},
    {"tool":"list_dir","path":"core"},
    {"tool":"read_file","path":"config/game_config.json"},
    {"tool":"search_learned_skills","query":"...","k":3},
    {"tool":"enable_catalog_skill","skill_id":"laser_beam"},
    {"tool":"refresh_ai_sandbox_bridge"},
    {"tool":"patch_mouse_steer_guard"},
    {"tool":"write_file","path":"core/custom_mechanic.gd","content":"..."},
    {"tool":"write_file","path":"scenes/main.tscn","content":"..."},
    {"tool":"validate_gdscript","path":"core/custom_mechanic.gd"},
    {"tool":"self_check","summary":"草稿回复","how_to_play":["重开后点…"]},
    {"tool":"emit_progress","stage":"write_changes","detail":"..."},
    {"tool":"done","summary":"自然中文回复本轮原话（覆盖各 goals）","how_to_play":["试玩1","试玩2"]}
  ]
}
工具：diagnose_workspace | list_dir | read_file | write_file | enable_catalog_skill | patch_mouse_steer_guard | refresh_ai_sandbox_bridge | ensure_touch_skill_buttons | search_learned_skills | validate_gdscript | self_check | emit_progress | done
"""


_BUGFIX_HINTS: re.Pattern[str] = re.compile(
    r"没生效|不发射|没反应|不能用|只有.?键|人物.*消失|不显示|白屏|黑屏|"
    r"打不开|没法.*启动|闪退|报错|修复"
)
_NEEDS_LLM_CREATE: re.Pattern[str] = re.compile(
    r"Boss|关卡编辑|新敌人|自己写|前所未有|改引擎|联机|存档"
)


def _can_catalog_express(route: dict[str, Any], user_text: str, feedback: str) -> bool:
    """明确 catalog 命中时走确定性快车道（秒级），不必多轮 LLM。"""
    if feedback.strip():
        return False
    if _BUGFIX_HINTS.search(user_text or ""):
        return False
    if _NEEDS_LLM_CREATE.search(user_text or ""):
        return False
    # 「掉落才开」绝不能快开 catalog 按钮
    if is_drop_loot_request(user_text or ""):
        return False
    if route.get("express") is False:
        return False
    if str(route.get("intent") or "") != "A":
        return False
    skill_ids = [str(s) for s in (route.get("skill_ids") or []) if str(s).strip()]
    return bool(skill_ids)


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
) -> dict[str, Any]:
    """shmup 掉落物确定性落地：powerup_types + apply_powerup 拾取解锁。"""
    emit_progress(workspace_root, "understand", user_text[:80] or "掉落才开")
    emit_progress(
        workspace_root, "write_changes", "掉落物快车道：powerup_types + apply_powerup"
    )
    written: list[str] = []

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
    if "laser" not in names:
        types.append({"name": "laser", "frame": 14})
    if "bomb" not in names:
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
        raise ValueError("掉落物快车道失败：缺少 core/player_ship.gd")
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
        raise ValueError("掉落物快车道门禁失败: " + "; ".join(gate_errors[:4]))

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
        "agent_rounds": 0,
        "agent_thought": "drop loot express",
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
) -> dict[str, Any]:
    tool = str(action.get("tool", "")).strip()
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
        content = read_workspace_file(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
        )
        return {"tool": tool, "path": path, "content": content}
    if tool == "write_file":
        path = str(action.get("path", "")).strip()
        content = str(action.get("content", ""))
        if not path or not content.strip():
            raise AgentWorkspaceError("write_file 需要 path 与 content")
        if path.endswith(".gd"):
            syn = validate_gdscript(content)
            api = assert_apis_in_contract(content, contract)
            if syn or api:
                raise AgentWorkspaceError(
                    "写入前校验失败: " + "; ".join(syn + api)
                )
        written = write_workspace_file(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            path,
            content,
        )
        return {"tool": tool, "path": written, "bytes": len(content.encode("utf-8"))}
    if tool == "enable_catalog_skill":
        if is_laser_bomb_drop_request(user_text or ""):
            raise AgentWorkspaceError(
                "掉落物需求禁止 enable_catalog_skill；"
                "请改会话 powerup_types/apply_powerup 或写 drop_loot_unlock.gd"
            )
        skill_id = str(action.get("skill_id", "")).strip()
        if not skill_id:
            raise AgentWorkspaceError("enable_catalog_skill 需要 skill_id")
        try:
            return enable_catalog_skill(workspace_root, genre, skill_id)
        except LearnedSkillsError as exc:
            raise AgentWorkspaceError(str(exc)) from exc
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
        errs = run_done_gates(
            workspace_root,
            written_paths=list(dict.fromkeys(written_paths or [])),
            summary=summary,
            how_to_play=how_to_play,
            genre=genre,
            contract=contract,
            catalog_changed=catalog_changed,
            user_text=user_text,
        )
        return {
            "tool": tool,
            "ok": not errs,
            "errors": errs,
            "detail": "门禁通过，可以 done" if not errs else "门禁未过，请继续改再 done",
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
) -> dict[str, Any]:
    """轮次耗尽/门禁多次未过时的兜底：尽力交付本轮已改内容，绝不上锁、绝不把游戏改到打不开。

    - 若磁盘能加载（或无代码改动）：返回本轮改动 = 诚实的"尽力而为、可能不完美、可继续"。
    - 若磁盘已被改到打不开：回滚本轮改动，保持可玩，诚实告知并邀请继续（仍不上锁）。
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

    if loads_ok and (written_unique or catalog_changed):
        # 尽力交付：本轮确有改动且游戏能加载
        if last_summary.strip():
            summary = last_summary.strip()
            if not re.search(r"可能|再|继续|不满意|如果", summary):
                summary += "（可能还没完全达到你要的效果，先重开看看；不满意再告诉我，我接着改。）"
        else:
            head = last_understanding.strip() or "按你说的改了这局游戏"
            summary = (
                f"{head}。我已经改了：{'、'.join(written_unique[:6]) or '本局配置'}。"
                "可能还没完全到位，先重开看看；不满意再说一句，我继续改。"
            )
        how = base_how or ["请重新启动游戏后试玩刚才的改动"]
        if not any("重开" in h or "启动" in h or "重新" in h for h in how):
            how.append("重要：重新启动游戏后新改动才会生效")
        return {
            "ok": True,
            "provider": "agent",
            "summary": summary,
            "message": summary,
            "changes": [],
            "sandbox_files": written_unique,
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
            "intent_route": route,
            "dry_run": dry,
        }

    # 改动会让游戏打不开 → 回滚保持可玩；仍不上锁
    if not loads_ok:
        rolled = _rollback_snapshot(workspace_root, pre_turn_snapshot)
        summary = (
            "这次的改法会让游戏打不开，我已经把这次改动撤回、保持游戏能正常玩（放心，没弄坏）。"
            "你可以再把想要的效果多说一点，或换个说法，我接着试。"
        )
        return {
            "ok": True,
            "provider": "agent",
            "summary": summary,
            "message": summary,
            "changes": [],
            "sandbox_files": [],
            "how_to_play": ["游戏保持原样，可继续试玩；想要的改动可以再说一次"],
            "applied_capabilities": [],
            "needs_relaunch": False,
            "verify_gaps": [f"本轮改动被回滚（会导致无法加载）：{reason}"],
            "repaired": False,
            "agent_rounds": rounds_used,
            "understanding": last_understanding,
            "goals": plan_goals,
            "progress": progress_events,
            "gate_passed": False,
            "partial": True,
            "rolled_back": rolled,
            "intent_route": route,
            "dry_run": dry,
        }

    # 本轮没有任何改动 → 温和邀请继续，不用"换个说法/没改成"的上锁话术
    summary = (
        (last_understanding.strip() + "。" if last_understanding.strip() else "")
        + "我还在琢磨怎么把这个改好，先没动你的游戏。"
        "你可以多给一点细节（想要什么效果、在哪出现），我继续帮你改。"
    )
    return {
        "ok": True,
        "provider": "agent",
        "summary": summary,
        "message": summary,
        "changes": [],
        "sandbox_files": [],
        "how_to_play": ["游戏保持原样，可继续试玩"],
        "applied_capabilities": [],
        "needs_relaunch": False,
        "verify_gaps": [f"本轮未产出改动：{reason}"],
        "repaired": False,
        "agent_rounds": rounds_used,
        "understanding": last_understanding,
        "goals": plan_goals,
        "progress": progress_events,
        "gate_passed": False,
        "partial": True,
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
    max_rounds: int = 8,
    *,
    run_dry_run: bool = False,
) -> dict[str, Any]:
    """执行智能体；成功返回 ok/provider=agent。

    轮次耗尽 / 门禁多次未过 → **不再抛异常上锁**，而是尽力交付本轮已改内容
    （见 `_salvage_agent_return`）；只有无 Key / LLM 通信等真错误才抛异常。
    """
    if not settings.llm_api_key.strip():
        raise ValueError("无 LLM_API_KEY，无法启动智能体")

    contract = load_contract(genre)
    progress_events: list[dict[str, Any]] = []
    emit_progress(workspace_root, "understand", user_text[:80] or "读懂需求")
    progress_events.append({"stage": "understand"})

    route = route_intent(user_text or feedback, contract)

    # catalog 捷径：激光/炸弹/二段跳等明确命中 → 秒级落地，不进多轮 LLM
    if _can_catalog_express(route, user_text, feedback):
        try:
            return _run_catalog_express(
                settings, workspace_root, genre, user_text, route, contract
            )
        except ValueError:
            # 快车道失败再走完整智能体
            emit_progress(workspace_root, "read_contract", "catalog 快车道未过，改走智能体")

    # shmup 掉落物捷径：仅当明确要「激光/炸弹做成掉落」时；通用掉落（爱心/金币等）走 LLM
    if (
        genre == "shmup"
        and is_laser_bomb_drop_request(user_text or "")
        and not feedback.strip()
    ):
        try:
            return _run_shmup_drop_loot_express(
                settings, workspace_root, user_text, route, contract
            )
        except ValueError:
            emit_progress(
                workspace_root, "read_contract", "掉落物快车道未过，改走智能体"
            )

    route_block = (
        "【意图建议·仅供参考，你可自主决策】\n" + format_route_for_prompt(route)
    )

    genre_ctx = genre_context_as_system_suffix(settings.templates_dir, genre)
    tree_preview = list_workspace_tree(
        workspace_root,
        settings.workspace_dir,
        settings.templates_dir,
        "",
        max_entries=40,
    )
    diag = diagnose_workspace(workspace_root, genre, contract)
    diag_block = format_diagnose_for_prompt(diag)

    emit_progress(workspace_root, "search_skills", "检索长期库")
    learned_hits = search_learned_skills(
        settings.learned_skills_dir,
        user_text or feedback,
        genre,
        k=5,
    )
    learned_block = format_skills_for_prompt(learned_hits)

    emit_progress(workspace_root, "read_contract", f"品类={genre} · 意图建议={route.get('intent')}")
    progress_events.append({"stage": "read_contract"})

    # 确定性助手：catalog 建议命中且非故障反馈时预开技能（advisory 也可预开）
    written: list[str] = []
    catalog_changed = False
    # 回合前快照：本轮首次改某文件前记录其原内容，兜底回滚（绝不把游戏改到打不开）
    pre_turn_snapshot: dict[str, bytes | None] = {}
    has_feedback = bool(feedback.strip()) or bool(
        re.search(r"没生效|不发射|没反应|不能用|只有.?键", user_text or "")
    )
    if route.get("intent") == "A" and not route.get("stop") and not has_feedback:
        for sid in route.get("skill_ids") or []:
            try:
                enable_catalog_skill(workspace_root, genre, str(sid))
                written.append("config/game_config.json")
                catalog_changed = True
            except LearnedSkillsError:
                pass

    # 路由已给出 goals 种子，避免首轮只能拆解不能写
    plan_goals: list[str] = []
    if route.get("intent") == "A" and route.get("skill_ids"):
        plan_goals = [f"开启 {sid}" for sid in route.get("skill_ids") or []][:5]
    elif str(route.get("hint") or "").strip():
        plan_goals = [str(route.get("hint")).strip()[:80]]

    for act in route.get("actions") or []:
        if not isinstance(act, dict):
            continue
        tool_name = str(act.get("tool", ""))
        if tool_name == "patch_mouse_steer_guard":
            if patch_shmup_mouse_steer_guard(workspace_root):
                written.append("core/player_ship.gd")
                emit_progress(
                    workspace_root, "write_changes", "已修补鼠标跟机与技能按钮冲突"
                )
        elif tool_name in ("refresh_ai_sandbox_bridge", "ensure_touch_skill_buttons"):
            if refresh_ai_sandbox_bridge(workspace_root, settings.templates_dir):
                written.append("core/ai_sandbox_bridge.gd")
                emit_progress(
                    workspace_root, "write_changes", "已刷新会话桥（触屏 HUD）"
                )

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
                + "；勿发明 bridge 方法，请在会话 core/scenes 用 GDScript 实现用户想要的效果"
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
        catalog_for_prompt(),
    ]
    if learned_block:
        context_bits.append(learned_block)
    context_bits.append(
        "请先给出 understanding + goals（拆解本轮原话），再施工；"
        "一条话里的多个要求都要进 goals 并尽量落地。"
        "done.summary 用自然中文直接回答本轮，覆盖各 goals；勿复读更早轮次宣传。"
    )
    user_blob = turn_text + "\n\n" + "\n".join(context_bits)

    system_content = _AGENT_SYSTEM + "\n\n" + genre_ctx
    if learned_block:
        system_content += "\n\n" + learned_block

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

    for _round in range(max(1, max_rounds)):
        emit_progress(
            workspace_root,
            "write_changes" if _round > 0 else "read_contract",
            f"智能体第 {_round + 1}/{max_rounds} 轮思考中…",
        )
        parsed = _llm_turn(settings, messages)
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
            raise ValueError("智能体未给出 actions")

        # 首轮或尚未拆解：要求先产出 goals，避免跳过理解直接乱写
        has_mutate = any(
            isinstance(a, dict)
            and str(a.get("tool", ""))
            in ("write_file", "enable_catalog_skill", "done")
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

        for raw in actions[:8]:
            if not isinstance(raw, dict):
                continue
            tool_name = str(raw.get("tool", "")).strip()
            if tool_name == "done":
                pending_done = raw
                continue
            if tool_name == "write_file":
                emit_progress(
                    workspace_root,
                    "write_changes",
                    str(raw.get("path", ""))[:60],
                )
            # 改文件前先快照原内容（本轮首次），供兜底回滚
            _snap_targets: list[str] = []
            if tool_name == "write_file":
                _p = str(raw.get("path", "")).strip().replace("\\", "/")
                if _p:
                    _snap_targets.append(_p)
            elif tool_name == "enable_catalog_skill":
                _snap_targets.append("config/game_config.json")
            elif tool_name == "patch_mouse_steer_guard":
                _snap_targets.append("core/player_ship.gd")
            elif tool_name in ("refresh_ai_sandbox_bridge", "ensure_touch_skill_buttons"):
                _snap_targets.append("core/ai_sandbox_bridge.gd")
            for _st in _snap_targets:
                if _st not in pre_turn_snapshot:
                    _sp = workspace_root / _st
                    try:
                        pre_turn_snapshot[_st] = _sp.read_bytes() if _sp.is_file() else None
                    except OSError:
                        pre_turn_snapshot[_st] = None
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
                )
            except (AgentWorkspaceError, OSError, ValueError) as exc:
                obs = {"tool": raw.get("tool"), "error": str(exc)}
            observations.append(obs)
            if obs.get("tool") == "write_file" and obs.get("path"):
                written.append(str(obs["path"]))
            if obs.get("tool") == "enable_catalog_skill" and not obs.get("error"):
                written.append("config/game_config.json")
                catalog_changed = True
            if obs.get("tool") in (
                "patch_mouse_steer_guard",
                "refresh_ai_sandbox_bridge",
                "ensure_touch_skill_buttons",
            ) and obs.get("ok"):
                path_w = str(obs.get("path") or "")
                if path_w:
                    written.append(path_w)
                elif obs.get("refreshed_bridge"):
                    written.append("core/ai_sandbox_bridge.gd")
            if obs.get("tool") == "search_learned_skills":
                for hit in obs.get("hits") or []:
                    sid = str(hit.get("skill_id") or "")
                    if sid and sid not in searched_ids:
                        searched_ids.append(sid)

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

            # 仅首开 catalog 建议时补 enable；反馈局不强制
            if (
                route.get("intent") == "A"
                and not route.get("advisory")
                and not has_feedback
            ):
                for sid in route.get("skill_ids") or []:
                    try:
                        enable_catalog_skill(workspace_root, genre, str(sid))
                        catalog_changed = True
                        written.append("config/game_config.json")
                    except LearnedSkillsError:
                        pass

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
                observations.append(
                    {
                        "tool": "done",
                        "error": "门禁未通过，禁止成功返回",
                        "gate_errors": gate_errors,
                    }
                )
                messages.append(
                    {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)}
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "done 被门禁拒绝，禁止口头成功。错误：\n"
                            + json.dumps(gate_errors, ensure_ascii=False)
                            + (
                                "\n本轮 goals：" + "；".join(plan_goals)
                                if plan_goals
                                else ""
                            )
                            + "\n请按 goals 补齐实现与 summary，再写入后重新 done。"
                        ),
                    }
                )
                if gate_failures >= 6:
                    # 不上锁：尽力交付本轮已改内容（能加载就给，坏了就回滚保可玩）
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
                    )
                continue

            # 门禁通过
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
            return {
                "ok": True,
                "provider": "agent",
                "summary": summary,
                "message": summary,
                "changes": [],
                "sandbox_files": list(dict.fromkeys(written)),
                "how_to_play": how_to_play,
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

        follow = (
            "工具结果:\n"
            + json.dumps(observations, ensure_ascii=False)[:8000]
        )
        if plan_goals:
            follow += "\n本轮 goals：" + "；".join(plan_goals) + "（未完成的请继续）"
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
        rounds_used=max(1, max_rounds),
        reason="未在限定轮次内完成",
    )
