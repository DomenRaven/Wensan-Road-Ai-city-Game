"""品类 Capability Contract：加载、注入、写后门禁（assert_apis / assert_claims / validate）。"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from app.config import ROOT_DIR

ProgressCallback = Callable[[str, str, str], None]

# 与需求 §3.1 / D7 对齐的阶段 id → 中文名
PROGRESS_STAGES: dict[str, tuple[str, str]] = {
    "understand": ("理解需求", "读懂孩子想改什么"),
    "search_skills": ("检索长期技能", "查找已验证的同类改法"),
    "read_contract": ("读取品类契约", "核对可调用 API 与挂钩路径"),
    "write_changes": ("写入改动", "改会话副本 core/config/scenes"),
    "validate": ("校验脚本与声称", "语法 · 契约 API · 声称对齐磁盘"),
    "done": ("完成说明", "整理试玩步骤"),
}

# 全局禁止幻想 API（即使未写进契约 forbidden 列表）
_GLOBAL_FORBIDDEN_APIS: tuple[str, ...] = (
    "add_method",
    "bridge.add_method",
    "ClassDB.instantiate",
    "merge_overrides",
    "patch_tuning",
    "set_color(",
    "bullet.set_color",
)

# Godot 4 常见写错：Color.red → Color.RED
_BAD_COLOR_LITERALS: re.Pattern[str] = re.compile(
    r"\bColor\.(red|green|blue|white|black|yellow|cyan|magenta|orange|gray|grey)\b"
)

_BRIDGE_CALL_RE: re.Pattern[str] = re.compile(
    r"\bbridge\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\("
)

# 声称关键词 → 磁盘验收策略
_CLAIM_RULES: list[tuple[re.Pattern[str], str, list[str]]] = [
    # (claim_pattern, claim_label, evidence_needles)
    (re.compile(r"护盾|盾牌|shield", re.I), "护盾", ["grant_temp_shield", "_has_shield", "apply_powerup", "\"shield\""]),
    (re.compile(r"五颜六色|彩色子弹|彩虹|bullet.?tint|tint_player", re.I), "彩色子弹", ["tint_player_bullets", "rainbow_player_bullets", "modulate", "Color("]),
    (re.compile(r"炸弹|清屏|bomb", re.I), "炸弹", ["\"bomb\"", "bomb"]),
    (re.compile(r"激光|laser", re.I), "激光", ["laser_beam", "\"laser_beam\""]),
    (re.compile(r"二段跳|双跳|double.?jump", re.I), "二段跳", ["double_jump", "grant_invincibility"]),
    (re.compile(r"下砸|ground.?pound", re.I), "下砸", ["ground_pound"]),
    (re.compile(r"无敌", re.I), "无敌", ["grant_invincibility", "_invincible", "invincible"]),
    (
        re.compile(r"boss|BOSS|首领|关底|头目|Boss战|boss战", re.I),
        "Boss",
        ["boss", "Boss", "spawn_boss", "boss_hp", "BossHP", "head_enemy"],
    ),
]


def default_contracts_dir() -> Path:
    return ROOT_DIR / "config" / "agent_contracts"


def load_contract(genre: str, contracts_dir: Path | None = None) -> dict[str, Any]:
    """加载品类契约；缺失时返回最小安全契约。"""
    base = contracts_dir or default_contracts_dir()
    path = base / f"{genre}.json"
    if not path.is_file():
        return _minimal_contract(genre)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _minimal_contract(genre)
    raw.setdefault("genre", genre)
    raw.setdefault("bridge_apis", [])
    raw.setdefault("catalog_skills", [])
    raw.setdefault("edit_recipes", [])
    raw.setdefault("hooks", {})
    raw.setdefault("notes", [])
    raw.setdefault("forbidden_invented_apis", list(_GLOBAL_FORBIDDEN_APIS))
    return raw


def _minimal_contract(genre: str) -> dict[str, Any]:
    return {
        "genre": genre,
        "bridge_apis": [
            {"name": "get_player", "sig": "() -> CharacterBody2D"},
            {"name": "get_player_node", "sig": "() -> Node"},
            {"name": "get_game_manager", "sig": "() -> Node"},
            {"name": "watch_coins", "sig": "(cb: Callable) -> void"},
            {"name": "get_coin_count", "sig": "() -> int"},
            {"name": "grant_invincibility", "sig": "(seconds: float) -> void"},
            {"name": "boost_move_speed", "sig": "(multiplier: float, seconds: float) -> void"},
            {"name": "show_countdown", "sig": "(seconds: float, title: String = \"倒计时\") -> void"},
            {"name": "flash_player_fx", "sig": "(seconds: float) -> void"},
            {"name": "set_tuning_number", "sig": "(dotted_path: String, value: float) -> void"},
        ],
        "catalog_skills": [],
        "edit_recipes": [],
        "hooks": {},
        "notes": ["契约文件缺失，仅注入通用桥 API"],
        "forbidden_invented_apis": list(_GLOBAL_FORBIDDEN_APIS),
    }


def bridge_api_names(contract: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for item in contract.get("bridge_apis") or []:
        if isinstance(item, dict):
            n = str(item.get("name", "")).strip()
            if n:
                names.add(n)
        elif isinstance(item, str) and item.strip():
            names.add(item.strip())
    return names


def format_contract_for_prompt(contract: dict[str, Any]) -> str:
    """注入 system / user 的契约摘要。"""
    genre = str(contract.get("genre", ""))
    lines: list[str] = [
        f"## 品类 Capability Contract（genre={genre}）",
        "创作主路径：在会话副本 core/**、config/**、scenes/** 用 GDScript/场景实现用户需求。",
        "bridge_apis 是可选捷径（调用 bridge.xxx 时必须在下列列表）；catalog 可复用勿限死。",
        "禁止发明 add_method / set_color 等幻想钩子；禁止改 templates。",
        "",
        "### bridge_apis（可选）",
    ]
    for item in contract.get("bridge_apis") or []:
        if isinstance(item, dict):
            lines.append(
                f"- {item.get('name')}{item.get('sig', '')} — {item.get('desc', '')}"
            )
        else:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("### catalog_skills（可复用捷径；也可用会话 core 另写等价实现）")
    skills = contract.get("catalog_skills") or []
    if skills:
        for s in skills:
            if isinstance(s, dict):
                rt = s.get("runtime") if isinstance(s.get("runtime"), dict) else {}
                rt_s = ""
                if rt:
                    rt_s = (
                        f" · runtime[input={rt.get('input', '')}, "
                        f"effect={rt.get('effect', '')}, touch={rt.get('touch', '')}]"
                    )
                lines.append(
                    f"- {s.get('id')} · {s.get('label', '')}：{s.get('desc', '')} "
                    f"（{s.get('trigger', '')}）{rt_s}"
                )
            else:
                lines.append(f"- {s}")
    else:
        lines.append("- （无预制）")
    lines.append("")
    lines.append("### edit_recipes（意图 → 正确施工路径）")
    for r in contract.get("edit_recipes") or []:
        if not isinstance(r, dict):
            continue
        lines.append(
            f"- [{r.get('intent')}] → {r.get('action')} · {r.get('paths', '')} · {r.get('hint', '')}"
        )
    hooks = contract.get("hooks") or {}
    if isinstance(hooks, dict) and hooks:
        lines.append("")
        lines.append("### hooks（关键相对路径）")
        for k, v in hooks.items():
            lines.append(f"- {k}: {v}")
    notes = contract.get("notes") or []
    if notes:
        lines.append("")
        lines.append("### notes")
        for n in notes:
            lines.append(f"- {n}")
    forbid = contract.get("forbidden_invented_apis") or list(_GLOBAL_FORBIDDEN_APIS)
    lines.append("")
    lines.append("### 禁止幻想 API")
    lines.append(", ".join(str(x) for x in forbid))
    return "\n".join(lines)


def validate_gdscript(content: str) -> list[str]:
    """轻量 GDScript 校验：结构 / 危险片段 / Godot4 颜色字面量。"""
    errors: list[str] = []
    body = content.strip()
    if not body:
        errors.append("脚本为空")
        return errors
    if "extends " not in body and "class_name " not in body:
        errors.append("缺少 extends / class_name")
    if body.count("(") != body.count(")"):
        errors.append("括号不配对")
    if body.count("{") != body.count("}"):
        errors.append("花括号不配对")
    bad = _BAD_COLOR_LITERALS.search(body)
    if bad:
        errors.append(f"Godot 4 颜色应为大写常量，勿写 Color.{bad.group(1)}")
    for snip in _GLOBAL_FORBIDDEN_APIS:
        if snip in body:
            errors.append(f"含幻想/禁止 API: {snip}")
    return errors


def assert_apis_in_contract(content: str, contract: dict[str, Any]) -> list[str]:
    """脚本中 bridge.xxx( 调用必须 ∈ 契约 bridge_apis。"""
    allowed = bridge_api_names(contract)
    forbid = {
        str(x) for x in (contract.get("forbidden_invented_apis") or _GLOBAL_FORBIDDEN_APIS)
    }
    errors: list[str] = []
    for snip in forbid:
        if snip and snip in content:
            errors.append(f"禁止 API: {snip}")
    for m in _BRIDGE_CALL_RE.finditer(content):
        name = m.group(1)
        if name not in allowed:
            errors.append(f"桥 API 不在契约内: bridge.{name}()")
    return list(dict.fromkeys(errors))


def _read_workspace_blob(workspace_root: Path, rels: list[str]) -> str:
    parts: list[str] = []
    cfg = workspace_root / "config" / "game_config.json"
    if cfg.is_file():
        parts.append(cfg.read_text(encoding="utf-8", errors="ignore"))
    for rel in rels:
        p = workspace_root / rel
        if p.is_file() and p.suffix.lower() in {".gd", ".json", ".tscn", ".md"}:
            parts.append(p.read_text(encoding="utf-8", errors="ignore")[:8000])
    core = workspace_root / "core"
    if core.is_dir():
        for p in sorted(core.glob("*.gd")):
            parts.append(p.read_text(encoding="utf-8", errors="ignore")[:4000])
        sandbox = core / "ai_sandbox"
        if sandbox.is_dir():
            for p in sorted(sandbox.rglob("*.gd")):
                parts.append(p.read_text(encoding="utf-8", errors="ignore")[:4000])
    scenes = workspace_root / "scenes"
    if scenes.is_dir():
        for p in sorted(scenes.rglob("*.tscn"))[:20]:
            parts.append(p.read_text(encoding="utf-8", errors="ignore")[:3000])
    return "\n".join(parts)


def _enabled_skills(workspace_root: Path) -> list[str]:
    cfg_path = workspace_root / "config" / "game_config.json"
    if not cfg_path.is_file():
        return []
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    tuning = cfg.get("tuning") if isinstance(cfg, dict) else {}
    if not isinstance(tuning, dict):
        return []
    raw = tuning.get("enabled_skills") or []
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _workspace_has_touch_pathway(workspace_root: Path) -> bool:
    """L3 触屏：edu 注入的 overlay、或桥/沙箱 ensure_touch_*。"""
    core = workspace_root / "core"
    if core.is_dir():
        for p in core.glob("*_touch_overlay.gd"):
            if p.is_file():
                return True
        bridge = core / "ai_sandbox_bridge.gd"
        if bridge.is_file():
            blob = bridge.read_text(encoding="utf-8", errors="ignore")
            if "ensure_touch_action" in blob or "ensure_touch_skill_buttons" in blob:
                return True
        sandbox = core / "ai_sandbox"
        if sandbox.is_dir():
            for p in sandbox.rglob("*.gd"):
                txt = p.read_text(encoding="utf-8", errors="ignore")
                if "ensure_touch_action" in txt or "ensure_touch_skill_buttons" in txt:
                    return True
    return False


def diagnose_workspace(
    workspace_root: Path,
    genre: str,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """会话盘点：给智能体真实阅读起点（非幻想）。"""
    core = workspace_root / "core"
    bridge = core / "ai_sandbox_bridge.gd"
    bridge_txt = (
        bridge.read_text(encoding="utf-8", errors="ignore") if bridge.is_file() else ""
    )
    ship = core / "player_ship.gd"
    ship_txt = ship.read_text(encoding="utf-8", errors="ignore") if ship.is_file() else ""
    overlays = (
        sorted(p.name for p in core.glob("*_touch_overlay.gd")) if core.is_dir() else []
    )
    sandbox_files: list[str] = []
    sandbox = core / "ai_sandbox"
    if sandbox.is_dir():
        sandbox_files = [
            p.relative_to(workspace_root).as_posix()
            for p in sorted(sandbox.rglob("*.gd"))
        ]
    skills = _enabled_skills(workspace_root)
    catalog_ids: list[str] = []
    if isinstance(contract, dict):
        for item in contract.get("catalog_skills") or []:
            if isinstance(item, dict) and item.get("id"):
                catalog_ids.append(str(item["id"]))
    hints: list[str] = []
    if skills and not _workspace_has_touch_pathway(workspace_root):
        hints.append("已开 catalog 技能但缺触屏通路（overlay/桥 ensure_touch）")
    if "laser_beam" in skills or "bomb" in skills:
        if (
            "ensure_touch_action" not in bridge_txt
            and "ensure_touch_skill_buttons" not in bridge_txt
        ):
            hints.append("会话桥缺少 ensure_touch_*，可 refresh_ai_sandbox_bridge")
        if (
            "func ensure_touch_skill_buttons" in bridge_txt
            and "same and _touch_hud_buttons" not in bridge_txt
        ):
            hints.append(
                "会话桥可能仍每帧重建触屏按钮（点按失效、键盘仍可用）→ refresh_ai_sandbox_bridge"
            )
    if (
        genre == "shmup"
        and ship_txt
        and "_edu_skill_ui_blocks_mouse" not in ship_txt
        and "Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)" in ship_txt
    ):
        hints.append(
            "飞机鼠标跟机未加守卫，点技能键可能拖飞机 → patch_mouse_steer_guard"
        )
    return {
        "genre": genre,
        "enabled_skills": skills,
        "catalog_ids": catalog_ids,
        "has_core": core.is_dir(),
        "has_bridge": bridge.is_file(),
        "bridge_has_ensure_touch": "ensure_touch_action" in bridge_txt
        or "ensure_touch_skill_buttons" in bridge_txt,
        "touch_overlays": overlays,
        "has_touch_pathway": _workspace_has_touch_pathway(workspace_root),
        "sandbox_files": sandbox_files[:20],
        "player_ship_mouse_guard": "_edu_skill_ui_blocks_mouse" in ship_txt,
        "hints": hints,
    }


def format_diagnose_for_prompt(diag: dict[str, Any]) -> str:
    lines = ["【会话诊断·磁盘事实】"]
    lines.append(f"- genre={diag.get('genre')} skills={diag.get('enabled_skills')}")
    lines.append(
        f"- bridge={diag.get('has_bridge')} ensure_touch={diag.get('bridge_has_ensure_touch')} "
        f"touch_pathway={diag.get('has_touch_pathway')} overlays={diag.get('touch_overlays')}"
    )
    lines.append(f"- sandbox={diag.get('sandbox_files')}")
    lines.append(f"- mouse_guard={diag.get('player_ship_mouse_guard')}")
    for h in diag.get("hints") or []:
        lines.append(f"- 提示: {h}")
    return "\n".join(lines)


def _catalog_skill_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in contract.get("catalog_skills") or []:
        if isinstance(item, dict):
            sid = str(item.get("id", "")).strip()
            if sid:
                out[sid] = item
    return out


def assert_catalog_runtime(
    workspace_root: Path,
    contract: dict[str, Any],
    *,
    summary: str = "",
    how_to_play: list[str] | None = None,
) -> list[str]:
    """L1+L3：enabled catalog 技能须有 runtime 声明，且 effect/touch 可解析。

    - effect=bridge:xxx → xxx ∈ bridge_apis
    - effect=catalog:id → 玩法目录技能（契约声明即可）
    - touch 须含 overlay / ensure_touch / passive
    """
    errors: list[str] = []
    skills = _enabled_skills(workspace_root)
    if not skills:
        return errors

    catalog = _catalog_skill_map(contract)
    allowed = bridge_api_names(contract)
    has_touch = _workspace_has_touch_pathway(workspace_root)
    # L3 硬检：必须有会话 core 内 overlay 或含 ensure_touch_* 的桥/沙箱。
    # 禁止「无 core 即放行」——最小仅-config 工作区不能声称可玩技能。

    for sid in skills:
        meta = catalog.get(sid)
        if meta is None:
            continue
        runtime = meta.get("runtime")
        if not isinstance(runtime, dict) or not runtime:
            errors.append(
                f"仅 L1：catalog「{sid}」已启用但缺 runtime，不能声称可玩技能"
            )
            continue
        effect = str(runtime.get("effect", "")).strip()
        touch = str(runtime.get("touch", "")).strip()
        input_s = str(runtime.get("input", "")).strip()
        if not effect or not touch or not input_s:
            errors.append(
                f"catalog「{sid}」runtime 不完整（需 input/effect/touch）"
            )
            continue
        if effect.startswith("bridge:"):
            method = effect.split(":", 1)[1].strip()
            if method not in allowed:
                errors.append(
                    f"技能「{sid}」runtime.effect 桥方法不在契约: {method}"
                )
        elif effect.startswith("catalog:"):
            pass
        else:
            errors.append(
                f"技能「{sid}」runtime.effect 无法解析: {effect}"
            )
        touch_l = touch.lower()
        if "passive" in touch_l:
            continue
        if not (
            "overlay" in touch_l
            or "ensure_touch" in touch_l
        ):
            errors.append(
                f"技能「{sid}」runtime.touch 未声明触屏通路: {touch}"
            )
        elif not has_touch:
            errors.append(
                f"技能「{sid}」runtime 未接线：会话缺触屏 overlay / ensure_touch_action"
            )
    return list(dict.fromkeys(errors))


def assert_claims(
    workspace_root: Path,
    summary: str,
    how_to_play: list[str],
    written_paths: list[str],
    *,
    genre: str = "",
) -> list[str]:
    """声称 ⊆ 磁盘事实。口头护盾/彩色等必须有实现证据，或诚实声明「仅道具/未新加」。"""
    claim_text = summary + "\n" + "\n".join(how_to_play)
    # 诚实免责：明确说「仅道具」「未新增」「无法」等则跳过对应声称
    honest = bool(
        re.search(
            r"仅道具|未新增|没有新加|无法新增|本关没有|目录没有|诚实说明|上限|"
            r"做不到|无法实现|超出能力|没有.?Boss|无.?Boss|不能做.?Boss",
            claim_text,
            re.I,
        )
    )
    blob = _read_workspace_blob(workspace_root, written_paths)
    skills = set(_enabled_skills(workspace_root))
    blob_l = blob.lower()
    errors: list[str] = []

    for pat, label, needles in _CLAIM_RULES:
        if not pat.search(claim_text):
            continue
        # catalog skill 直接命中 enabled
        if label == "炸弹" and "bomb" in skills:
            continue
        if label == "激光" and "laser_beam" in skills:
            continue
        if label == "二段跳" and "double_jump" in skills:
            continue
        if label == "下砸" and "ground_pound" in skills:
            continue
        if honest and label in ("护盾", "彩色子弹", "Boss"):
            # 允许诚实说明上限，但不得同时吹「已加 Boss/护盾」
            if label == "Boss" and re.search(
                r"已加|新增了|触发Boss|Boss战已|加了一个Boss|出现Boss|已触发",
                claim_text,
                re.I,
            ):
                errors.append("声称已加 Boss 但又写诚实上限——请二选一并对齐磁盘")
            elif label != "Boss" and re.search(r"已加|新增了|新技能.*护盾|护盾技能", claim_text):
                errors.append(f"声称新增「{label}」但同时写了诚实上限——请二选一并对齐磁盘")
            continue
        if label == "Boss":
            has_enemy_impl = bool(
                re.search(
                    r"boss_hp|BossHP|spawn_boss|head_enemy|take_damage|"
                    r"max_hp\s*[:=]|class_name\s+\w*Boss|"
                    r"group\([\"']boss[\"']\)",
                    blob,
                    re.I,
                )
            )
            only_invincibility_disguise = bool(
                re.search(r"grant_invincibility|watch_coins|coin_streak", blob)
            ) and not has_enemy_impl
            if has_enemy_impl:
                continue
            if only_invincibility_disguise:
                errors.append(
                    "声称「Boss」但磁盘实现与需求不对齐（存在无关顶替痕迹，缺对应实体）"
                )
            else:
                errors.append(
                    "声称「Boss」但磁盘无对应实现（请在会话 core/scenes 落地所求机制）"
                )
            continue
        found = False
        for n in needles:
            if n.lower() in blob_l or n in blob or n.strip('"') in skills:
                found = True
                break
        if not found:
            errors.append(f"声称「{label}」但磁盘无对应实现（技能/桥 API/脚本）")

    if genre == "shmup" and re.search(r"护盾技能|技能.*护盾|新增.*护盾", claim_text):
        if "grant_temp_shield" not in blob and "shield" not in skills:
            if not re.search(r"仅道具|捡道具", claim_text):
                errors.append("shmup 护盾非 catalog 技能：须用 grant_temp_shield 或说明仅道具护盾")

    return list(dict.fromkeys(errors))


def emit_progress(
    workspace_root: Path | None,
    stage: str,
    detail: str = "",
    *,
    on_progress: ProgressCallback | None = None,
    log: bool = True,
) -> dict[str, Any]:
    """写入 .agent_progress.json 并可选回调；阶段名中文。"""
    title, default_detail = PROGRESS_STAGES.get(stage, (stage, detail or ""))
    payload: dict[str, Any] = {
        "stage": stage,
        "title": title,
        "detail": detail or default_detail,
    }
    if log:
        print(f"[agent] {title} · {payload['detail']}", flush=True)
    if workspace_root is not None:
        try:
            path = workspace_root / ".agent_progress.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    if on_progress is not None:
        on_progress(stage, title, str(payload["detail"]))
    return payload


def read_progress(workspace_root: Path) -> dict[str, Any]:
    path = workspace_root / ".agent_progress.json"
    if not path.is_file():
        return {"stage": "", "title": "", "detail": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"stage": "", "title": "", "detail": ""}
    except (OSError, json.JSONDecodeError):
        return {"stage": "", "title": "", "detail": ""}


def run_done_gates(
    workspace_root: Path,
    *,
    written_paths: list[str],
    summary: str,
    how_to_play: list[str],
    genre: str,
    contract: dict[str, Any],
    catalog_changed: bool = False,
    user_text: str = "",
) -> list[str]:
    """done 硬挡：返回错误列表；空列表 = 通过。"""
    errors: list[str] = []
    if not written_paths and not catalog_changed:
        errors.append("没有任何有效写入或 catalog 变更，不能 done")
    if not how_to_play:
        errors.append("how_to_play 不能为空")
    elif not any("重开" in h or "启动" in h or "重新" in h for h in how_to_play):
        errors.append("how_to_play 须提醒重开游戏后生效")
    how_blob = "\n".join(how_to_play) + "\n" + summary
    ut = (user_text or "").strip()
    is_bugfix = bool(
        re.search(
            r"消失|不显示|看不见|白屏|黑屏|没法|无法启动|打不开|闪退|报错|修复|修好|坏了|"
            r"人物.*没|角色.*没|看不到画|没有画面|没生效",
            ut,
        )
    )
    if not re.search(r"触屏|点按|按钮|屏幕下方|手指", how_blob):
        # 故障修复局允许「重开后查看」类试玩说明，不强行要技能按钮文案
        if not (
            is_bugfix
            and re.search(r"重开|启动|重新|查看|看看|是否", how_blob)
        ):
            errors.append("how_to_play 须含触屏操作说明（展厅硬性，禁止只写键盘）")

    # 本轮优先：问题/故障类原话时，禁止只复读「已加技能」类宣传
    if re.search(
        r"没法|无法|打不开|白屏|黑屏|看不到|没有画面|没生效|不行|不能用|坏了|闪退|报错|"
        r"开始游戏.*(没|不)|进不去|点了没|消失|不显示|看不见|修复",
        ut,
    ):
        promo_only = bool(
            re.search(r"已添加|已开启|已为你|已加了|已启用", summary)
        ) and not bool(
            re.search(
                r"修好|修复|恢复|启动|画面|生效|解决|原因|能开|可以玩|能进|可见|排查|显示|出现",
                summary,
            )
        )
        if promo_only or (
            re.search(r"启动|白屏|黑屏|看不到画|没有画面|消失|不显示", ut)
            and not re.search(
                r"启动|画面|白屏|黑屏|修好|修复|恢复|能开|可以|可见|显示|出现",
                summary,
            )
        ):
            errors.append(
                "本轮用户在反馈问题：summary 须直接回应本轮原话，禁止只复读更早轮次的功能宣传"
            )

    skills = set(_enabled_skills(workspace_root))
    claim_blob = summary + "\n" + "\n".join(how_to_play)
    if re.search(r"启用.{0,10}炸弹|开启.{0,10}炸弹|已为你启用了炸弹", claim_blob) and "bomb" not in skills:
        errors.append("声称启用了炸弹但 tuning.enabled_skills 中没有 bomb")
    if re.search(r"启用.{0,10}激光|开启.{0,10}激光|已为你启用了.{0,6}激光", claim_blob) and "laser_beam" not in skills:
        errors.append("声称启用了激光但 tuning.enabled_skills 中没有 laser_beam")

    for rel in written_paths:
        if not rel.endswith(".gd"):
            continue
        path = workspace_root / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        errors.extend(f"{rel}: {e}" for e in validate_gdscript(content))
        errors.extend(f"{rel}: {e}" for e in assert_apis_in_contract(content, contract))

    # 扫 ai_sandbox 全部（防漏检）
    sandbox = workspace_root / "core" / "ai_sandbox"
    if sandbox.is_dir():
        for p in sandbox.rglob("*.gd"):
            rel = p.relative_to(workspace_root).as_posix()
            if rel in written_paths:
                continue
            content = p.read_text(encoding="utf-8", errors="ignore")
            api_errs = assert_apis_in_contract(content, contract)
            syn_errs = validate_gdscript(content)
            if api_errs or syn_errs:
                errors.extend(f"{rel}: {e}" for e in syn_errs + api_errs)

    errors.extend(
        assert_claims(
            workspace_root,
            summary,
            how_to_play,
            written_paths,
            genre=genre,
        )
    )
    errors.extend(
        assert_catalog_runtime(
            workspace_root,
            contract,
            summary=summary,
            how_to_play=how_to_play,
        )
    )
    return list(dict.fromkeys(errors))


def dry_run_godot(
    workspace_root: Path,
    godot_path: str,
    *,
    timeout_sec: float = 25.0,
) -> dict[str, Any]:
    """P1：headless 冒烟；无 SCRIPT ERROR / parse error 视为通过。"""
    exe = Path(godot_path)
    if not exe.is_file():
        return {"ok": False, "skipped": True, "reason": "godot_missing", "errors": []}
    project = workspace_root / "project.godot"
    if not project.is_file():
        return {"ok": False, "skipped": True, "reason": "no_project", "errors": []}
    try:
        proc = subprocess.run(
            [
                str(exe),
                "--headless",
                "--path",
                str(workspace_root),
                "--quit-after",
                "2",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "skipped": False, "reason": str(exc), "errors": [str(exc)]}

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    errors: list[str] = []
    for line in combined.splitlines():
        low = line.lower()
        if "script error" in low or "parse error" in low or "failed to load script" in low:
            errors.append(line.strip()[:240])
        elif re.search(r"\bERROR:", line) and "script" in low:
            errors.append(line.strip()[:240])
    return {
        "ok": len(errors) == 0,
        "skipped": False,
        "reason": "",
        "errors": errors[:12],
        "exit_code": proc.returncode,
    }


def snippet_has_invented_apis(snippet: str, contract: dict[str, Any] | None = None) -> bool:
    """坏片段检测：幻想 API → 拒绝入库。"""
    if any(x in snippet for x in _GLOBAL_FORBIDDEN_APIS):
        return True
    if _BAD_COLOR_LITERALS.search(snippet):
        return True
    if contract is not None and assert_apis_in_contract(snippet, contract):
        return True
    return False
