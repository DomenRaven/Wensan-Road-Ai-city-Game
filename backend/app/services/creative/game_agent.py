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
from app.services.creative.intent_router import (
    enforce_route_on_actions,
    format_route_for_prompt,
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
- 用户没提就不要送无关大礼包；长期库仅明显相关才复用

【聪明拆解 · 每轮必须】
1. understanding：用一句话复述本轮用户到底要什么
2. goals：拆成 1～5 条可验收子目标（一条用户话里的多个要求都要拆开，例如「加炸弹 + 酷炫特效 + 全屏震动 + 别动原子弹」→ 多条 goals）
3. 再 actions：先读盘/诊断，再按 goals 逐项施工，最后 self_check → done
4. 禁止跳过拆解直接 done；未覆盖的 goal 要么继续改，要么在 summary 诚实说明没做成哪一条

【创作】
- 尽量做出来：会话 core/**、scenes/**、config/**、ai_sandbox 均可写；catalog / 桥 API / Learned Skills 是捷径不是天花板
- 实现用户要的机制本身，勿用无关玩法顶替后口头当作完成
- 禁止空 done、幻想 API（add_method / set_color / OS.execute 等）；禁止改 templates/**、project.godot
- 声称 ⊆ 磁盘；新操作尽量触屏可点；how_to_play 含重开 + 点屏

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
        timeout=max(90.0, float(settings.llm_timeout_sec)),
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


def run_game_agent(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    user_text: str,
    history: list[dict[str, str]] | None = None,
    feedback: str = "",
    max_rounds: int = 16,
    *,
    run_dry_run: bool = True,
) -> dict[str, Any]:
    """执行智能体；成功返回 ok/provider=agent；失败抛异常供上层重试/诚实失败。"""
    if not settings.llm_api_key.strip():
        raise ValueError("无 LLM_API_KEY，无法启动智能体")

    contract = load_contract(genre)
    progress_events: list[dict[str, Any]] = []
    emit_progress(workspace_root, "understand", user_text[:80] or "读懂需求")
    progress_events.append({"stage": "understand"})

    route = route_intent(user_text or feedback, contract)
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

    # 确定性助手：仅在建议动作为补丁/刷桥时预执行；开 catalog 不在反馈局强制
    written: list[str] = []
    catalog_changed = False
    has_feedback = bool(feedback.strip()) or bool(
        re.search(r"没生效|不发射|没反应|不能用|只有.?键", user_text or "")
    )
    if (
        route.get("intent") == "A"
        and not route.get("stop")
        and not route.get("advisory")
        and not has_feedback
    ):
        for sid in route.get("skill_ids") or []:
            try:
                enable_catalog_skill(workspace_root, genre, str(sid))
                written.append("config/game_config.json")
                catalog_changed = True
            except LearnedSkillsError:
                pass

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
    plan_goals: list[str] = []
    learned_skill_ids_used: list[str] = [
        str(h.get("skill_id")) for h in learned_hits if h.get("skill_id")
    ]
    searched_ids: list[str] = []
    gate_failures = 0
    dry_run_result: dict[str, Any] | None = None

    for _round in range(max(1, max_rounds)):
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
            # 多 goals 时：summary 应尽量回应拆解结果（启发式，防只完成一条就交差）
            if len(plan_goals) >= 2:
                blob = summary + "\n" + "\n".join(how_to_play)
                uncovered = [
                    g
                    for g in plan_goals
                    if not any(
                        token and token in blob
                        for token in re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", g)[:3]
                    )
                ]
                if len(uncovered) >= max(2, len(plan_goals) - 1):
                    gate_errors.append(
                        "请在 summary 中覆盖本轮 goals（现缺少对："
                        + "；".join(uncovered[:3])
                        + " 的说明）"
                    )

            if run_dry_run and not gate_errors and written:
                dry_run_result = dry_run_godot(
                    workspace_root, settings.godot_path, timeout_sec=20.0
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
                if gate_failures >= 4:
                    raise ValueError(
                        "智能体 done 门禁多次失败: " + "; ".join(gate_errors[:6])
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

    raise ValueError("智能体未在限定轮次内完成（无 done）")
