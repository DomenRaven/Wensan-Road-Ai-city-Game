"""S-A2 · 自然语言改参（nl-patch）· OpenAI / DeepSeek 兼容。

职责：读 workspace game_config.json → LLM（或本地 stub）生成白名单 patch →
钳制（默认 ±15%）→ 写回 config；同时把变更镜像到
workspace/core/ai_sandbox/overrides.json（仅新建沙箱文件，不改冻结 core）。

可选：
- new_files → core/ai_sandbox/*.gd 修饰脚本
- icons/*.svg|png → 技能图标（运行时由 AiSandboxBridge HUD 加载）
- tuning.enabled_skills → 仅允许 optional_skills 目录内预制技能开关

红线：禁止写入 templates/**。
智能体主路径可改会话副本 core/config/scenes；无 Key 时离线 stub 只写 config + ai_sandbox。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests
from app.config import Settings
from app.services.ai_sandbox import (
    AiSandboxError,
    changes_to_overrides_patch,
    ensure_sandbox_dir,
    list_sandbox_files,
    write_modifier_gdscript,
    write_overrides_json,
    write_sandbox_asset,
)
from app.services.config_builder import (
    get_path,
    load_optional_skills_catalog,
    load_optional_skills_entries,
    load_optional_skills_max,
    set_path,
)
from app.services.creative.genre_context import genre_context_as_system_suffix
from app.services.creative.game_agent import run_game_agent
from app.services.creative.learned_skills import (
    append_session_patch_log,
    record_not_effective_feedback,
)
from app.services.creative.sandbox_intent import (
    catalog_for_prompt,
    compile_user_intent,
    how_to_play_for_applied,
    infer_applied_from_patch,
    merge_compiled_into,
    verify_against_request,
)
from app.services.agent_workspace import AgentWorkspaceError
from app.services.tuning_mapper import clamp_value
from app.services.workspace import workspace_config_path
from app.services.workspace_guard import (
    assert_not_under_templates,
    assert_under_workspace,
)

NL_PATCH_CLAMP_PERCENT: float = 30.0
_THEME_TITLE_MAX: int = 32
_SAFE_NEW_GD = re.compile(
    r"^(?:[a-z][a-z0-9_]{0,24}/){0,3}[a-z][a-z0-9_]{0,40}\.gd$"
)
_SAFE_NEW_ICON = re.compile(r"^(?:icons/)?[a-z][a-z0-9_]{0,40}\.(svg|png)$")
_SAFE_MANIFEST = "icons/manifest.json"


class NlPatchError(ValueError):
    """nl-patch 业务错误（超纲请求 / 白名单外路径等）。"""


def _walk_numeric(prefix: str, node: dict[str, Any], out: dict[str, float]) -> None:
    for key, value in node.items():
        if key == "enabled_skills":
            continue
        path: str = f"{prefix}.{key}"
        if isinstance(value, dict):
            _walk_numeric(path, value, out)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out[path] = float(value)


def numeric_tuning_paths(config: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    tuning: Any = config.get("tuning", {})
    if isinstance(tuning, dict):
        _walk_numeric("tuning", tuning, out)
    return out


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp_numeric(base_val: Any, requested: Any) -> Any:
    if not isinstance(base_val, (int, float)) or isinstance(base_val, bool):
        return None
    if not isinstance(requested, (int, float)) or isinstance(requested, bool):
        return None
    clamped: float = clamp_value(float(base_val), float(requested), NL_PATCH_CLAMP_PERCENT)
    if isinstance(base_val, int):
        return int(round(clamped))
    return round(clamped, 4)


def _sanitize_enabled_skills(
    raw_value: Any,
    genre: str,
    config: dict[str, Any],
) -> list[str] | None:
    if not isinstance(raw_value, list):
        return None
    catalog = set(load_optional_skills_catalog().get(genre, []))
    if not catalog:
        return None
    max_n = load_optional_skills_max()
    out: list[str] = []
    for item in raw_value:
        sid = str(item).strip()
        if sid in catalog and sid not in out:
            out.append(sid)
        if len(out) >= max_n:
            break
    before_raw = get_path(config, "tuning.enabled_skills")
    before: list[str] = (
        [str(x) for x in before_raw] if isinstance(before_raw, list) else []
    )
    if out == before:
        return None
    return out


def _sanitize_changes(
    raw_changes: dict[str, Any],
    config: dict[str, Any],
    base_config: dict[str, Any],
    genre: str,
) -> list[dict[str, Any]]:
    allowed_numeric: dict[str, float] = numeric_tuning_paths(base_config)
    changes: list[dict[str, Any]] = []
    for raw_path, raw_value in raw_changes.items():
        path: str = str(raw_path).strip()
        if not path:
            continue
        if path == "theme.title":
            if not isinstance(raw_value, str):
                continue
            new_title: str = raw_value.strip()[:_THEME_TITLE_MAX]
            if not new_title:
                continue
            before: Any = get_path(config, path)
            if str(before) == new_title:
                continue
            changes.append({"path": path, "before": before, "after": new_title})
            continue
        if path == "tuning.enabled_skills":
            after_skills = _sanitize_enabled_skills(raw_value, genre, config)
            if after_skills is None:
                continue
            before_skills = get_path(config, path)
            changes.append(
                {
                    "path": path,
                    "before": before_skills if isinstance(before_skills, list) else [],
                    "after": after_skills,
                }
            )
            continue
        if path.startswith("sandbox_rules.") or path.startswith("tuning.sandbox_rules."):
            before = get_path(config, path)
            if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
                after_num: float | int = (
                    int(round(float(raw_value)))
                    if "every" in path or path.endswith("_n")
                    else round(float(raw_value), 4)
                )
                if before == after_num:
                    continue
                changes.append({"path": path, "before": before, "after": after_num})
            continue
        if not path.startswith("tuning."):
            continue
        if path not in allowed_numeric:
            continue
        base_val: Any = get_path(base_config, path)
        after: Any = _clamp_numeric(base_val, raw_value)
        if after is None:
            continue
        before = get_path(config, path)
        if isinstance(before, (int, float)) and float(before) == float(after):
            continue
        changes.append({"path": path, "before": before, "after": after})
    return changes


def _apply_changes(config: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = json.loads(json.dumps(config))
    for change in changes:
        set_path(merged, str(change["path"]), change["after"])
    return merged


def _normalize_new_file_name(name: str) -> str | None:
    raw = name.strip().replace("\\", "/").lstrip("/")
    if raw.startswith("core/ai_sandbox/"):
        raw = raw[len("core/ai_sandbox/") :]
    if raw == _SAFE_MANIFEST:
        return raw
    if _SAFE_NEW_GD.match(raw):
        return raw
    if _SAFE_NEW_ICON.match(raw):
        if not raw.startswith("icons/"):
            return f"icons/{raw}"
        return raw
    return None


def _sanitize_new_files(raw_files: Any) -> list[dict[str, str]]:
    if not isinstance(raw_files, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw_files[:8]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("filename") or item.get("name") or item.get("path") or "").strip()
        content = str(item.get("content") or item.get("code") or "")
        norm = _normalize_new_file_name(name)
        if not norm or not content.strip():
            continue
        out.append({"filename": norm, "content": content})
    return out


_SYSTEM_PROMPT: str = (
    "你是少儿游戏工坊的关卡程序员助手。可以："
    "1) 调白名单数值（约±30%）与 theme.title；"
    "2) 开关预制技能 tuning.enabled_skills（最多2个，仅目录 id）；"
    "3) 【重点】在 core/ai_sandbox/ 【新建】任意 GDScript（可子目录）与 icons/*.svg，"
    "通过 /root/AiSandboxBridge 的 API 实现玩法（金币连击 buff、倒计时、特效等）。"
    "严禁修改已有 core 源文件与 templates；严禁 OS.execute / FileAccess WRITE / 联机商城广告。"
    "只返回 JSON："
    '{"changes": {...}, "new_files": [{"filename":"coin_streak_buff.gd","content":"..."}], "summary":"..."}。'
    "复杂需求必须写 new_files，不要只改数字假装完成。"
    "脚本须 extends Node 或 RefCounted，并实现 func apply(bridge)->void 调用 bridge API。"
    "若用户反馈「没生效」，优先补齐 sandbox_rules / enabled_skills / icons，并写清 summary 告诉怎么试玩。"
)


def _build_user_prompt(
    text: str,
    knobs: dict[str, float],
    current_title: str,
    genre: str,
    enabled_skills: list[str],
    genre_context: str,
    feedback: str = "",
    repair_gaps: list[str] | None = None,
) -> str:
    knob_lines: list[str] = [f"- {path} = {value}" for path, value in sorted(knobs.items())]
    skill_lines: list[str] = []
    for sid, label, desc in load_optional_skills_entries(genre):
        skill_lines.append(f"- {sid} · {label}：{desc}")
    if not skill_lines:
        skill_lines.append("- （本局无预制技能目录）")
    skills_now = ", ".join(enabled_skills) if enabled_skills else "（无）"
    parts: list[str] = [
        f"小朋友的要求：{text}",
        "",
        catalog_for_prompt(),
        "",
        genre_context,
        "",
        f"当前游戏标题（theme.title）：{current_title}",
        f"当前已启用技能 tuning.enabled_skills：{skills_now}",
        f"可启用预制技能（最多 {load_optional_skills_max()} 个）：",
        "\n".join(skill_lines),
        "",
        f"可调白名单数值（约±{NL_PATCH_CLAMP_PERCENT:g}%）：",
        "\n".join(knob_lines),
        "",
        "若需求包含新机制（每N金币、特效、倒计时等），必须同时写 sandbox_rules.* 与 new_files；"
        "开二段跳时写 tuning.enabled_skills 并配 icons/double_jump.svg。",
    ]
    fb = str(feedback or "").strip()
    if fb:
        parts.extend(["", f"【用户反馈·上次未生效】{fb}", "请针对反馈补齐缺失能力，不要重复无效改动。"])
    if repair_gaps:
        parts.extend(["", "【自检缺口·必须补齐】", *[f"- {g}" for g in repair_gaps]])
    return "\n".join(parts)


def _chat_completions_url(base_url: str) -> str:
    base: str = base_url.strip().rstrip("/")
    return f"{base}/chat/completions"


def _normalize_history(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[-8:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content[:500]})
    return out


def _call_llm(
    settings: Settings,
    text: str,
    knobs: dict[str, float],
    current_title: str,
    genre: str,
    enabled_skills: list[str],
    history: list[dict[str, str]] | None = None,
    feedback: str = "",
    repair_gaps: list[str] | None = None,
) -> dict[str, Any]:
    """调用兼容 OpenAI 的 chat/completions（DashScope 等）。用 requests 避开本机 urllib SSL EOF。"""
    url: str = _chat_completions_url(settings.llm_base_url)
    genre_context = genre_context_as_system_suffix(settings.templates_dir, genre)
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": _SYSTEM_PROMPT + "\n\n" + genre_context + "\n\n" + catalog_for_prompt(),
        },
    ]
    for turn in _normalize_history(history):
        messages.append(turn)
    messages.append(
        {
            "role": "user",
            "content": _build_user_prompt(
                text,
                knobs,
                current_title,
                genre,
                enabled_skills,
                genre_context,
                feedback=feedback,
                repair_gaps=repair_gaps,
            ),
        }
    )
    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
    }
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
        "X-API-Key": settings.llm_api_key,
    }
    response = requests.post(
        url,
        json=body,
        headers=headers,
        timeout=float(settings.llm_timeout_sec),
    )
    if response.status_code >= 400:
        raise ValueError(f"LLM HTTP {response.status_code}: {response.text[:400]}")
    payload: dict[str, Any] = response.json()

    choices: list[Any] = payload.get("choices", [])
    if not choices:
        raise ValueError("LLM 响应缺少 choices")
    content: str = str(choices[0].get("message", {}).get("content", "")).strip()
    if not content:
        raise ValueError("LLM 响应内容为空")
    parsed: Any = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回的不是 JSON 对象")
    raw_changes: Any = parsed.get("changes", {})
    if not isinstance(raw_changes, dict):
        raw_changes = {}
    return {
        "changes": raw_changes,
        "summary": str(parsed.get("summary", "")).strip(),
        "new_files": _sanitize_new_files(parsed.get("new_files")),
    }


_HARDER_WORDS: tuple[str, ...] = ("难", "硬", "厉害", "强", "hard", "快", "急", "冲")
_EASIER_WORDS: tuple[str, ...] = ("简单", "容易", "慢", "轻松", "easy", "友好", "温柔")

_SIMPLE_SKILL_SVGS: dict[str, str] = {
    "double_jump": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#38bdf8"/>'
        '<path d="M20 40c8-14 16-14 24 0" fill="none" stroke="#fff" stroke-width="4" '
        'stroke-linecap="round"/>'
        '<path d="M20 28c8-14 16-14 24 0" fill="none" stroke="#e0f2fe" stroke-width="4" '
        'stroke-linecap="round"/>'
        "</svg>"
    ),
    "ground_pound": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#f59e0b"/>'
        '<path d="M32 14v28" stroke="#fff" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M20 36l12 14 12-14" fill="none" stroke="#fff" stroke-width="5" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    ),
    "shield_burst": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#22c55e"/>'
        '<path d="M32 12l16 8v14c0 12-8 20-16 24-8-4-16-12-16-24V20z" fill="#fff" opacity=".95"/>'
        "</svg>"
    ),
}


def _default_skill_svg(skill_id: str) -> str:
    if skill_id in _SIMPLE_SKILL_SVGS:
        return _SIMPLE_SKILL_SVGS[skill_id]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="14" fill="#6366f1"/>'
        f'<text x="32" y="38" text-anchor="middle" font-size="18" fill="#fff">'
        f"{skill_id[:2]}</text></svg>"
    )


def _coin_streak_buff_script(every: int = 5, duration: float = 3.0) -> str:
    return (
        "extends Node\n"
        "\n"
        f"var _every: int = {every}\n"
        f"var _duration: float = {duration}\n"
        "var _bridge: Node = null\n"
        "\n"
        "func apply(bridge) -> void:\n"
        "\t_bridge = bridge\n"
        "\tif bridge != null and bridge.has_method(\"watch_coins\"):\n"
        "\t\tbridge.watch_coins(Callable(self, \"_on_coin\"))\n"
        "\n"
        "func _on_coin(total: int) -> void:\n"
        "\tif _bridge == null:\n"
        "\t\treturn\n"
        "\tif total <= 0 or (total % _every) != 0:\n"
        "\t\treturn\n"
        "\tif _bridge.has_method(\"grant_invincibility\"):\n"
        "\t\t_bridge.grant_invincibility(_duration)\n"
        "\tif _bridge.has_method(\"boost_move_speed\"):\n"
        "\t\t_bridge.boost_move_speed(1.35, _duration)\n"
        "\tif _bridge.has_method(\"flash_player_fx\"):\n"
        "\t\t_bridge.flash_player_fx(_duration)\n"
        "\tif _bridge.has_method(\"show_countdown\"):\n"
        "\t\t_bridge.show_countdown(_duration, \"无敌加速\")\n"
    )


def _stub_skill_and_icon_bundle(
    text: str,
    config: dict[str, Any],
    base_config: dict[str, Any],
    genre: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """本地 stub：识别二段跳 / 无敌 / 图标 / 金币连击等关键词。"""
    changes: list[dict[str, Any]] = []
    new_files: list[dict[str, str]] = []
    catalog = load_optional_skills_catalog().get(genre, [])
    want_icon = any(w in text for w in ("图标", "icon", "画画", "绘制"))
    skill_add: list[str] = []
    if any(w in text for w in ("二段跳", "双跳", "二段", "double")) and "double_jump" in catalog:
        skill_add.append("double_jump")
    if any(w in text for w in ("下砸", "砸地", "pound")) and "ground_pound" in catalog:
        skill_add.append("ground_pound")
    if any(w in text for w in ("护盾", "shield")) and "shield_burst" in catalog:
        skill_add.append("shield_burst")

    # 每 N 金币 → 无敌加速倒计时特效（原生规则 + 脚本双保险）
    if any(w in text for w in ("金币", "coin")) and any(
        w in text for w in ("无敌", "加速", "特效", "倒计时", "buff")
    ):
        every = 5
        changes.append(
            {
                "path": "sandbox_rules.coin_every",
                "before": get_path(config, "sandbox_rules.coin_every"),
                "after": every,
            }
        )
        changes.append(
            {
                "path": "sandbox_rules.coin_duration",
                "before": get_path(config, "sandbox_rules.coin_duration"),
                "after": 3.0,
            }
        )
        changes.append(
            {
                "path": "sandbox_rules.coin_speed_mult",
                "before": get_path(config, "sandbox_rules.coin_speed_mult"),
                "after": 1.35,
            }
        )
        new_files.append(
            {
                "filename": "coin_streak_buff.gd",
                "content": _coin_streak_buff_script(every, 3.0),
            }
        )

    if skill_add:
        before_raw = get_path(config, "tuning.enabled_skills")
        before: list[str] = [str(x) for x in before_raw] if isinstance(before_raw, list) else []
        merged: list[str] = []
        for sid in before + skill_add:
            if sid in catalog and sid not in merged:
                merged.append(sid)
        merged = merged[: load_optional_skills_max()]
        if merged != before:
            changes.append(
                {
                    "path": "tuning.enabled_skills",
                    "before": before,
                    "after": merged,
                }
            )
        if want_icon or skill_add:
            for sid in merged:
                new_files.append(
                    {
                        "filename": f"icons/{sid}.svg",
                        "content": _default_skill_svg(sid),
                    }
                )

    if any(w in text for w in ("无敌", "受伤闪", "invincible", "免伤")) and not any(
        w in text for w in ("金币", "coin")
    ):
        path = "tuning.lives.invincible_sec"
        if path in numeric_tuning_paths(base_config):
            base_val = get_path(base_config, path)
            before = get_path(config, path)
            after = _clamp_numeric(base_val, float(base_val) * 1.25)
            if after is not None and (
                not isinstance(before, (int, float)) or float(before) != float(after)
            ):
                changes.append({"path": path, "before": before, "after": after})

    return changes, new_files


def _stub_changes(
    text: str,
    config: dict[str, Any],
    base_config: dict[str, Any],
    genre: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    skill_changes, skill_files = _stub_skill_and_icon_bundle(
        text, config, base_config, genre
    )
    if skill_changes or skill_files:
        return skill_changes, skill_files

    knobs: dict[str, float] = numeric_tuning_paths(base_config)
    if not knobs:
        return [], []
    lowered: str = text.lower()
    harder: bool = any(w in lowered for w in _HARDER_WORDS)
    easier: bool = any(w in lowered for w in _EASIER_WORDS)
    direction: float = 1.0
    if easier and not harder:
        direction = -1.0

    def pick(keywords: tuple[str, ...]) -> list[str]:
        return [p for p in knobs if any(k in p for k in keywords)]

    targets: list[str] = []
    if any(w in lowered for w in ("跳", "jump")):
        targets = pick(("jump",))
    elif any(w in lowered for w in ("敌", "怪", "enemy", "monster", "npc", "对手")):
        targets = pick(("enemy", "patrol", "spawn", "horde", "npc", "ai"))
        direction = 1.0 if not easier else -1.0
    elif any(w in lowered for w in ("弯", "转", "转向", "turn", "steer")):
        targets = pick(("turn", "steer", "friction"))
    elif any(w in lowered for w in ("球", "ball")):
        targets = pick(("ball", "paddle"))
        if any(w in lowered for w in ("慢", "easy", "简单")):
            direction = -1.0
    elif any(w in lowered for w in ("分", "金", "coin", "score")):
        targets = pick(("coin", "score", "xp", "reward"))
    elif any(w in lowered for w in ("无敌", "invincible")):
        targets = pick(("invincible",))
    else:
        targets = pick(("speed", "move", "accel")) or list(knobs.keys())[:1]

    changes: list[dict[str, Any]] = []
    percent: float = NL_PATCH_CLAMP_PERCENT
    for path in targets[:2]:
        base_val: Any = get_path(base_config, path)
        if not isinstance(base_val, (int, float)) or isinstance(base_val, bool):
            continue
        requested: float = float(base_val) * (1.0 + direction * percent / 100.0)
        after: Any = _clamp_numeric(base_val, requested)
        if after is None:
            continue
        before: Any = get_path(config, path)
        if isinstance(before, (int, float)) and float(before) == float(after):
            continue
        changes.append({"path": path, "before": before, "after": after})
    return changes, []


def _mirror_to_sandbox(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    changes: list[dict[str, Any]],
    new_files: list[dict[str, str]],
) -> list[str]:
    written: list[str] = []
    ensure_sandbox_dir(workspace_root, settings.workspace_dir, settings.templates_dir)
    patch = changes_to_overrides_patch(changes)
    icon_theme: dict[str, str] = {}
    for item in new_files:
        name = item["filename"]
        if name.endswith(".svg") or name.endswith(".png"):
            sid = Path(name).stem
            icon_theme[sid] = f"res://core/ai_sandbox/{name}"
    if icon_theme:
        patch = _deep_merge_dict(patch, {"theme": {"skill_icons": icon_theme}})
    if patch:
        rel = write_overrides_json(
            workspace_root,
            settings.workspace_dir,
            settings.templates_dir,
            genre,
            patch,
        )
        written.append(rel)
    for item in new_files:
        name = item["filename"]
        try:
            if name.endswith(".gd"):
                rel = write_modifier_gdscript(
                    workspace_root,
                    settings.workspace_dir,
                    settings.templates_dir,
                    genre,
                    name,
                    item["content"],
                )
            else:
                rel = write_sandbox_asset(
                    workspace_root,
                    settings.workspace_dir,
                    settings.templates_dir,
                    genre,
                    name,
                    item["content"],
                )
            written.append(rel)
        except AiSandboxError:
            continue
    return written


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = json.loads(json.dumps(base)) if base else {}
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _ensure_coin_streak_rules(
    text: str,
    config: dict[str, Any],
    changes: list[dict[str, Any]],
    new_files: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not (
        any(w in text for w in ("金币", "coin"))
        and any(w in text for w in ("无敌", "加速", "特效", "倒计时", "buff"))
    ):
        return changes, new_files
    paths = {str(c.get("path")) for c in changes}
    out = list(changes)
    if "sandbox_rules.coin_every" not in paths:
        out.append(
            {
                "path": "sandbox_rules.coin_every",
                "before": get_path(config, "sandbox_rules.coin_every"),
                "after": 5,
            }
        )
    if "sandbox_rules.coin_duration" not in paths:
        out.append(
            {
                "path": "sandbox_rules.coin_duration",
                "before": get_path(config, "sandbox_rules.coin_duration"),
                "after": 3.0,
            }
        )
    if "sandbox_rules.coin_speed_mult" not in paths:
        out.append(
            {
                "path": "sandbox_rules.coin_speed_mult",
                "before": get_path(config, "sandbox_rules.coin_speed_mult"),
                "after": 1.35,
            }
        )
    files = list(new_files)
    if not any(str(f.get("filename", "")).endswith("coin_streak_buff.gd") for f in files):
        files.append(
            {
                "filename": "coin_streak_buff.gd",
                "content": _coin_streak_buff_script(5, 3.0),
            }
        )
    return out, files


def _ensure_double_jump_bundle(
    text: str,
    config: dict[str, Any],
    genre: str,
    changes: list[dict[str, Any]],
    new_files: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not any(w in text for w in ("二段跳", "双跳", "二段", "double")):
        return changes, new_files
    catalog = load_optional_skills_catalog().get(genre, [])
    if "double_jump" not in catalog:
        return changes, new_files
    out = list(changes)
    paths = {str(c.get("path")) for c in out}
    if "tuning.enabled_skills" not in paths:
        before_raw = get_path(config, "tuning.enabled_skills")
        before: list[str] = [str(x) for x in before_raw] if isinstance(before_raw, list) else []
        merged = list(before)
        if "double_jump" not in merged:
            merged.append("double_jump")
        merged = merged[: load_optional_skills_max()]
        out.append(
            {
                "path": "tuning.enabled_skills",
                "before": before,
                "after": merged,
            }
        )
    files = list(new_files)
    want_icon = any(w in text for w in ("图标", "icon", "画画", "绘制", "画"))
    if want_icon and not any("double_jump.svg" in str(f.get("filename", "")) for f in files):
        files.append(
            {
                "filename": "icons/double_jump.svg",
                "content": _default_skill_svg("double_jump"),
            }
        )
    return out, files


def _log_patch_result(
    settings: Settings,
    workspace_root: Path,
    genre: str,
    request_text: str,
    feedback_text: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """成功改动写入本局日志；「没生效」反馈降权长期库。"""
    blob: str = f"{feedback_text}\n{request_text}"
    if "没生效" in blob or "没有生效" in blob:
        demoted = record_not_effective_feedback(
            settings.learned_skills_dir,
            request_text or feedback_text,
            genre,
            k=3,
        )
        result = dict(result)
        result["demoted_skills"] = demoted
    if result.get("ok"):
        append_session_patch_log(
            workspace_root,
            {
                "ok": True,
                "provider": result.get("provider"),
                "user_text": request_text,
                "feedback": feedback_text,
                "summary": result.get("summary") or result.get("message"),
                "how_to_play": result.get("how_to_play") or [],
                "sandbox_files": result.get("sandbox_files") or [],
                "applied_capabilities": result.get("applied_capabilities") or [],
                "gate_passed": bool(result.get("gate_passed")),
                "changes": result.get("changes") or [],
                "learned_skills": result.get("learned_skills") or [],
            },
        )
    return result


def _is_bugfix_request(*texts: str) -> bool:
    blob = "\n".join(str(t or "") for t in texts)
    return bool(
        re.search(
            r"消失|不显示|看不见|白屏|黑屏|没法.*启动|无法启动|打不开|闪退|报错|"
            r"修复|修好|坏了|人物.*没|角色.*没|看不到画|没有画面|没生效|点了没反应",
            blob,
        )
    )


def apply_nl_patch(
    settings: Settings,
    workspace_root: Path,
    templates_dir: Path,
    genre: str,
    text: str,
    history: list[dict[str, str]] | None = None,
    feedback: str = "",
) -> dict[str, Any]:
    request_text: str = str(text or "").strip()
    feedback_text: str = str(feedback or "").strip()
    if not request_text and not feedback_text:
        raise NlPatchError("请先说出你想怎么改")
    if not request_text and feedback_text:
        # 「没生效」续聊：用反馈当本轮诉求，结合历史
        request_text = feedback_text
        feedback_text = "上次改动试玩时没生效，请按能力目录补齐并写清怎么玩"
    if len(request_text) > 500:
        request_text = request_text[:500]
    if len(feedback_text) > 300:
        feedback_text = feedback_text[:300]

    config_path: Path = workspace_config_path(workspace_root)
    resolved: Path = assert_under_workspace(config_path, settings.workspace_dir.resolve())
    assert_not_under_templates(resolved, templates_dir.resolve())
    if not resolved.is_file():
        raise NlPatchError("workspace 尚未生成，请先完成制作")

    config: dict[str, Any] = _load_json(resolved)
    base_config_path: Path = templates_dir / genre / "config" / "game_config.json"
    base_config: dict[str, Any] = (
        _load_json(base_config_path) if base_config_path.is_file() else config
    )
    knobs: dict[str, float] = numeric_tuning_paths(base_config)
    current_title: str = str(get_path(config, "theme.title") or "")
    enabled_raw = get_path(config, "tuning.enabled_skills")
    enabled_skills: list[str] = (
        [str(x) for x in enabled_raw] if isinstance(enabled_raw, list) else []
    )

    # 1) 确定性意图编译（降级兜底 + 智能体成功后的技能补齐）
    compiled: dict[str, Any] = compile_user_intent(request_text, genre, config)

    provider: str = "stub"
    summary: str = ""
    llm_error: str = ""
    new_files: list[dict[str, str]] = []
    changes: list[dict[str, Any]] = []
    repaired: bool = False

    # 1b) 【唯一主路径】有 API Key → 只走智能体（可写会话 core/scenes）。
    # 不再降级到旧「只改 tuning」的 _call_llm / stub——那不是 LLM 做不到，是历史兜底在误导。
    # 无 API Key → 才用本地 stub（展厅离线演示）。
    bugfix = _is_bugfix_request(request_text, feedback_text)
    agent_feedback = feedback_text
    if bugfix and not agent_feedback:
        agent_feedback = (
            "这是运行故障反馈：请 diagnose_workspace + 读玩家/主场景/近期改动，"
            "修复可见性或启动问题；禁止再开新技能或叠无关 buff。"
        )

    if settings.llm_api_key.strip():
        # 网络类可再试 1 次；门禁/业务失败不整段重跑（避免 6 分钟×2）
        agent_attempts = 2
        last_exc: BaseException | None = None
        for attempt in range(agent_attempts):
            try:
                fb = agent_feedback
                if attempt > 0:
                    fb = (
                        (fb + "；" if fb else "")
                        + "上一轮未完成，请继续：先 understanding+goals，再读盘施工，勿空 done。"
                    )
                agent_out: dict[str, Any] = run_game_agent(
                    settings,
                    workspace_root,
                    genre,
                    request_text,
                    history=history,
                    feedback=fb,
                    max_rounds=10,
                    run_dry_run=False,
                )
                how_lines = list(agent_out.get("how_to_play") or [])
                msg = str(agent_out.get("summary") or agent_out.get("message") or "").strip()
                if not msg:
                    msg = "已按你这句话改好了本局游戏副本"
                files = list(dict.fromkeys(list(agent_out.get("sandbox_files") or [])))
                applied_caps = list(agent_out.get("applied_capabilities") or [])
                return _log_patch_result(
                    settings,
                    workspace_root,
                    genre,
                    request_text,
                    feedback_text,
                    {
                        "ok": True,
                        "provider": "agent",
                        "summary": msg,
                        "message": msg,
                        "changes": list(agent_out.get("changes") or []),
                        "sandbox_files": files,
                        "llm_error": "",
                        "how_to_play": how_lines,
                        "applied_capabilities": applied_caps,
                        "needs_relaunch": True,
                        "verify_gaps": list(agent_out.get("verify_gaps") or []),
                        "repaired": attempt > 0,
                        "agent_rounds": agent_out.get("agent_rounds"),
                        "learned_skills": list(agent_out.get("learned_skills") or []),
                        "gate_passed": bool(agent_out.get("gate_passed")),
                        "progress": list(agent_out.get("progress") or []),
                        "dry_run": agent_out.get("dry_run") or {},
                        "intent_route": agent_out.get("intent_route"),
                        "diagnose": agent_out.get("diagnose"),
                        "understanding": agent_out.get("understanding"),
                        "goals": list(agent_out.get("goals") or []),
                        "express": bool(agent_out.get("express")),
                    },
                )
            except (
                requests.RequestException,
                TimeoutError,
            ) as exc:
                last_exc = exc
                llm_error = f"agent:{exc}"
                continue
            except (
                ValueError,
                json.JSONDecodeError,
                OSError,
                AgentWorkspaceError,
            ) as exc:
                # 业务/门禁失败：不整段重跑（否则「发射激光」可拖到十几分钟）
                last_exc = exc
                llm_error = f"agent:{exc}"
                break

        detail = str(last_exc or llm_error).strip()[:200]
        message = (
            "智能体这轮没改成（不是降级成规则引擎，是施工/门禁未通过）。"
            "请换个说法或再发一次，我继续用智能体改会话副本。"
        )
        if detail:
            message = message.rstrip("。") + f"。线索：{detail}"
        return _log_patch_result(
            settings,
            workspace_root,
            genre,
            request_text,
            feedback_text,
            {
                "ok": False,
                "provider": "agent",
                "summary": message,
                "message": message,
                "changes": [],
                "sandbox_files": list_sandbox_files(workspace_root),
                "llm_error": llm_error,
                "how_to_play": [
                    "可直接再发一次同样的需求",
                    "或补充更具体的现象后让我继续改",
                ],
                "applied_capabilities": [],
                "needs_relaunch": False,
                "verify_gaps": [detail] if detail else [],
                "repaired": False,
                "gate_passed": False,
            },
        )

    # —— 以下仅「无 LLM_API_KEY」离线 stub ——
    provider = "stub"
    changes, new_files = _stub_changes(request_text, config, base_config, genre)

    # 2) 编译结果优先合并（技能 / sandbox_rules / 缺省脚本图标）
    changes, new_files = merge_compiled_into(changes, new_files, compiled)

    # 3) 后端兜底（与编译重叠时幂等）
    changes, new_files = _ensure_coin_streak_rules(
        request_text, config, changes, new_files
    )
    changes, new_files = _ensure_double_jump_bundle(
        request_text, config, genre, changes, new_files
    )

    # 4) stub 自检缺口 → 再合并编译（有 Key 时不会走到这里）
    applied: list[str] = infer_applied_from_patch(changes, new_files)
    for cap in compiled.get("applied_capabilities", []):
        if cap not in applied:
            applied.append(str(cap))
    gaps: list[str] = verify_against_request(request_text, applied)
    if gaps:
        changes, new_files = merge_compiled_into(changes, new_files, compiled)
        applied = infer_applied_from_patch(changes, new_files)
        gaps = verify_against_request(request_text, applied)

    how_lines: list[str] = list(compiled.get("how_to_play") or [])
    if not how_lines:
        how_lines = how_to_play_for_applied(applied, request_text)
    else:
        # 补一条重开提示
        if not any("重新启动" in h for h in how_lines):
            how_lines.append("重要：必须重新启动游戏后新规则才会生效")

    if not changes and not new_files:
        # 意图已理解但无可写增量（已在上限 / 技能已开）→ 仍算对话成功，避免「越改越失败」
        if applied or compiled.get("how_to_play"):
            how_lines = list(compiled.get("how_to_play") or []) or how_to_play_for_applied(
                applied, request_text
            )
            summary = (
                "你要的改动已经在当前安全范围内了；请按试玩说明重开游戏验证。"
                if not feedback_text
                else "已按反馈复查：规则/技能仍在，请重开游戏按说明再试。"
            )
            if how_lines:
                summary = summary.rstrip("。") + "。试玩：" + "；".join(how_lines[:3])
            return _log_patch_result(
                settings,
                workspace_root,
                genre,
                request_text,
                feedback_text,
                {
                    "ok": True,
                    "provider": provider,
                    "summary": summary,
                    "changes": [],
                    "sandbox_files": list_sandbox_files(workspace_root),
                    "message": summary,
                    "llm_error": llm_error,
                    "how_to_play": how_lines,
                    "applied_capabilities": applied,
                    "needs_relaunch": True,
                    "verify_gaps": gaps,
                    "repaired": repaired,
                    "already_applied": True,
                },
            )
        message: str = (
            "本地规则没太听懂，可以说得更具体些（比如「开二段跳」「无敌久一点」）"
        )
        return _log_patch_result(
            settings,
            workspace_root,
            genre,
            request_text,
            feedback_text,
            {
                "ok": False,
                "provider": provider,
                "summary": summary or message,
                "changes": [],
                "sandbox_files": list_sandbox_files(workspace_root),
                "message": message,
                "llm_error": llm_error,
                "how_to_play": [],
                "applied_capabilities": [],
                "needs_relaunch": False,
                "verify_gaps": gaps,
                "repaired": repaired,
            },
        )

    if changes:
        merged: dict[str, Any] = _apply_changes(config, changes)
        resolved.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    sandbox_written: list[str] = _mirror_to_sandbox(
        settings, workspace_root, genre, changes, new_files
    )

    if not summary:
        summary = (
            "已按你的话落地玩法（沙箱规则/技能），请重开游戏后按试玩说明体验"
            if provider == "llm"
            else "本地规则已落地玩法，请重开游戏后按试玩说明体验"
        )
    if how_lines:
        summary = summary.rstrip("。") + "。" + "试玩：" + "；".join(how_lines[:3])

    return _log_patch_result(
        settings,
        workspace_root,
        genre,
        request_text,
        feedback_text,
        {
            "ok": True,
            "provider": provider,
            "summary": summary,
            "changes": changes,
            "sandbox_files": sandbox_written or list_sandbox_files(workspace_root),
            "message": summary,
            "llm_error": llm_error,
            "how_to_play": how_lines,
            "applied_capabilities": applied,
            "needs_relaunch": True,
            "verify_gaps": gaps,
            "repaired": repaired,
        },
    )
