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
# 匹配时按「整词/显式调用」——勿误伤 _merge_overrides_json 等合法实现
_GLOBAL_FORBIDDEN_APIS: tuple[str, ...] = (
    "add_method",
    "bridge.add_method",
    "ClassDB.instantiate",
    "merge_overrides",
    "patch_tuning",
    "set_color(",
    "bullet.set_color",
    'Engine.has_singleton("Bridge")',
    "Bridge.ensure_touch_skill_buttons",
)

_TRUSTED_EDU_SCRIPT_NAMES: frozenset[str] = frozenset(
    {
        "ai_sandbox_bridge.gd",
        "edu_action_bridge.gd",
        "window_chrome_overlay.gd",
    }
)

# 7.19 / 总纲 TG4：用户附加条件 → 禁止仅 enable catalog 交差
_CONDITIONAL_MECHANIC_HINTS: re.Pattern[str] = re.compile(
    r"每\s*\d+|每一|每接|每吃|每打|每击|连续\s*\d*|连击|满\s*\d+|充能|"
    r"倍速|加快|球速|速度.{0,6}(很|更)?快|三倍|更快|"
    r"反应不过|对面.{0,8}(难|慢|反应)|对手.{0,8}(难|慢)|"
    r"冷却|秒后|持续\s*\d+|倒计时|触发条件"
)


def user_text_has_conditional_mechanics(user_text: str) -> bool:
    """原话是否含触发条件/手感/数值改写（非「只要开开关」）。"""
    return bool(_CONDITIONAL_MECHANIC_HINTS.search(user_text or ""))


def _is_mechanic_code_path(rel: str) -> bool:
    """会话玩法脚本/场景（排除桥与触屏 overlay）。"""
    path = rel.replace("\\", "/").lstrip("/")
    name = Path(path).name
    if name in _TRUSTED_EDU_SCRIPT_NAMES:
        return False
    if name.endswith("_touch_overlay.gd"):
        return False
    if path.endswith((".gd", ".tscn")):
        return True
    return False


def assert_conditional_mechanics_landed(
    workspace_root: Path,
    *,
    written_paths: list[str],
    catalog_changed: bool = False,
    user_text: str = "",
    summary: str = "",
    genre: str = "",
) -> list[str]:
    """有条件原话时：必须有玩法代码/场景落地，禁止只改 enabled_skills。"""
    _ = catalog_changed
    ut: str = (user_text or "").strip()
    if not user_text_has_conditional_mechanics(ut):
        return []
    from app.services.creative.intent_router import is_drop_loot_request

    if is_drop_loot_request(ut):
        return []

    paths: list[str] = [str(p).replace("\\", "/") for p in written_paths]
    if not genre:
        # 兼容旧调用：无 genre 时任意玩法脚本即可
        if any(_is_mechanic_code_path(p) for p in paths):
            return []
        errors: list[str] = [
            "用户原话含触发条件/手感/数值（如每N次、加快、球速）："
            "请在会话 core/scenes（或 ai_sandbox）写入计数/倍率等逻辑后再 done"
        ]
        if re.search(r"已开启|已为你开启|已启用|已加了", summary or "") and not re.search(
            r"每|计数|充能|球速|加快|倍|条件|冷却|倒计时", summary or ""
        ):
            errors.append("summary 请说明条件如何落地（计数/充能/球速等）")
        return list(dict.fromkeys(errors))

    chain = CRITICAL_CHAIN_BY_GENRE.get(genre) or {}
    chain_paths = set(chain.get("paths") or [])
    hit_chain = any(p in chain_paths for p in paths)
    # 接线证据：写入内容含计数/冷却等，或命中关键路径 / ai_sandbox 新机制
    evidence = hit_chain
    cond_pat = re.compile(
        r"_count|cooldown|every|充能|倍率|% |\bmod\b|timer|streak|charge",
        re.I,
    )
    for rel in paths:
        if not _is_mechanic_code_path(rel):
            continue
        fp = workspace_root / rel
        if not fp.is_file():
            continue
        try:
            body = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if cond_pat.search(body) or rel.startswith("core/ai_sandbox/"):
            evidence = True
            break
    if evidence:
        return []

    errors = [
        "用户原话含触发条件/手感/数值（如每N次、加快、球速）："
        "请写入本品类关键玩法路径或含计数/冷却/倍率的会话脚本后再 done"
    ]
    if re.search(r"已开启|已为你开启|已启用|已加了", summary or "") and not re.search(
        r"每|计数|充能|球速|加快|倍|条件|冷却|倒计时", summary or ""
    ):
        errors.append(
            "summary 请说明条件如何落地（计数/充能/球速等）"
        )
    return list(dict.fromkeys(errors))


def _is_trusted_edu_script(rel: str) -> bool:
    """会话内从 _edu 注入的桥/触屏脚本：门禁不验其正文（模板已审）。"""
    name = Path(rel.replace("\\", "/")).name
    if name in _TRUSTED_EDU_SCRIPT_NAMES:
        return True
    return name.endswith("_touch_overlay.gd")


def _strip_gd_strings_and_comments(content: str) -> str:
    """去掉双引号/单引号字符串与 # 行注释，供括号配对粗检。"""
    no_str = re.sub(r'"(?:\\.|[^"\\])*"', '""', content)
    no_str = re.sub(r"'(?:\\.|[^'\\])*'", "''", no_str)
    lines: list[str] = []
    for line in no_str.splitlines():
        if "#" in line:
            line = line.split("#", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _contains_forbidden_api(content: str, snip: str) -> bool:
    """禁止 API 检测：带点号/括号的按字面；裸名按整词，避免 _merge_overrides_json 误伤。"""
    token = str(snip or "").strip()
    if not token:
        return False
    if "(" in token or "." in token:
        return token in content
    return (
        re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", content)
        is not None
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
            {
                "name": "get_player",
                "sig": "() -> Node",
                "desc": "兼容入口；具体玩家类型以当前品类模板为准",
            },
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
        "bridge_apis 是可选捷径（调用 bridge.xxx 时使用下列列表中的名字）；catalog 可复用也可会话另写。",
        "可写范围：会话 workspace；桥 API 以列表为准；同等效果可用会话 GDScript 实现。",
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
    lines.append("### 契约外名称（不作为可调用 API；请用会话 GDScript 实现同等效果）")
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
    structural = _strip_gd_strings_and_comments(body)
    if structural.count("(") != structural.count(")"):
        errors.append("括号不配对")
    if structural.count("{") != structural.count("}"):
        errors.append("花括号不配对")
    bad = _BAD_COLOR_LITERALS.search(body)
    if bad:
        errors.append(f"Godot 4 颜色请用大写常量，例如 Color.RED（当前为 Color.{bad.group(1)}）")
    # Python 字面量误写：GDScript 用 null/true/false（在去字符串/注释后按整词检测）
    py_lit = re.search(r"(?<![A-Za-z0-9_.])(None|True|False)(?![A-Za-z0-9_])", structural)
    if py_lit:
        repl = {"None": "null", "True": "true", "False": "false"}[py_lit.group(1)]
        errors.append(
            f"含 Python 字面量 {py_lit.group(1)}，GDScript 应写 {repl}"
        )
    for snip in _GLOBAL_FORBIDDEN_APIS:
        if _contains_forbidden_api(body, snip):
            errors.append(f"契约列表不含此 API：{snip}；请用会话 GDScript 实现同等效果")
    return errors


def assert_apis_in_contract(content: str, contract: dict[str, Any]) -> list[str]:
    """脚本中 bridge.xxx( 调用必须 ∈ 契约 bridge_apis。"""
    allowed = bridge_api_names(contract)
    forbid = {
        str(x) for x in (contract.get("forbidden_invented_apis") or _GLOBAL_FORBIDDEN_APIS)
    }
    # Node 通用方法：局部变量常叫 bridge，勿当成 Autoload 桥 API
    node_methods = {
        "has_method",
        "call",
        "get",
        "set",
        "connect",
        "disconnect",
        "is_connected",
        "emit_signal",
        "get_node",
        "get_node_or_null",
    }
    errors: list[str] = []
    for snip in forbid:
        if snip and _contains_forbidden_api(content, snip):
            errors.append(f"契约列表不含此 API：{snip}；请用会话 GDScript 实现同等效果")
    for m in _BRIDGE_CALL_RE.finditer(content):
        name = m.group(1)
        if name in node_methods:
            continue
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


# 七品类玩家关键路径（会话副本；用于健康门禁 / 可玩快照）
# scene_node：场景里操控角色节点名；group_in_scene=False 时须脚本 add_to_group("player")
# （pingpong 无独立 player.tscn，角色是 game.tscn 的 PlayerPaddle）
PLAYER_PRESENCE_BY_GENRE: dict[str, dict[str, Any]] = {
    "shmup": {
        "script": "core/player_ship.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/shmup_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": True,
    },
    "platformer": {
        "script": "core/player_platformer.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/platformer_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": True,
    },
    "parkour": {
        "script": "core/player_runner.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/parkour_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": True,
    },
    "survivor": {
        "script": "core/player_survivor.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/survivor_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": False,  # _ready 里 add_to_group("player")
    },
    "fighting": {
        "script": "core/player_fighter.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/fighting_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": True,
    },
    "racing": {
        "script": "core/car_topdown.gd",
        "scene": "scenes/player.tscn",
        "hooks": "core/racing_hooks.gd",
        "scene_node": "Player",
        "group_in_scene": True,
    },
    "pingpong": {
        "script": "core/paddle.gd",
        "scene": "scenes/game.tscn",
        "hooks": "core/pingpong_hooks.gd",
        "scene_node": "PlayerPaddle",
        "group_in_scene": False,
        "visual_tokens": ("Sprite2D", "AnimatedSprite2D", "Sprite", "Visual", "ColorRect"),
    },
}

# 兼容旧引用
PLAYER_SCRIPT_BY_GENRE: dict[str, str] = {
    g: str(cfg["script"]) for g, cfg in PLAYER_PRESENCE_BY_GENRE.items()
}
PLAYER_HOOKS_BY_GENRE: dict[str, str] = {
    g: str(cfg["hooks"]) for g, cfg in PLAYER_PRESENCE_BY_GENRE.items() if cfg.get("hooks")
}
PLAYER_SCENE_REL: str = "scenes/player.tscn"

# 臆造相对/绝对路径：Player 不在 Main 直属，开局在 GameRoot/LevelRoot 动态实例下
_BAD_PLAYER_NODE_PATH = re.compile(
    r"""get_node(?:_or_null)?\s*\(\s*["'](?:\.\./)+(?:Player|PlayerPaddle)(?:/[^"']*)?["']"""
    r"""|get_node(?:_or_null)?\s*\(\s*["']/root/Main/(?:Player|PlayerPaddle)(?:/[^"']*)?["']"""
    r"""|\$["']?(?:\.\./)+(?:Player|PlayerPaddle)"""
    r"""|\$["']?/root/Main/(?:Player|PlayerPaddle)""",
    re.I,
)
_OK_VISIBLE_FALSE_CONTEXT = re.compile(
    r"shield|overlay|label|hud|countdown|beam|laser|_ui|ui_|toast|preview|"
    r"start_screen|game_over|victory|boss_bar|help_label|level_up|visual\b",
    re.I,
)
_BAD_ROOT_MODULATE_ZERO = re.compile(
    r"""(?:self|_player|player)\.modulate(?:\.a)?\s*=\s*(?:0(?:\.0+)?|Color\s*\([^)]*0\s*\))""",
    re.I,
)
_BAD_PLAYER_QUEUE_FREE = re.compile(
    r"""(?:self|_player|player)\.queue_free\s*\(""",
    re.I,
)
_PLAYER_SCRIPT_SUFFIXES: tuple[str, ...] = (
    "player_ship.gd",
    "player_platformer.gd",
    "player_runner.gd",
    "player_survivor.gd",
    "player_fighter.gd",
    "car_topdown.gd",
    "paddle.gd",
)


def player_critical_paths(genre: str) -> list[str]:
    cfg = PLAYER_PRESENCE_BY_GENRE.get(genre)
    if not cfg:
        return []
    paths: list[str] = []
    for key in ("script", "scene", "hooks"):
        rel = cfg.get(key)
        if rel:
            paths.append(str(rel))
    return paths


def gameplay_critical_paths(genre: str) -> list[str]:
    """玩家存在 + 品类玩法关键链（球/生成器/对局等）——禁止 LLM 整写 stub。"""
    paths: list[str] = list(player_critical_paths(genre))
    known = {p.replace("\\", "/") for p in paths}
    chain = CRITICAL_CHAIN_BY_GENRE.get(genre) or {}
    for rel in list(chain.get("paths") or []) + list(
        (chain.get("must_keep_funcs") or {}).keys()
    ):
        n = str(rel).replace("\\", "/")
        if n and n not in known:
            known.add(n)
            paths.append(n)
    return paths


def assert_workspace_critical_chain(
    workspace_root: Path,
    genre: str,
) -> list[str]:
    """done 门禁：会话磁盘上关键玩法锚点须仍在（防「门禁绿但玩法链被 stub 掏空」）。"""
    return assert_critical_chain_preserved(
        "",  # unused when scanning all
        "",
        genre,
        before=None,
        workspace_root=workspace_root,
    )


def _strip_gd_comments_strings(text: str) -> str:
    """粗去注释与字符串，降低门禁误报。"""
    out = re.sub(r"#.*?$", "", text, flags=re.M)
    out = re.sub(r'"""[\s\S]*?"""', '""', out)
    out = re.sub(r"'''[\s\S]*?'''", "''", out)
    out = re.sub(r'"(?:\\.|[^"\\])*"', '""', out)
    out = re.sub(r"'(?:\\.|[^'\\])*'", "''", out)
    return out


def _scan_script_player_dangers(rel: str, text: str) -> list[str]:
    errs: list[str] = []
    if _BAD_PLAYER_NODE_PATH.search(text):
        errs.append(
            f"{rel}: 检测到相对/绝对 Main 路径找玩家；"
            "请改用 get_tree().get_nodes_in_group('player') "
            "或 AiSandboxBridge.get_player_node()"
            "（开局在 GameRoot/LevelRoot；乒乓用 $PlayerPaddle / match_controller）"
        )
    stripped = _strip_gd_comments_strings(text)
    is_player_script = rel in PLAYER_SCRIPT_BY_GENRE.values() or any(
        rel.endswith(s) for s in _PLAYER_SCRIPT_SUFFIXES
    )
    is_hooks = rel.endswith("_hooks.gd")
    if is_player_script or is_hooks:
        for line in stripped.splitlines():
            if not line.strip():
                continue
            if re.search(r"\.visible\s*=\s*false\b|^\s*visible\s*=\s*false\b", line, re.I):
                if _OK_VISIBLE_FALSE_CONTEXT.search(line):
                    continue
                if is_hooks or re.search(
                    r"(?:self|_player|player|\bp)\.visible\s*=\s*false|^\s*visible\s*=\s*false",
                    line,
                    re.I,
                ):
                    errs.append(
                        f"{rel}: 检测到玩家根 visible=false；"
                        "请保持根节点可见（护盾/UI 子节点可单独隐藏）；闪烁只改 Sprite"
                    )
                    break
        if _BAD_ROOT_MODULATE_ZERO.search(stripped):
            errs.append(
                f"{rel}: 玩家根 modulate/a 请保持可见；闪烁请成对恢复 Sprite 透明度"
            )
        if _BAD_PLAYER_QUEUE_FREE.search(stripped):
            errs.append(f"{rel}: 请保留可操控角色节点（用无敌/隐藏 Sprite，代替删除节点）")
    return errs


def _scan_player_scene(
    scene_rel: str,
    text: str,
    *,
    scene_node: str = "Player",
    group_in_scene: bool = True,
    visual_tokens: tuple[str, ...] | None = None,
    script_text: str = "",
) -> list[str]:
    errs: list[str] = []
    tokens = visual_tokens or ("Sprite2D", "AnimatedSprite2D")
    if not any(tok in text for tok in tokens):
        errs.append(
            f"{scene_rel} 须保留可视节点（{'/'.join(tokens)}），否则角色不可见"
        )
    node_pat = re.escape(scene_node)
    if not re.search(rf'\[node name="{node_pat}"', text):
        errs.append(f'{scene_rel} 须保留节点 "{scene_node}"')
    if group_in_scene:
        if not re.search(r'groups\s*=\s*\[[^\]]*["\']player["\']', text):
            errs.append(f'{scene_rel} 须保留 groups 含 "player"')
    else:
        # survivor：场景无 group，脚本必须 add_to_group
        if scene_node == "Player" and script_text:
            if 'add_to_group("player")' not in script_text and "add_to_group('player')" not in script_text:
                errs.append(
                    f'玩家脚本须保留 add_to_group("player")（{scene_rel} 无 groups 时）'
                )
    m = re.search(
        rf'\[node name="{node_pat}"[^\]]*\](.*?)(?=\n\[node |\Z)',
        text,
        re.S,
    )
    if m and re.search(r"(?m)^visible\s*=\s*false\s*$", m.group(1)):
        errs.append(
            f'{scene_rel} 的 {scene_node} 根节点检测到 visible=false；请保持可见'
        )
    return errs


def assert_player_presence_health(
    workspace_root: Path,
    genre: str,
    *,
    written_paths: list[str] | None = None,
) -> list[str]:
    """静态门禁：玩家脚本/场景仍在，且无「人消失」高危写法。

    覆盖七品类（shmup/platformer/parkour/survivor/fighting/racing/pingpong）。
    """
    cfg = PLAYER_PRESENCE_BY_GENRE.get(genre)
    if not cfg:
        return []
    errs: list[str] = []
    written = {str(p).replace("\\", "/") for p in (written_paths or [])}

    script_rel = str(cfg["script"])
    scene_rel = str(cfg["scene"])
    hooks_rel = str(cfg.get("hooks") or "")
    script_text = ""

    script_path = workspace_root / script_rel
    if not script_path.is_file():
        errs.append(f"缺少玩家脚本 {script_rel}（人物会消失/无法操控）")
    else:
        script_text = script_path.read_text(encoding="utf-8", errors="ignore")
        errs.extend(_scan_script_player_dangers(script_rel, script_text))

    scene_path = workspace_root / scene_rel
    if not scene_path.is_file():
        errs.append(f"缺少 {scene_rel}（人物无法生成）")
    else:
        visual = cfg.get("visual_tokens")
        errs.extend(
            _scan_player_scene(
                scene_rel,
                scene_path.read_text(encoding="utf-8", errors="ignore"),
                scene_node=str(cfg.get("scene_node") or "Player"),
                group_in_scene=bool(cfg.get("group_in_scene", True)),
                visual_tokens=tuple(visual) if visual else None,
                script_text=script_text,
            )
        )

    if hooks_rel:
        hooks_path = workspace_root / hooks_rel
        if hooks_path.is_file():
            errs.extend(
                _scan_script_player_dangers(
                    hooks_rel,
                    hooks_path.read_text(encoding="utf-8", errors="ignore"),
                )
            )

    for rel in sorted(written):
        if not rel.endswith(".gd"):
            continue
        if rel in (script_rel, hooks_rel):
            continue
        path = workspace_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        errs.extend(_scan_script_player_dangers(rel, text))

    return list(dict.fromkeys(errs))


def validate_player_write_content(path: str, content: str, genre: str) -> list[str]:
    """write_file 前置：拦截会毁掉玩家可见/可控的内容。"""
    rel = str(path or "").replace("\\", "/").lstrip("/")
    if not content.strip():
        return []
    errs: list[str] = []
    cfg = PLAYER_PRESENCE_BY_GENRE.get(genre) or {}
    scene_rel = str(cfg.get("scene") or PLAYER_SCENE_REL)
    if rel == scene_rel or rel == PLAYER_SCENE_REL:
        visual = cfg.get("visual_tokens")
        errs.extend(
            _scan_player_scene(
                rel,
                content,
                scene_node=str(cfg.get("scene_node") or "Player"),
                group_in_scene=bool(cfg.get("group_in_scene", True)),
                visual_tokens=tuple(visual) if visual else None,
                script_text="",
            )
        )
        # survivor 写场景时不强制 group（由脚本负责）；若误删 Sprite 仍拦
    elif rel.endswith(".gd"):
        errs.extend(_scan_script_player_dangers(rel, content))
        # 写 survivor 玩家脚本时强制保留 add_to_group
        if genre == "survivor" and rel.endswith("player_survivor.gd"):
            if 'add_to_group("player")' not in content and "add_to_group('player')" not in content:
                errs.append(f'{rel}: 须保留 add_to_group("player")')
    return list(dict.fromkeys(errs))


def save_last_playable_snapshot(workspace_root: Path, genre: str) -> bool:
    """门禁通过后保存玩家关键文件，供 salvage 从「已坏但可加载」基线救回。"""
    if genre not in PLAYER_PRESENCE_BY_GENRE:
        return False
    if assert_player_presence_health(workspace_root, genre):
        return False
    snap_root = workspace_root / ".agent" / "last_playable"
    try:
        snap_root.mkdir(parents=True, exist_ok=True)
        saved = 0
        for rel in player_critical_paths(genre):
            src = workspace_root / rel
            if not src.is_file():
                continue
            dest = snap_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            saved += 1
        meta = snap_root / "meta.json"
        meta.write_text(
            json.dumps(
                {"genre": genre, "files": player_critical_paths(genre)},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return saved > 0
    except OSError:
        return False


def restore_last_playable_snapshot(workspace_root: Path, genre: str) -> list[str]:
    """从 last_playable 恢复玩家关键文件；返回已恢复相对路径。"""
    snap_root = workspace_root / ".agent" / "last_playable"
    if not snap_root.is_dir():
        return []
    restored: list[str] = []
    for rel in player_critical_paths(genre):
        src = snap_root / rel
        if not src.is_file():
            continue
        dest = workspace_root / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            restored.append(rel)
        except OSError:
            pass
    return restored


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

    presence = PLAYER_PRESENCE_BY_GENRE.get(genre) or {}
    player_script = str(presence.get("script") or "")
    hooks_file = str(presence.get("hooks") or "")
    player_scene = str(presence.get("scene") or "")
    scene_node = str(presence.get("scene_node") or "Player")
    player_health = assert_player_presence_health(workspace_root, genre)
    if player_script:
        hints.append(
            f"玩家脚本={player_script} 场景={player_scene} 节点={scene_node} "
            f"hooks={hooks_file or '无'}；"
            "开局后多在 GameRoot/LevelRoot 下；"
            "用 group=player 或 AiSandboxBridge.get_player_node()"
            + ("；乒乓操控节点是 PlayerPaddle（scenes/game.tscn）" if genre == "pingpong" else "")
        )
    if player_health:
        hints.append("玩家健康告警: " + "；".join(player_health[:4]))

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
        "player_script": player_script,
        "player_script_exists": bool(player_script)
        and (workspace_root / player_script).is_file(),
        "player_scene": player_scene,
        "player_scene_exists": bool(player_scene)
        and (workspace_root / player_scene).is_file(),
        "hooks_file": hooks_file,
        "player_health_errors": player_health,
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
    if diag.get("player_script"):
        lines.append(
            f"- player_script={diag.get('player_script')} exists={diag.get('player_script_exists')} "
            f"scene={diag.get('player_scene_exists')} hooks={diag.get('hooks_file')}"
        )
    health = diag.get("player_health_errors") or []
    if health:
        lines.append("- player_health=FAIL: " + "；".join(str(x) for x in health[:4]))
    else:
        lines.append("- player_health=ok")
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


_DROP_BUTTON_PROMO: re.Pattern[str] = re.compile(
    r"已为你开启|点屏幕下方对应按钮|点屏幕下方「|点屏幕下方.*按钮试玩|"
    r"底部.*技能按钮|点下方对应按钮"
)
_DROP_PLAY_HINT: re.Pattern[str] = re.compile(r"捡|拾取|碰|撞|接住|掉落|掉下|飞到|吃到")


def _powerup_types_has_loot(workspace_root: Path) -> bool:
    cfg_path = workspace_root / "config" / "game_config.json"
    if not cfg_path.is_file():
        return False
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        tuning = cfg.get("tuning") if isinstance(cfg, dict) else {}
        types = tuning.get("powerup_types") if isinstance(tuning, dict) else []
        if not isinstance(types, list):
            return False
        for item in types:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower()
            if name in ("laser", "bomb", "laser_beam"):
                return True
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return False


def _apply_powerup_unlocks_loot(workspace_root: Path) -> bool:
    player = workspace_root / "core" / "player_ship.gd"
    if not player.is_file():
        return False
    try:
        text = player.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    m = re.search(r"func\s+apply_powerup[\s\S]+?(?=\nfunc\s+|\Z)", text)
    if not m:
        return False
    body = m.group(0)
    has_branch = bool(re.search(r'["\'](?:laser|bomb|laser_beam)["\']\s*:', body))
    unlocks = bool(
        re.search(r"enabled_skills|unlock|AiSandboxBridge|_unlock_catalog", body)
    )
    return has_branch and unlocks


def _sandbox_drop_loot_script(workspace_root: Path, written_paths: list[str]) -> bool:
    candidates: list[Path] = []
    for rel in written_paths:
        if "drop_loot" in rel.replace("\\", "/") or rel.endswith("drop_loot_unlock.gd"):
            candidates.append(workspace_root / rel)
    sandbox = workspace_root / "core" / "ai_sandbox"
    if sandbox.is_dir():
        candidates.extend(sandbox.glob("*drop*loot*.gd"))
    for p in candidates:
        if not p.is_file():
            continue
        try:
            chunk = p.read_text(encoding="utf-8", errors="ignore")[:12000]
        except OSError:
            continue
        if re.search(r"laser|bomb|laser_beam", chunk, re.I) and re.search(
            r"enabled_skills|apply_powerup|pickup|拾取|unlock",
            chunk,
            re.I,
        ):
            return True
    return False


def _drop_loot_impl_evidence(workspace_root: Path, written_paths: list[str]) -> bool:
    """须同时具备：掉落表含 laser/bomb + apply_powerup 拾取解锁（或等价 sandbox）。"""
    types_ok = _powerup_types_has_loot(workspace_root)
    apply_ok = _apply_powerup_unlocks_loot(workspace_root)
    if types_ok and apply_ok:
        return True
    if _sandbox_drop_loot_script(workspace_root, written_paths) and types_ok and apply_ok:
        return True
    return False


def assert_drop_loot_done(
    workspace_root: Path,
    *,
    written_paths: list[str],
    summary: str,
    how_to_play: list[str],
    catalog_changed: bool = False,
    genre: str = "",
    laser_bomb: bool = False,
) -> list[str]:
    """掉落物需求门禁。

    - 通用掉落（爱心/金币等）：禁按钮话术冒充 + 须写捡/拾取试玩说明（实现证据由通用门禁把关）。
    - 激光/炸弹掉落（laser_bomb=True）：额外要求 powerup_types 含 laser/bomb + apply_powerup 解锁，
      并保护 shmup 敌机→request_powerup 管道 / 主场景不被掏空。
    """
    errors: list[str] = []
    claim = summary + "\n" + "\n".join(how_to_play)
    if _DROP_BUTTON_PROMO.search(claim) and not _DROP_PLAY_HINT.search(claim):
        errors.append(
            "掉落物需求：summary/how_to_play 请写清「敌机掉落→拾取后才可用」"
        )
    if not _DROP_PLAY_HINT.search(claim):
        errors.append(
            "掉落物需求：how_to_play/summary 须写清「打敌机→捡掉落物」试玩步骤"
        )

    if not laser_bomb:
        # 通用掉落：不强制 laser/bomb 专用实现；实现证据交给通用 assert_claims/写盘检查
        return list(dict.fromkeys(errors))

    cfg_path = workspace_root / "config" / "game_config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            tuning = cfg.get("tuning") if isinstance(cfg, dict) else {}
            if isinstance(tuning, dict) and "powerup_types" not in tuning:
                errors.append(
                    "掉落物需求：请保留并扩展 powerup_types（在原配置上追加 laser/bomb）"
                )
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    if not _drop_loot_impl_evidence(workspace_root, written_paths):
        errors.append(
            "掉落物需求：请调用 apply_shmup_drop_loot_chain，或同时做到 "
            "powerup_types 含 laser/bomb，且 core/player_ship.gd 的 apply_powerup "
            "在拾取 laser/bomb 后写入 enabled_skills（仅改 powerup_pickup 不够）"
        )
    if catalog_changed and not _drop_loot_impl_evidence(workspace_root, written_paths):
        errors.append(
            "掉落物需求：请落地掉落→拾取逻辑（powerup_types + apply_powerup）"
        )
    # 「捡到才开」：开局不得预开 laser_beam/bomb
    pre_enabled = set(_enabled_skills(workspace_root))
    bad_pre = sorted(pre_enabled & {"laser_beam", "bomb", "laser"})
    if bad_pre:
        errors.append(
            "掉落物需求：开局 enabled_skills 勿预开 "
            + "、".join(bad_pre)
            + "（保持 []，由 apply_powerup 拾取后解锁）"
        )
    # shmup：保住敌机→request_powerup 管道，禁止 LLM 整文件掏空 spawner/主场景
    if genre == "shmup":
        spawner = workspace_root / "core" / "enemy_spawner.gd"
        if spawner.is_file():
            try:
                sp_txt = spawner.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                sp_txt = ""
            if "request_powerup" not in sp_txt:
                errors.append(
                    "掉落物需求：enemy_spawner 丢失 request_powerup（勿整文件重写 spawner）"
                )
        main_tscn = workspace_root / "scenes" / "main.tscn"
        if main_tscn.is_file():
            try:
                main_txt = main_tscn.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                main_txt = ""
            if "game_manager" not in main_txt.lower() and "GameManager" not in main_txt:
                if len(main_txt) < 400 or "EnemySpawner" not in main_txt:
                    errors.append(
                        "掉落物需求：scenes/main.tscn 疑似被掏空，请只改 powerup_types/"
                        "apply_powerup，勿重写主场景"
                    )
    return list(dict.fromkeys(errors))


# ---------------------------------------------------------------------------
# HF-14：证据验收（evidence[] · 定义 + 接线）
# ---------------------------------------------------------------------------

_WIRED_BY_PROCESS: frozenset[str] = frozenset(
    {"_process", "_physics_process", "process", "physics_process"}
)
_WIRED_BY_TIMER: frozenset[str] = frozenset({"timer", "Timer", "TIMEOUT", "timeout"})


def normalize_evidence_list(raw: Any) -> list[dict[str, Any]]:
    """把 done/self_check 的 evidence 规范成 dict 列表；非法项丢弃。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").replace("\\", "/").strip().lstrip("/")
        symbol = str(item.get("symbol") or "").strip()
        wired_raw = item.get("wired_by")
        if isinstance(wired_raw, list):
            wired_by = "|".join(
                str(x).strip() for x in wired_raw if str(x).strip()
            )
        else:
            wired_by = str(wired_raw or "").strip()
        goal = str(item.get("goal") or "").strip()
        note = str(item.get("note") or "").strip()
        missing = bool(item.get("missing")) or str(item.get("status") or "").lower() == "missing"
        caller = str(item.get("caller_path") or path).replace("\\", "/").strip().lstrip("/")
        if not path and not symbol and not missing:
            continue
        out.append(
            {
                "goal": goal,
                "path": path,
                "symbol": symbol,
                "wired_by": wired_by,
                "note": note,
                "missing": missing,
                "caller_path": caller or path,
            }
        )
    return out


def _find_symbol_kind(text: str, symbol: str) -> str | None:
    """在 GDScript 中定位符号定义类型：func / var / const / signal。"""
    if not symbol or not text:
        return None
    esc = re.escape(symbol)
    patterns: list[tuple[str, str]] = [
        ("func", rf"(?m)^\s*(?:static\s+)?func\s+{esc}\s*\("),
        ("var", rf"(?m)^\s*(?:@\w+\s+)*var\s+{esc}\b"),
        ("const", rf"(?m)^\s*const\s+{esc}\b"),
        ("signal", rf"(?m)^\s*signal\s+{esc}\b"),
    ]
    for kind, pat in patterns:
        if re.search(pat, text):
            return kind
    return None


def _extract_func_body(text: str, func_name: str) -> str | None:
    """提取 func_name 函数体（含签名行后至下一同级 func/class 前）。"""
    if not text or not func_name:
        return None
    esc = re.escape(func_name)
    m = re.search(
        rf"(?m)^(?P<indent>\t*)(?:static\s+)?func\s+{esc}\s*\([^)]*\)[^\n]*:\s*$",
        text,
    )
    if not m:
        return None
    indent = m.group("indent") or ""
    start = m.end()
    # 下一同级或更外层声明
    nxt = re.search(
        rf"(?m)^(?!{re.escape(indent)}\t){re.escape(indent)}"
        r"(?:(?:static\s+)?func\s+|class\s+|signal\s+)",
        text[start:],
    )
    end = start + nxt.start() if nxt else len(text)
    return text[m.start() : end]


def _symbol_referenced_in(body: str, symbol: str, *, as_call: bool) -> bool:
    if not body or not symbol:
        return False
    cleaned = _strip_gd_comments_strings(body)
    esc = re.escape(symbol)
    if as_call:
        return bool(re.search(rf"\b{esc}\s*\(", cleaned))
    return bool(re.search(rf"\b{esc}\b", cleaned))


_GD_IDENTIFIER_RE: re.Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_valid_evidence_symbol(symbol: str) -> bool:
    if not symbol or not _GD_IDENTIFIER_RE.match(symbol):
        return False
    if symbol in ("func", "var", "const", "signal", "class", "extends"):
        return False
    return True


def _parse_wired_by_candidates(wired_by: str) -> tuple[list[str], list[str]]:
    """拆分多 caller；含 '/' 的散文串视为格式错误。"""
    raw = (wired_by or "").strip()
    if not raw:
        return [], []
    if "/" in raw:
        return [], [
            "evidence wired_by 含 '/' 请拆成多条 evidence 或使用 A|B 分隔多个调用方"
        ]
    if "|" in raw:
        parts = raw.split("|")
    elif "," in raw:
        parts = raw.split(",")
    else:
        parts = [raw]
    return [p.strip() for p in parts if p.strip()], []


def _find_called_funcs_in_body(body: str) -> list[str]:
    cleaned = _strip_gd_comments_strings(body or "")
    names = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", cleaned)
    skip = {
        "if",
        "elif",
        "while",
        "for",
        "match",
        "assert",
        "print",
        "push_warning",
        "push_error",
        "max",
        "min",
        "clamp",
        "lerp",
    }
    out: list[str] = []
    for n in names:
        if n not in skip and n not in out:
            out.append(n)
    return out


def _symbol_wired_via_caller(
    caller_text: str,
    caller_name: str,
    symbol: str,
    *,
    as_call: bool,
    max_hops: int = 2,
) -> bool:
    body = _extract_func_body(caller_text, caller_name)
    if body is None:
        return False
    if _symbol_referenced_in(body, symbol, as_call=as_call):
        return True
    if max_hops <= 0:
        return False
    for callee in _find_called_funcs_in_body(body):
        if _symbol_wired_via_caller(
            caller_text,
            callee,
            symbol,
            as_call=as_call,
            max_hops=max_hops - 1,
        ):
            return True
    return False


def _check_process_hook_wired(
    caller_text: str,
    caller_rel: str,
    symbol: str,
    *,
    hook: str,
    as_call: bool,
    label: str,
) -> list[str]:
    body = _extract_func_body(caller_text, hook)
    if body is None:
        return [
            f"evidence 接线失败：{caller_rel} 无 {hook}（symbol={symbol}，{label}）"
        ]
    if _symbol_referenced_in(body, symbol, as_call=as_call):
        return []
    if _symbol_wired_via_caller(
        caller_text, hook, symbol, as_call=as_call, max_hops=2
    ):
        return []
    return [
        f"evidence 接线失败：{hook} 路径内未调用/引用 {symbol}@"
        f"{caller_rel}（{label}）"
    ]


def _check_timer_wired(
    caller_text: str,
    caller_rel: str,
    symbol: str,
    *,
    as_call: bool,
    label: str,
) -> list[str]:
    cleaned = _strip_gd_comments_strings(caller_text)
    has_timer = bool(re.search(r"\bTimer\b|timeout|\.connect\s*\(", cleaned, re.I))
    if not has_timer:
        return [
            f"evidence 接线失败：声明 Timer 但 {caller_rel} 未见 Timer/connect"
            f"（{label}）"
        ]
    if _symbol_referenced_in(cleaned, symbol, as_call=as_call):
        return []
    return [f"evidence 接线失败：Timer 路径下未见 {symbol}（{label}）"]


def _check_one_wired_by_candidate(
    caller_text: str,
    caller_rel: str,
    symbol: str,
    candidate: str,
    *,
    as_call: bool,
    label: str,
) -> list[str]:
    wb_key = candidate.strip()
    wb_norm = wb_key.lstrip("_")
    if wb_key in _WIRED_BY_PROCESS or f"_{wb_norm}" in _WIRED_BY_PROCESS or wb_norm in {
        "process",
        "physics_process",
    }:
        hook = wb_key if wb_key.startswith("_") else f"_{wb_norm}"
        if hook not in ("_process", "_physics_process"):
            hook = "_process" if "physics" not in hook else "_physics_process"
        return _check_process_hook_wired(
            caller_text,
            caller_rel,
            symbol,
            hook=hook,
            as_call=as_call,
            label=label,
        )
    if wb_key in _WIRED_BY_TIMER or wb_norm.lower() == "timer":
        return _check_timer_wired(
            caller_text, caller_rel, symbol, as_call=as_call, label=label
        )
    if _symbol_wired_via_caller(
        caller_text, wb_key, symbol, as_call=as_call, max_hops=2
    ):
        return []
    cleaned = _strip_gd_comments_strings(caller_text)
    if "connect(" in cleaned and _symbol_referenced_in(
        cleaned, symbol, as_call=as_call
    ):
        return []
    return [
        f"evidence 接线失败：{wb_key} 路径内未调用/引用 {symbol}"
        f"（{caller_rel}，{label}）"
    ]


def _assert_one_evidence_wired(
    workspace_root: Path,
    item: dict[str, Any],
) -> list[str]:
    """核对单条 evidence：定义存在 + wired_by 调用接到位。"""
    errs: list[str] = []
    goal = str(item.get("goal") or "")
    label = goal or str(item.get("symbol") or item.get("path") or "evidence")
    if item.get("missing"):
        errs.append(f"evidence 标明 missing，不得 done：{label}")
        return errs

    path = str(item.get("path") or "").replace("\\", "/").strip()
    symbol = str(item.get("symbol") or "").strip()
    wired_by = str(item.get("wired_by") or "").strip()
    caller_rel = str(item.get("caller_path") or path).replace("\\", "/").strip()

    # HF-15.1 H1：非法 evidence 形状
    if path.lower().endswith((".tscn", ".tres")):
        errs.append(
            f"evidence 不可用场景路径当 symbol：请改为 .gd 中的 func/var…（{label}）"
        )
        return errs
    if "->" in wired_by or re.search(r"\.gd\s*->", wired_by):
        errs.append(
            f"wired_by 须为函数名或 A|B，禁止箭头链（{label}）"
        )
        return errs

    if not path or not symbol:
        errs.append(f"evidence 缺 path/symbol：{label}")
        return errs

    if not _is_valid_evidence_symbol(symbol):
        errs.append(
            f"evidence symbol 须为单个标识符，请拆成多条 evidence："
            f"{symbol}（{label}）"
        )
        return errs

    def_path = workspace_root / path
    if not def_path.is_file():
        errs.append(f"evidence 路径不存在：{path}（{label}）")
        return errs
    try:
        def_text = def_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        errs.append(f"evidence 无法读取：{path}（{label}）")
        return errs

    kind = _find_symbol_kind(def_text, symbol)
    if kind is None:
        errs.append(
            f"evidence 符号未定义：{symbol} @ {path}（{label}）；"
            "须为 func/var/const/signal"
        )
        return errs

    if not wired_by:
        return errs

    candidates, fmt_errs = _parse_wired_by_candidates(wired_by)
    if fmt_errs:
        return [f"{fmt_errs[0]}（{label}）"]
    if not candidates:
        return errs

    caller_path = workspace_root / caller_rel
    if not caller_path.is_file():
        errs.append(f"evidence 调用方路径不存在：{caller_rel}（{label}）")
        return errs
    try:
        caller_text = caller_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        errs.append(f"evidence 无法读取调用方：{caller_rel}（{label}）")
        return errs

    as_call = kind == "func"
    per_cand: list[list[str]] = []
    for cand in candidates:
        per_cand.append(
            _check_one_wired_by_candidate(
                caller_text,
                caller_rel,
                symbol,
                cand,
                as_call=as_call,
                label=label,
            )
        )
    if any(not e for e in per_cand):
        return errs
    # 全部 candidate 失败：回灌第一条谓词原文
    for e in per_cand:
        if e:
            errs.extend(e)
            break
    return errs


def _symbol_existed_at_turn_start(
    pre_turn_snapshot: dict[str, bytes | None],
    path: str,
    symbol: str,
) -> bool:
    """回合初 snapshot 中该 path 是否已定义 symbol（HF-15.1 H2）。"""
    rel = path.replace("\\", "/").strip()
    snap = pre_turn_snapshot.get(rel)
    if snap is None:
        return False
    text = snap.decode("utf-8", errors="ignore")
    return _find_symbol_kind(text, symbol) is not None


def assert_evidence_wired(
    workspace_root: Path,
    evidence: list[dict[str, Any]] | None,
    *,
    goals: list[str] | None = None,
    require: bool = False,
    written_paths: list[str] | None = None,
    pre_turn_snapshot: dict[str, bytes | None] | None = None,
) -> list[str]:
    """HF-14：核对 evidence[] ⊆ 磁盘（定义 + wired_by 接线）。

    - require=False 且 evidence 空：跳过（兼容旧调用方）
    - require=True 且 evidence 空：gate_error
    - 任一条 missing / 缺定义 / 未接线 → 错误
    - HF-15.1：新符号须本轮 written_paths 写入（见 pre_turn_snapshot）
    """
    items = normalize_evidence_list(evidence)
    errors: list[str] = []
    if require and not items:
        errors.append(
            "done 须提交 evidence[]：每条含 path/symbol/wired_by"
            "（周期机制须声明接到 _process/_physics_process/Timer）"
        )
        return errors
    if not items:
        return []

    for item in items:
        errors.extend(_assert_one_evidence_wired(workspace_root, item))

    written_set = {
        str(p).replace("\\", "/").strip()
        for p in (written_paths or [])
        if str(p).strip()
    }
    if require and written_set and pre_turn_snapshot is not None:
        for item in items:
            if item.get("missing"):
                continue
            path = str(item.get("path") or "").replace("\\", "/").strip()
            symbol = str(item.get("symbol") or "").strip()
            if not path or not symbol:
                continue
            if _symbol_existed_at_turn_start(pre_turn_snapshot, path, symbol):
                continue
            label = str(item.get("goal") or symbol or path)
            if path not in written_set:
                errors.append(
                    f"evidence 新符号须本轮写入 {path}："
                    f"{symbol} 回合初不存在且 path 未出现在 written_paths（{label}）"
                )

    goal_list = [str(g).strip() for g in (goals or []) if str(g).strip()]
    if require and goal_list and len(items) < 1:
        errors.append("goals 非空时 evidence 不能为空")
    return list(dict.fromkeys(errors))


# ---------------------------------------------------------------------------
# HF-15.1：同错早停键 · replace 观测 symbols_added
# ---------------------------------------------------------------------------

_SYMBOLS_ADDED_RE: re.Pattern[str] = re.compile(
    r"(?m)^\s*(?:static\s+)?func\s+(\w+)"
)


def extract_symbols_added_from_gd(text: str, *, limit: int = 20) -> list[str]:
    """从 GDScript 片段提取 func 名（HF-15.1 H4）。"""
    out: list[str] = []
    for name in _SYMBOLS_ADDED_RE.findall(text or ""):
        if name not in out:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def _normalize_one_gate_error_key(err: str) -> str:
    e = str(err).strip()
    if not e:
        return ""
    sym_m = re.search(r"符号未定义：(\w+)\s*@\s*([^\s（]+)", e)
    if sym_m:
        return f"symbol_undefined:{sym_m.group(1)}@{sym_m.group(2)}"
    if "新符号须本轮写入" in e:
        sym_m2 = re.search(r"：(\w+)\s", e)
        path_m = re.search(r"写入\s+([^\s：]+)", e)
        if sym_m2 and path_m:
            return f"new_symbol_not_written:{sym_m2.group(1)}@{path_m.group(1)}"
    if "wired_by 含 '/'" in e or "箭头链" in e or "wired_by 须为函数名" in e:
        return "wired_by_format"
    if "不可用场景路径" in e:
        return "tscn_path_symbol"
    if "接线失败" in e and "symbol=" in e:
        return re.sub(r"[\s，。；：\"'（）]+", "", e[:100])
    return re.sub(r"[\s，。；：\"'（）]+", "", e[:120])[:80]


def normalize_gate_error_keys(errors: list[str]) -> frozenset[str]:
    """门禁失败信息 → 归一化键集合（HF-15.1 H3）。"""
    keys: list[str] = []
    for err in errors:
        key = _normalize_one_gate_error_key(err)
        if key:
            keys.append(key)
    return frozenset(keys)


def gate_error_key_sets_similar(
    left: frozenset[str],
    right: frozenset[str],
) -> bool:
    """连续失败是否视为「同错」（Jaccard ≥ 0.8）。"""
    if not left or not right:
        return False
    if left == right:
        return True
    inter = len(left & right)
    union = len(left | right)
    return union > 0 and (inter / union) >= 0.8


def update_gate_error_streak(
    streak: int,
    last_keys: frozenset[str],
    errors: list[str],
) -> tuple[int, frozenset[str]]:
    """更新同错连击计数；返回 (新 streak, 本轮键)。"""
    keys = normalize_gate_error_keys(errors)
    if not keys:
        return streak, last_keys
    if last_keys and gate_error_key_sets_similar(last_keys, keys):
        return streak + 1, keys
    return 1, keys


# ---------------------------------------------------------------------------
# HF-15：L2 表现谓词（进度条 · 图标可见）
# ---------------------------------------------------------------------------

_L2_PROGRESS_TRIGGERS: tuple[str, ...] = (
    "进度条",
    "冷却条",
    "充能条",
    "ProgressBar",
)
_L2_ICON_TRIGGERS: tuple[str, ...] = (
    "图标",
    "命数图标",
    "血量图标",
    "生命图标",
    "LivesDisplay",
)
_L2_ICON_NODE_NAME: re.Pattern[str] = re.compile(r"(?i)(life|icon|lives)")
_PROGRESS_BAR_TYPES: frozenset[str] = frozenset({"ProgressBar", "TextureProgressBar"})
_PROGRESS_VALUE_WRITE: re.Pattern[str] = re.compile(
    r"\.(?:value|ratio)\s*[\+\-\*/]?=|\.set_value\s*\(",
    re.I,
)


def _l2_trigger_blob(
    goals: list[str] | None,
    user_text: str = "",
) -> str:
    parts = [str(g).strip() for g in (goals or []) if str(g).strip()]
    parts.append((user_text or "").strip())
    return "\n".join(parts)


def l2_presentation_triggers_hit(
    goals: list[str] | None,
    user_text: str = "",
) -> tuple[bool, bool]:
    blob = _l2_trigger_blob(goals, user_text)
    progress = any(t in blob for t in _L2_PROGRESS_TRIGGERS)
    icon = any(t in blob for t in _L2_ICON_TRIGGERS)
    return progress, icon


def _iter_workspace_gd_scripts(workspace_root: Path) -> list[Path]:
    out: list[Path] = []
    for sub in ("core", "scenes"):
        base = workspace_root / sub
        if base.is_dir():
            out.extend(sorted(base.rglob("*.gd")))
    return out


def _iter_workspace_tscn(workspace_root: Path) -> list[Path]:
    out: list[Path] = []
    scenes = workspace_root / "scenes"
    if scenes.is_dir():
        out.extend(sorted(scenes.rglob("*.tscn")))
    core = workspace_root / "core"
    if core.is_dir():
        out.extend(sorted(core.rglob("*.tscn")))
    return out


def _scan_tscn_progress_bars(text: str, rel: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(
        r'\[node name="([^"]+)" type="(ProgressBar|TextureProgressBar)"',
        text,
    ):
        found.append(f"{rel}:{m.group(1)}")
    return found


def _scan_tscn_icon_nodes(text: str, rel: str) -> list[tuple[str, bool]]:
    """返回 (node_id, has_texture_in_scene)。"""
    nodes: list[tuple[str, bool]] = []
    for m in re.finditer(
        r'\[node name="([^"]+)" type="TextureRect"[^\]]*\](.*?)(?=\n\[node |\Z)',
        text,
        re.S,
    ):
        name = m.group(1)
        if not _L2_ICON_NODE_NAME.search(name):
            continue
        section = m.group(0)
        has_tex = bool(re.search(r"(?m)^texture\s*=", section))
        nodes.append((f"{rel}:{name}", has_tex))
    return nodes


def _body_writes_progress_value(body: str) -> bool:
    cleaned = _strip_gd_comments_strings(body or "")
    return bool(_PROGRESS_VALUE_WRITE.search(cleaned))


def _gd_has_progress_value_in_runtime(text: str) -> bool:
    for hook in ("_process", "_physics_process"):
        body = _extract_func_body(text, hook)
        if body is None:
            continue
        if _body_writes_progress_value(body):
            return True
        for callee in _find_called_funcs_in_body(body):
            cb = _extract_func_body(text, callee)
            if cb and _body_writes_progress_value(cb):
                return True
            for cc in _find_called_funcs_in_body(cb or ""):
                cb2 = _extract_func_body(text, cc)
                if cb2 and _body_writes_progress_value(cb2):
                    return True
    cleaned = _strip_gd_comments_strings(text)
    if re.search(r"\bTimer\b|timeout|\.connect\s*\(", cleaned, re.I):
        for m in re.finditer(
            r"(?m)^(?P<ind>\t*)(?:static\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            text,
        ):
            fname = m.group(2)
            if fname.startswith("_on_") or "timeout" in fname.lower():
                fb = _extract_func_body(text, fname)
                if fb and _body_writes_progress_value(fb):
                    return True
    return False


def _script_covers_icon_node(text: str, node_name: str) -> bool:
    cleaned = _strip_gd_comments_strings(text or "")
    esc = re.escape(node_name)
    if re.search(r"\.texture\s*=", cleaned):
        if (
            node_name in text
            or re.search(rf'["\']{esc}["\']', text)
            or re.search(rf"get_node(?:_or_null)?\s*\([^)]*{esc}", text, re.I)
        ):
            return True
    if re.search(
        r"custom_minimum_size\s*=\s*Vector2\s*\(\s*[^0]",
        cleaned,
    ) and re.search(rf"{esc}|Icon|Life", text, re.I):
        if re.search(
            r"\.modulate\s*=\s*(?!Color\s*\(\s*1,\s*1,\s*1,\s*0\s*\))",
            cleaned,
        ):
            return True
    return False


def _workspace_icon_visibility_ok(
    workspace_root: Path,
    icon_nodes: list[tuple[str, bool]],
) -> tuple[bool, str]:
    if not icon_nodes:
        return True, ""
    scripts_text = ""
    for p in _iter_workspace_gd_scripts(workspace_root):
        try:
            scripts_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except OSError:
            continue
    for node_id, has_tex in icon_nodes:
        short = node_id.split(":")[-1]
        if has_tex:
            continue
        if _script_covers_icon_node(scripts_text, short):
            continue
        return (
            False,
            f"L2 图标可见失败：{short} 无 texture 且无占位路径",
        )
    return True, ""


def assert_presentation_predicates(
    workspace_root: Path,
    *,
    goals: list[str] | None = None,
    user_text: str = "",
) -> list[str]:
    """HF-15 L2：goals/原话命中高置信词时，核对 UI 可见/驱动谓词。"""
    want_progress, want_icon = l2_presentation_triggers_hit(goals, user_text)
    if not want_progress and not want_icon:
        return []

    errors: list[str] = []

    if want_progress:
        bar_nodes: list[str] = []
        for tscn in _iter_workspace_tscn(workspace_root):
            try:
                txt = tscn.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = tscn.relative_to(workspace_root).as_posix()
            bar_nodes.extend(_scan_tscn_progress_bars(txt, rel))
        if bar_nodes:
            has_write = False
            for gd in _iter_workspace_gd_scripts(workspace_root):
                try:
                    gtxt = gd.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if _gd_has_progress_value_in_runtime(gtxt):
                    has_write = True
                    break
            if not has_write:
                errors.append(
                    "L2 进度条失败：场景有 "
                    + "、".join(bar_nodes[:3])
                    + " 但脚本未见 _process/_physics_process/Timer 路径对 "
                    ".value/.ratio 的写入"
                )
        else:
            errors.append(
                "L2 进度条失败：goals 含进度条/冷却条但场景未见 "
                "ProgressBar/TextureProgressBar 节点"
            )

    if want_icon:
        icon_nodes: list[tuple[str, bool]] = []
        for tscn in _iter_workspace_tscn(workspace_root):
            try:
                txt = tscn.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = tscn.relative_to(workspace_root).as_posix()
            icon_nodes.extend(_scan_tscn_icon_nodes(txt, rel))
        if icon_nodes:
            ok, msg = _workspace_icon_visibility_ok(workspace_root, icon_nodes)
            if not ok and msg:
                errors.append(msg)
        # 无 icon 节点时不误杀（宁漏勿杀）

    return list(dict.fromkeys(errors))


def _code_fingerprint(text: str) -> str:
    """去注释/字符串/空白后的指纹，用于反馈轮「真 diff」判断。"""
    cleaned = _strip_gd_comments_strings(text or "")
    return re.sub(r"\s+", "", cleaned)


def summaries_near_duplicate(a: str, b: str, *, threshold: float = 0.82) -> bool:
    """启发式：两段 summary 是否近亲复读。"""
    from difflib import SequenceMatcher

    sa = re.sub(r"\s+", "", (a or "").strip())
    sb = re.sub(r"\s+", "", (b or "").strip())
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    if len(sa) >= 12 and (sa in sb or sb in sa):
        return True
    return SequenceMatcher(None, sa, sb).ratio() >= threshold


def assert_feedback_has_real_diff(
    workspace_root: Path,
    *,
    written_paths: list[str],
    pre_turn_snapshot: dict[str, bytes | None],
    summary: str,
    previous_summary: str,
) -> list[str]:
    """HF-14 S3：反馈轮须有真代码 diff；禁近亲 summary 空转交差。"""
    errors: list[str] = []
    real_change = False
    checked_any = False
    for rel in written_paths:
        rel_n = str(rel).replace("\\", "/").strip()
        if not rel_n.endswith((".gd", ".tscn", ".json")):
            continue
        if rel_n not in pre_turn_snapshot:
            # 本轮新建
            path = workspace_root / rel_n
            if path.is_file():
                real_change = True
                break
            continue
        checked_any = True
        before_b = pre_turn_snapshot.get(rel_n)
        path = workspace_root / rel_n
        if not path.is_file():
            if before_b is not None:
                real_change = True
                break
            continue
        try:
            after = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        before = "" if before_b is None else before_b.decode("utf-8", errors="ignore")
        if _code_fingerprint(before) != _code_fingerprint(after):
            real_change = True
            break

    if not written_paths:
        errors.append(
            "反馈轮无磁盘写入：请先 read 上轮改动再 replace_text 最小 patch，"
            "勿只改 summary"
        )
    elif not real_change and (checked_any or written_paths):
        errors.append(
            "反馈轮相对上轮无真代码 diff（仅空白/注释不算）："
            "请对照用户原话补接线或逻辑后再 done"
        )

    if previous_summary.strip() and summaries_near_duplicate(summary, previous_summary):
        if not real_change:
            errors.append(
                "反馈轮 summary 与上轮近亲复读且无新写入：请说明本轮实际补了什么"
            )
    return list(dict.fromkeys(errors))


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
    evidence: list[dict[str, Any]] | None = None,
    require_evidence: bool = False,
    goals: list[str] | None = None,
    pre_turn_snapshot: dict[str, bytes | None] | None = None,
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
    # 延迟导入，避免与 intent_router 循环依赖
    from app.services.creative.intent_router import (
        is_drop_loot_request,
        is_laser_bomb_drop_request,
    )

    drop_loot = is_drop_loot_request(ut)
    laser_bomb_drop = is_laser_bomb_drop_request(ut)
    is_bugfix = bool(
        re.search(
            r"消失|不显示|看不见|白屏|黑屏|没法|无法启动|打不开|闪退|报错|修复|修好|坏了|"
            r"人物.*没|角色.*没|看不到画|没有画面|没生效",
            ut,
        )
    )
    # 触屏可玩：按钮技能要点按；被动/位移类机制（碰到/穿过/踩/接住…）也是触屏拖动操控角色达成
    touch_ok = bool(
        re.search(
            r"触屏|点按|按钮|屏幕下方|手指|碰到|碰|撞|穿过|踩|接住|走到|移动|拖动|靠近|吃到|捡",
            how_blob,
        )
    )
    if drop_loot and _DROP_PLAY_HINT.search(how_blob):
        touch_ok = True
    if not touch_ok:
        # 故障修复局允许「重开后查看」类试玩说明，不强行要技能按钮文案
        if not (
            is_bugfix
            and re.search(r"重开|启动|重新|查看|看看|是否", how_blob)
        ):
            errors.append(
                "how_to_play 请含触屏可玩操作（点按/拖动/碰到等）"
            )
    if drop_loot:
        errors.extend(
            assert_drop_loot_done(
                workspace_root,
                written_paths=written_paths,
                summary=summary,
                how_to_play=how_to_play,
                catalog_changed=catalog_changed,
                genre=genre,
                laser_bomb=laser_bomb_drop,
            )
        )

    # 总纲 TG4 / 7.19：带条件的需求禁止仅 enable 交差
    errors.extend(
        assert_conditional_mechanics_landed(
            workspace_root,
            written_paths=written_paths,
            catalog_changed=catalog_changed,
            user_text=ut,
            summary=summary,
            genre=genre,
        )
    )

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
                "本轮用户在反馈问题：summary 请直接回应本轮原话（修好了什么 / 如何再试）"
            )

    # 掉落才开：summary 常写「捡到后开启」，不得逼 LLM 把 laser/bomb 预开进 enabled_skills
    skills = set(_enabled_skills(workspace_root))
    claim_blob = summary + "\n" + "\n".join(how_to_play)
    if not drop_loot:
        if (
            re.search(r"启用.{0,10}炸弹|开启.{0,10}炸弹|已为你启用了炸弹", claim_blob)
            and "bomb" not in skills
        ):
            errors.append("声称启用了炸弹但 tuning.enabled_skills 中没有 bomb")
        if (
            re.search(
                r"启用.{0,10}激光|开启.{0,10}激光|已为你启用了.{0,6}激光",
                claim_blob,
            )
            and "laser_beam" not in skills
        ):
            errors.append("声称启用了激光但 tuning.enabled_skills 中没有 laser_beam")

    for rel in written_paths:
        if not rel.endswith(".gd"):
            continue
        if _is_trusted_edu_script(rel):
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
    # HF-10：玩家可见/可控静态门禁（shmup/platformer/parkour）
    errors.extend(
        assert_player_presence_health(
            workspace_root,
            genre,
            written_paths=written_paths,
        )
    )
    # HF-12：关键玩法链须仍在磁盘（防 stub 整写后门禁仍绿）
    errors.extend(assert_workspace_critical_chain(workspace_root, genre))
    # HF-14：evidence 定义 + 接线（require 由 Agent done 打开；旧调用方默认跳过）
    errors.extend(
        assert_evidence_wired(
            workspace_root,
            evidence,
            goals=goals,
            require=require_evidence,
            written_paths=written_paths,
            pre_turn_snapshot=pre_turn_snapshot,
        )
    )
    errors.extend(
        assert_presentation_predicates(
            workspace_root,
            goals=goals,
            user_text=ut,
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
    lines = combined.splitlines()
    errors: list[str] = []
    # 命中这些即视为加载/运行错误（含破坏场景接线、丢节点等运行时错，不只脚本解析）
    _err_needle = re.compile(
        r"script error|parse error|failed to load|"
        r"node not found|invalid access|invalid call|invalid get index|"
        r"nonexistent function|already connected|"
        r"could not (?:resolve|preload)|non-existent resource|invalid parameter",
        re.I,
    )
    for i, line in enumerate(lines):
        if _err_needle.search(line):
            msg = line.strip()[:240]
            # 追加紧跟的定位行「   at: func (res://xxx.gd:NN)」，让 LLM 精确定位
            for j in (i + 1, i + 2):
                if j < len(lines) and re.search(r"\bat:\s", lines[j]) and "res://" in lines[j]:
                    msg += " | " + lines[j].strip()[:160]
                    break
            errors.append(msg)
        elif re.search(r"\bERROR:", line) and ("res://" in line or "script" in line.lower()):
            errors.append(line.strip()[:240])
    # 去重保序
    errors = list(dict.fromkeys(errors))
    return {
        "ok": len(errors) == 0,
        "skipped": False,
        "reason": "",
        "errors": errors[:12],
        "exit_code": proc.returncode,
    }


def snippet_has_invented_apis(snippet: str, contract: dict[str, Any] | None = None) -> bool:
    """坏片段检测：幻想 API → 拒绝入库。"""
    if any(_contains_forbidden_api(snippet, x) for x in _GLOBAL_FORBIDDEN_APIS):
        return True
    if _BAD_COLOR_LITERALS.search(snippet):
        return True
    if contract is not None and assert_apis_in_contract(snippet, contract):
        return True
    return False


# ---------------------------------------------------------------------------
# HF-12：Diff / 函数 / 信号 / 关键玩法链保真
# ---------------------------------------------------------------------------

_GD_FUNC_RE: re.Pattern[str] = re.compile(
    r"(?m)^func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([^\n:]+))?\s*:"
)
_GD_SIGNAL_RE: re.Pattern[str] = re.compile(r"(?m)^signal\s+([A-Za-z_][A-Za-z0-9_]*)")
_GD_EXTENDS_RE: re.Pattern[str] = re.compile(r"(?m)^extends\s+(\S+)")
_GD_CLASS_RE: re.Pattern[str] = re.compile(r"(?m)^class_name\s+(\S+)")
_GD_EXPORT_RE: re.Pattern[str] = re.compile(
    r"(?m)^@export(?:_[A-Za-z0-9_]+)?\s+var\s+([A-Za-z_][A-Za-z0-9_]*)"
)
_GD_ONREADY_RE: re.Pattern[str] = re.compile(
    r"(?m)^@onready\s+var\s+([A-Za-z_][A-Za-z0-9_]*)"
)
_TSCN_NODE_RE: re.Pattern[str] = re.compile(
    r'(?m)^\[node name="([^"]+)"[^\]]*\]'
)
_TSCN_SCRIPT_RE: re.Pattern[str] = re.compile(
    r'(?m)^script\s*=\s*ExtResource\("([^"]+)"\)'
)

# 七品类关键玩法链锚点（门禁材料，非 Intent 特例）
CRITICAL_CHAIN_BY_GENRE: dict[str, dict[str, Any]] = {
    "platformer": {
        "paths": [
            "core/player_platformer.gd",
            "core/game_manager.gd",
            "scenes/level_01.tscn",
        ],
        "must_keep_funcs": {
            "core/player_platformer.gd": [
                "_physics_process",
                "notify_hazard",
                "_try_stomp_enemy",
            ],
        },
        "must_keep_tokens": {
            "scenes/player.tscn": ['groups=["player"]'],
        },
    },
    "shmup": {
        "paths": [
            "core/player_ship.gd",
            "core/enemy_spawner.gd",
            "core/bullet.gd",
        ],
        "must_keep_funcs": {
            "core/player_ship.gd": [
                "_physics_process",
                "apply_powerup",
                "_fire_bullet",
            ],
        },
        "must_keep_signals": {
            "core/enemy_spawner.gd": ["request_powerup"],
        },
        "must_keep_tokens": {
            "core/player_ship.gd": ["func apply_powerup"],
        },
    },
    "parkour": {
        "paths": ["core/player_runner.gd"],
        "must_keep_funcs": {
            "core/player_runner.gd": [
                "_physics_process",
                "set_playing",
            ],
        },
        "must_keep_tokens": {
            "core/player_runner.gd": ["_playing"],
        },
    },
    "survivor": {
        "paths": ["core/player_survivor.gd", "core/auto_weapon.gd"],
        "must_keep_funcs": {
            "core/player_survivor.gd": ["_physics_process"],
        },
        "must_keep_tokens": {
            "core/player_survivor.gd": ['add_to_group("player")'],
        },
    },
    "fighting": {
        "paths": ["core/fighter.gd", "core/player_fighter.gd"],
        "must_keep_funcs": {
            "core/fighter.gd": ["_physics_process", "apply_hurt", "try_light_attack"],
        },
        "must_keep_tokens": {},
    },
    "racing": {
        "paths": ["core/car_topdown.gd", "core/lap_counter.gd"],
        "must_keep_funcs": {
            "core/car_topdown.gd": ["_process", "setup_playing"],
        },
        "must_keep_tokens": {},
    },
    "pingpong": {
        "paths": [
            "core/ball.gd",
            "core/paddle.gd",
            "core/match_controller.gd",
            "scenes/game.tscn",
        ],
        "must_keep_funcs": {
            "core/ball.gd": [
                "_try_paddle_bounce",
                "_apply_paddle_bounce",
                "_check_scoring",
                "reset_to_center",
                "halt",
            ],
            "core/paddle.gd": [
                "_physics_process",
                "configure_bounds",
                "get_hit_rect",
            ],
            "core/match_controller.gd": [
                "setup",
                "_start_rally",
                "_on_ball_scored",
            ],
        },
        "must_keep_tokens": {
            "scenes/game.tscn": ["PlayerPaddle"],
            "core/ball.gd": ["signal scored"],
        },
    },
}


_DEFAULT_MAX_CHANGED_RATIO: float = 0.20


def parse_gdscript_structure(content: str) -> dict[str, Any]:
    """提取 .gd 结构快照：extends/class/signal/export/onready/函数签名与正文。"""
    text = content or ""
    funcs: dict[str, dict[str, str]] = {}
    matches = list(_GD_FUNC_RE.finditer(text))
    for i, m in enumerate(matches):
        name = m.group(1)
        sig = m.group(0).split(":", 1)[0].strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        funcs[name] = {"sig": sig, "body": body}
    extends_m = _GD_EXTENDS_RE.search(text)
    class_m = _GD_CLASS_RE.search(text)
    return {
        "extends": extends_m.group(1) if extends_m else "",
        "class_name": class_m.group(1) if class_m else "",
        "signals": _GD_SIGNAL_RE.findall(text),
        "exports": _GD_EXPORT_RE.findall(text),
        "onready": _GD_ONREADY_RE.findall(text),
        "funcs": funcs,
        "func_names": list(funcs.keys()),
    }


def parse_tscn_structure(content: str) -> dict[str, Any]:
    nodes = _TSCN_NODE_RE.findall(content or "")
    scripts = _TSCN_SCRIPT_RE.findall(content or "")
    return {"nodes": nodes, "script_bindings": scripts}


_TSCN_SECTION_OPEN_RE = re.compile(
    r"^\[(?P<kind>gd_scene|ext_resource|sub_resource|node|resource)\b"
)
_TSCN_SUBRESOURCE_ID_RE = re.compile(
    r'\[sub_resource\b[^\]]*?\bid\s*=\s*"([^"]+)"'
)
_TSCN_SUBRESOURCE_USE_RE = re.compile(r'SubResource\s*\(\s*"([^"]+)"\s*\)')
_TSCN_EXTENTS_RE = re.compile(r"(?m)^[ \t]*extents\s*=")


def _tscn_section_header_closed(line: str) -> bool:
    """资源头是否在本行闭合（忽略属性里 groups=[...] 的中括号）。"""
    depth = 0
    in_str = False
    closed_at = -1
    for i, ch in enumerate(line):
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                closed_at = i
                break
    if closed_at < 0 or depth != 0:
        return False
    return all(c.isspace() for c in line[closed_at + 1 :])


def lint_tscn_godot4(content: str) -> list[str]:
    """写入前静态检查 Godot 4 .tscn 常见致命错误（防 dry-run 漏检未引用场景）。"""
    text = content or ""
    if not text.strip():
        return ["场景内容为空"]
    errs: list[str] = []
    defined_subs: set[str] = set()
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        if _TSCN_SECTION_OPEN_RE.match(stripped) and not _tscn_section_header_closed(
            stripped
        ):
            errs.append(f"第{i}行: 资源头缺少闭合 ]（如 [node name=\"X\" type=\"Y\"]）")
        for m in _TSCN_SUBRESOURCE_ID_RE.finditer(stripped):
            defined_subs.add(m.group(1))
        for m in _TSCN_SUBRESOURCE_USE_RE.finditer(stripped):
            rid = m.group(1)
            if rid not in defined_subs:
                errs.append(
                    f"第{i}行: SubResource(\"{rid}\") 在定义之前被引用；"
                    "请把 [sub_resource ...] 块放在引用之前"
                )
    if _TSCN_EXTENTS_RE.search(text):
        errs.append(
            "Godot 4 碰撞形状请用 size = Vector2(...)，不要用 Godot 3 的 extents"
        )
    return list(dict.fromkeys(errs))


def _nonblank_lines(text: str) -> list[str]:
    return [ln for ln in (text or "").splitlines() if ln.strip()]


def _changed_line_ratio(before: str, after: str) -> float:
    a = _nonblank_lines(before)
    b = _nonblank_lines(after)
    if not a:
        return 0.0 if not b else 1.0
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    j = 0
    while (
        j < len(a) - i
        and j < len(b) - i
        and a[-(j + 1)] == b[-(j + 1)]
    ):
        j += 1
    changed = max(len(a) - i - j, len(b) - i - j, 0)
    return min(1.0, changed / max(1, len(a)))


def assert_script_structure_fidelity(
    path: str,
    before: str,
    after: str,
    *,
    genre: str = "",
    allow_rewrite: bool = False,
    max_changed_ratio: float = _DEFAULT_MAX_CHANGED_RATIO,
    target_func_hints: list[str] | None = None,
) -> list[str]:
    """比较本动作前后结构；拦截非目标删除与大范围漂移。"""
    rel = str(path or "").replace("\\", "/")
    if not before.strip() or before == after:
        return []
    if allow_rewrite:
        return assert_critical_chain_preserved(rel, after, genre, before=before)

    errs: list[str] = []
    suffix = Path(rel).suffix.lower()
    if suffix == ".gd":
        b = parse_gdscript_structure(before)
        a = parse_gdscript_structure(after)
        if b["extends"] and a["extends"] and b["extends"] != a["extends"]:
            errs.append(f"{rel}: extends 被改成 {a['extends']}（原 {b['extends']}）")
        if b["class_name"] and a["class_name"] and b["class_name"] != a["class_name"]:
            errs.append(f"{rel}: class_name 被改动")
        deleted_funcs = [n for n in b["func_names"] if n not in a["funcs"]]
        if deleted_funcs:
            errs.append(
                f"{rel}: 原有函数需继续保留：{', '.join(deleted_funcs[:8])}；"
                "请用最小 patch 更新目标函数"
            )
        deleted_signals = [s for s in b["signals"] if s not in a["signals"]]
        if deleted_signals:
            errs.append(
                f"{rel}: 原有信号需继续保留：{', '.join(deleted_signals[:6])}"
            )
        deleted_exports = [s for s in b["exports"] if s not in a["exports"]]
        if deleted_exports:
            errs.append(
                f"{rel}: 原有 @export 变量需继续保留：{', '.join(deleted_exports[:8])}"
            )
        deleted_onready = [s for s in b["onready"] if s not in a["onready"]]
        if deleted_onready:
            errs.append(
                f"{rel}: 原有 @onready 变量需继续保留：{', '.join(deleted_onready[:8])}"
            )
        hints = set(target_func_hints or [])
        modified: list[str] = []
        for name, meta in b["funcs"].items():
            if name not in a["funcs"]:
                continue
            if meta["body"] != a["funcs"][name]["body"] or meta["sig"] != a["funcs"][name]["sig"]:
                modified.append(name)
        if hints:
            nontarget = [n for n in modified if n not in hints]
            if nontarget:
                errs.append(
                    f"{rel}: 非目标函数被改动 {', '.join(nontarget[:8])}；"
                    "请只 patch 目标函数"
                )
        ratio = _changed_line_ratio(before, after)
        if ratio > max_changed_ratio:
            errs.append(
                f"{rel}: 非空白行改动比例 {ratio:.0%} 超过默认 {max_changed_ratio:.0%}；"
                "请改用 replace_text 做更小 patch，或 goals 标明 rewrite_scope"
            )
    elif suffix == ".tscn":
        b = parse_tscn_structure(before)
        a = parse_tscn_structure(after)
        deleted_nodes = [n for n in b["nodes"] if n not in a["nodes"]]
        if deleted_nodes:
            errs.append(
                f"{rel}: 原有场景节点需继续保留：{', '.join(deleted_nodes[:8])}"
            )

    errs.extend(assert_critical_chain_preserved(rel, after, genre, before=before))
    return list(dict.fromkeys(errs))


def assert_critical_chain_preserved(
    path: str,
    content: str,
    genre: str,
    *,
    before: str | None = None,
    workspace_root: Path | None = None,
) -> list[str]:
    """若改动命中品类关键文件，要求锚点函数/信号/词元仍在。

    若提供 before：只要求「改前已存在」的锚点继续保留（避免迷你夹具误伤）。
    若提供 workspace_root 且 path 为空：扫描本品类全部关键文件（done 门禁）。
    """
    rel = str(path or "").replace("\\", "/")
    cfg = CRITICAL_CHAIN_BY_GENRE.get(genre) or {}
    errs: list[str] = []
    must_funcs: dict[str, list[str]] = cfg.get("must_keep_funcs") or {}
    must_signals: dict[str, list[str]] = cfg.get("must_keep_signals") or {}
    must_tokens: dict[str, list[str]] = cfg.get("must_keep_tokens") or {}

    scan_rels: list[str]
    if workspace_root is not None and not rel:
        scan_rels = list(
            dict.fromkeys(
                list(must_funcs.keys())
                + list(must_signals.keys())
                + list(must_tokens.keys())
                + list(cfg.get("paths") or [])
            )
        )
    else:
        scan_rels = [rel] if rel else []

    for file_rel in scan_rels:
        file_rel_n = str(file_rel).replace("\\", "/")
        disk_text: str | None = None
        if workspace_root is not None:
            disk_path = workspace_root / file_rel_n
            # 缺失文件不在此硬拦（玩家健康/诊断另管）；专拦「文件在但被 stub 掏空」
            if not disk_path.is_file():
                continue
            try:
                disk_text = disk_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                errs.append(f"无法读取关键玩法文件 {file_rel_n}")
                continue
        text = disk_text if disk_text is not None else (content or "")
        src_before = before if before is not None and not workspace_root else text
        if workspace_root is not None:
            # done 扫描：锚点相对当前磁盘全文强制存在（不因 stub「改前没有」而放行）
            src_before = text

        for fname in must_funcs.get(file_rel_n) or []:
            if workspace_root is None:
                existed = bool(
                    re.search(
                        rf"(?m)^func\s+{re.escape(fname)}\s*\(", src_before or ""
                    )
                )
                if not existed:
                    continue
            if not re.search(rf"(?m)^func\s+{re.escape(fname)}\s*\(", text or ""):
                errs.append(f"{file_rel_n}: 关键玩法函数缺失 {fname}()")
        for sname in must_signals.get(file_rel_n) or []:
            if workspace_root is None:
                existed = bool(
                    re.search(
                        rf"(?m)^signal\s+{re.escape(sname)}\b", src_before or ""
                    )
                )
                if not existed:
                    continue
            if not re.search(rf"(?m)^signal\s+{re.escape(sname)}\b", text or ""):
                errs.append(f"{file_rel_n}: 关键信号缺失 {sname}")
        for tok in must_tokens.get(file_rel_n) or []:
            if workspace_root is None and before is not None and tok not in (
                before or ""
            ):
                continue
            if tok and tok not in (text or ""):
                errs.append(f"{file_rel_n}: 关键链词元缺失 {tok}")
    return list(dict.fromkeys(errs))


def infer_target_funcs_from_patch(old_text: str, before: str) -> list[str]:
    """根据 replace 的 old_text 推断触及的函数名。"""
    if not old_text or not before:
        return []
    idx = before.find(old_text)
    if idx < 0:
        return []
    head = before[: idx + len(old_text)]
    names = _GD_FUNC_RE.findall(head)
    if not names:
        return []
    last = names[-1]
    fname = last[0] if isinstance(last, tuple) else str(last)
    return [fname]
