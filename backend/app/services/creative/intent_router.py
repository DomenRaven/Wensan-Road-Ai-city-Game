"""意图路由 A/B/C/D（建议向，品类无关）。

A 命中 catalog → 建议参考 skill_ids（可 enable 或会话现场实现；有条件必须写逻辑）
B 故障/调参修盘 → 禁再 enable 交差；可改 tuning / 会话 core / 桥
C 新机制 → 会话 core / scenes / ai_sandbox 自由实现；桥 API 可选
D 仅幻想引擎 API（add_method 等）→ 转会话 GDScript；前所未有玩法不算 D
"""

from __future__ import annotations

import re
from typing import Any

from app.services.creative.agent_contracts import bridge_api_names

# 用户话术 → 意图粗分类线索
_NEW_MECH_HINTS: re.Pattern[str] = re.compile(
    r"新技能|加一个|增加一个|新增|来个|来一个|我想要|能不能加|加个|整一个|整一个"
)
_TUNING_HINTS: re.Pattern[str] = re.compile(
    r"更快|更慢|太快|太慢|更高|更低|手感|难度|速度|射速|弹速|跳跃|颜色|外观|"
    r"五颜六色|彩色|彩虹|护盾|无敌|加速|氮气"
)
_CATALOG_HINTS: re.Pattern[str] = re.compile(
    r"技能太少|技能少|多加点技能|开技能|启用|打开|开启|加上|要炸弹|要激光|"
    r"二段跳|双跳|下砸|滑铲|吸经验|爆发|扣杀|旋转球|格挡|上勾拳|氮气|漂移|"
    r"发射激光|磁铁|大力扣杀|曲线球"
)
# 「掉落才开 / 敌机掉落物」≠ 一键 enable catalog 按钮技能
_DROP_LOOT_MECH: re.Pattern[str] = re.compile(
    r"掉落|掉落物|掉下来|敌机掉|敌人掉|击杀掉|"
    r"捡到才|拾取才|捡了才|捡起才|获得才|掉到才|掉了才|"
    r"不是按钮|别.*按钮|不要按钮|不要一上来就|"
    r"道具开启|掉宝|战利品|落地才"
)


def is_drop_loot_request(text: str) -> bool:
    """用户要把某能力做成掉落/拾取才解锁，而非直接开 catalog 按钮。"""
    return bool(_DROP_LOOT_MECH.search(text or ""))


# 掉落语义中明确点名 catalog 技能（激光/炸弹）——才允许走 shmup 掉落快车道 + 专用门禁
_LASER_BOMB_NAME: re.Pattern[str] = re.compile(
    r"激光|镭射|laser|炸弹|清屏|bomb", re.I
)


def is_laser_bomb_drop_request(text: str) -> bool:
    """掉落请求且明确针对激光/炸弹（快车道/专用门禁的适用范围）。

    「掉落一颗爱心回血」等通用掉落不属于此类，应走 LLM 自由创作。
    """
    t = text or ""
    return is_drop_loot_request(t) and bool(_LASER_BOMB_NAME.search(t))


def _catalog_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in contract.get("catalog_skills") or []:
        if isinstance(item, dict) and str(item.get("id", "")).strip():
            out.append(item)
    return out


def _match_catalog_skills(text: str, contract: dict[str, Any]) -> list[str]:
    """按 id / label / 常见别名命中 catalog。"""
    low = text.lower()
    hits: list[str] = []
    aliases: dict[str, tuple[str, ...]] = {
        "bomb": ("炸弹", "清屏", "清屏弹", "大炸弹", "bomb"),
        "laser_beam": ("激光", "镭射", "发射激光", "开激光", "激光炮", "laser"),
        "double_jump": ("二段跳", "双跳", "两段跳", "再跳一次", "double_jump", "double jump"),
        "ground_pound": ("下砸", "砸地", "地面砸击", "ground_pound", "ground pound"),
        "magnet": ("吸经验", "磁铁", "吸取", "磁力", "magnet"),
        "nova": ("环形爆发", "爆发", "清屏一圈", "大招清怪", "nova"),
        "slide": ("滑铲", "下滑", "滑行", "slide"),
        "power_smash": ("大力扣杀", "扣杀", "重击", "大力扣", "power_smash"),
        "curve_ball": ("旋转球", "曲线球", "曲线球路", "curve"),
        "block_parry": ("格挡", "招架", "防御反击", "parry", "block"),
        "special_uppercut": ("上勾拳", "勾拳", "必杀勾拳", "uppercut"),
        "boost": ("氮气", "加速氮气", "开加速", "喷气加速", "boost"),
        "drift_snap": ("漂移", "甩尾", "drift"),
    }
    for skill in _catalog_entries(contract):
        sid = str(skill.get("id", "")).strip()
        label = str(skill.get("label", "")).strip()
        needles = list(aliases.get(sid, ()))
        needles.extend([sid, label])
        for n in needles:
            if not n:
                continue
            if n.lower() in low or n in text:
                if sid not in hits:
                    hits.append(sid)
                break
    # 「技能太少」类：未点名则建议开满尚未启用的 catalog（由调用方决定开几个）
    if not hits and re.search(r"技能太少|技能少|多加.*技能|多来点技能", text):
        for skill in _catalog_entries(contract):
            sid = str(skill.get("id", "")).strip()
            if sid and sid not in hits:
                hits.append(sid)
    return hits


def _match_recipe(text: str, contract: dict[str, Any]) -> dict[str, Any] | None:
    for r in contract.get("edit_recipes") or []:
        if not isinstance(r, dict):
            continue
        intent = str(r.get("intent", "")).strip()
        if not intent:
            continue
        # 用 / 或 、 拆关键词
        parts = re.split(r"[/、,，|]", intent)
        for p in parts:
            p = p.strip()
            if len(p) >= 2 and (p in text or p.lower() in text.lower()):
                return r
    return None


def _needs_unknown_bridge(text: str, contract: dict[str, Any]) -> bool:
    """仅拦截「幻想引擎/桥 API」——前所未有玩法应走 C，用会话 core 实现。"""
    if re.search(
        r"add_method|bridge\.add_method|自己写引擎|改引擎源码|OS\.execute|HTTPRequest",
        text,
        re.I,
    ):
        return True
    known = bridge_api_names(contract)
    for m in re.finditer(r"bridge\.([A-Za-z_][A-Za-z0-9_]*)", text):
        if m.group(1) not in known:
            return True
    return False


def route_intent(user_text: str, contract: dict[str, Any]) -> dict[str, Any]:
    """输出确定性路由结果。

    返回::
        {
          "intent": "A"|"B"|"C"|"D",
          "recipe_id": str,
          "skill_ids": list[str],
          "actions": list[dict],
          "hint": str,
          "stop": bool,
          "stop_reason": str,
        }
    """
    text = (user_text or "").strip()
    genre = str(contract.get("genre", ""))
    skill_ids = _match_catalog_skills(text, contract)
    recipe = _match_recipe(text, contract)
    recipe_id = str((recipe or {}).get("intent", "") or "")

    # 可玩性：白屏 / 人物不显示 → 优先读玩家与近期改动
    if re.search(
        r"人物.*消失|角色.*消失|人不显示|人物.*不显示|看不见.*人|角色.*看不见|"
        r"精灵.*消失|player.*visible|不显示了|人没了|角色没了|"
        r"白屏|黑屏|看不到画|没有画面",
        text,
        re.I,
    ):
        return {
            "intent": "B",
            "recipe_id": "运行时显示/启动故障",
            "skill_ids": [],
            "actions": [
                {"tool": "diagnose_workspace"},
                {"tool": "prefer", "action": "read_then_fix_core"},
            ],
            "hint": (
                "先 diagnose + 读玩家脚本/主场景/本局近期改动；"
                "核对 visible、modulate.a、position、scale、挂载与 group=player；"
                "最小写入修复后，summary 说明修好了什么"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": True,
        }

    # 输入冲突：shmup 左键跟机抢技能按钮（品类门控，避免非 shmup 被「飞机」话术带偏）
    if genre == "shmup" and re.search(
        r"鼠标|点.*按钮.*(飞|位置|没反应)|只会改变.*位置|技能不能用|按钮.*没反应|"
        r"点了没反应|点技能.*飞|跟机|点屏幕.*飞",
        text,
    ):
        return {
            "intent": "B",
            "recipe_id": "鼠标与技能按钮冲突",
            "skill_ids": [],
            "actions": [
                {"tool": "patch_mouse_steer_guard"},
                {"tool": "ensure_touch_skill_buttons"},
            ],
            "hint": (
                "左键跟机会与技能按钮抢输入："
                "patch 会话 core/player_ship.gd 跟机守卫 + 桥 is_mouse_steer_blocked；"
                "how_to_play 写「点技能键时飞机不会跟着跑」"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": False,
        }

    # 触屏无效但键盘有效：查桥/HUD
    if re.search(
        r"(按钮|触屏|屏幕).{0,12}(不|没|无法).{0,8}(发射|放|出|用|反应)|"
        r"(键盘|按键|[QqEe]|空格).{0,8}(可以|能|行)|"
        r"只有.{0,6}(键盘|按键)|点了.{0,8}不(发射|出|放)",
        text,
    ):
        return {
            "intent": "B",
            "recipe_id": "触屏按钮无效键盘有效",
            "skill_ids": [],
            "actions": [
                {"tool": "refresh_ai_sandbox_bridge"},
                {"tool": "ensure_touch_skill_buttons"},
            ],
            "hint": (
                "键盘有效说明能力已在盘上；优先 refresh_ai_sandbox_bridge 与触屏 HUD，"
                "再确认会话文件确有改动后写 how_to_play"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": True,
        }

    # D：未知桥 API → 改会话实现同等效果
    if _needs_unknown_bridge(text, contract):
        return {
            "intent": "D",
            "recipe_id": recipe_id,
            "skill_ids": skill_ids,
            "actions": [],
            "hint": "该桥/引擎 API 不在契约列表：请用会话 core GDScript 实现同等效果",
            "stop": True,
            "stop_reason": "请用会话 GDScript 实现同等效果（契约外 API 不调用）",
            "genre": genre,
            "advisory": True,
        }

    # 掉落/拾取才开启
    if is_drop_loot_request(text):
        named = skill_ids[:2]
        named_txt = "、".join(named) if named else "该能力"
        if genre != "shmup":
            return {
                "intent": "C",
                "recipe_id": recipe_id or "drop_loot_unlock",
                "skill_ids": [],
                "actions": [
                    {"tool": "diagnose_workspace"},
                    {"tool": "prefer", "action": "read_then_write_core"},
                ],
                "hint": (
                    f"目标是让{named_txt}走当前品类真实掉落/拾取链；"
                    "请先读生成、碰撞/拾取、效果应用与计分/生命相关脚本，"
                    "再用会话逻辑实现掉落→拾取→效果"
                ),
                "stop": False,
                "stop_reason": "",
                "genre": genre,
                "advisory": True,
                "express": False,
            }
        return {
            "intent": "C",
            "recipe_id": recipe_id or "drop_loot_unlock",
            "skill_ids": [],
            "actions": [
                {"tool": "diagnose_workspace"},
                {
                    "tool": "apply_shmup_drop_loot_chain",
                    "skills": named or ["laser_beam", "bomb"],
                    "hint": (
                        f"实现：{named_txt} 作为敌机/敌人掉落道具；"
                        "玩家捡到后才解锁或临时可用"
                    ),
                },
            ],
            "hint": (
                "目标是「掉落物/捡到才开」。优先调用 apply_shmup_drop_loot_chain；"
                "手写须同时改 powerup_types 与 core/player_ship.gd 的 apply_powerup 拾取解锁；"
                "how_to_play 写「打敌机→捡掉落」。"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": False,
            "express": False,
        }

    # HF-12：带条件需求优先开放实现，Catalog 仅材料
    from app.services.creative.agent_contracts import user_text_has_conditional_mechanics

    if skill_ids and user_text_has_conditional_mechanics(text):
        return {
            "intent": "C",
            "recipe_id": recipe_id or "free_create_with_catalog_reference",
            "skill_ids": skill_ids,
            "actions": [
                {"tool": "diagnose_workspace"},
                {"tool": "read_file", "path": "config/game_config.json"},
            ],
            "hint": (
                "用户原话含条件/数值/手感：请用会话脚本实现计数/冷却/倍率/触发时机；"
                f"catalog {', '.join(skill_ids[:3])} 仅作材料参考；"
                "须在会话脚本写出条件/计数/冷却后再 done"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": True,
            "express": False,
        }

    # A：命中 catalog（纯开关类）
    if skill_ids:
        actions = [
            {"tool": "enable_catalog_skill", "skill_id": sid} for sid in skill_ids
        ]
        extra_hint = ""
        if recipe and str(recipe.get("action", "")) in ("bridge_api", "sandbox_apply"):
            extra_hint = f"；同时可按 recipe 施工：{recipe.get('hint', '')}"
            actions.append(
                {
                    "tool": "write_file",
                    "path": "core/ai_sandbox/routed_effect.gd",
                    "hint": str(recipe.get("hint", "")),
                }
            )
        return {
            "intent": "A",
            "recipe_id": recipe_id or "catalog",
            "skill_ids": skill_ids,
            "actions": actions,
            "hint": (
                "可参考 catalog skill_ids：enable 或会话现场实现均可；"
                "有附加条件时在会话脚本写出条件逻辑"
            )
            + extra_hint,
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": bool(re.search(r"技能太少|技能少|多加.*技能|多来点技能", text)),
            "express": False,
        }

    # 有 recipe：先按 action 分流（bridge/sandbox → C，再 B）
    if recipe is not None:
        action = str(recipe.get("action", ""))
        if action in ("bridge_api", "sandbox_apply", "sandbox_or_rules"):
            return {
                "intent": "C",
                "recipe_id": recipe_id,
                "skill_ids": [],
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "core/ai_sandbox/routed_effect.gd",
                        "hint": str(recipe.get("hint", "")),
                    }
                ],
                "hint": str(recipe.get("hint", "仅契约内 bridge_apis + apply(bridge)")),
                "stop": False,
                "stop_reason": "",
                "genre": genre,
            }
        if action == "enable_catalog_skill":
            all_ids = [str(s.get("id")) for s in _catalog_entries(contract)]
            return {
                "intent": "A",
                "recipe_id": recipe_id,
                "skill_ids": all_ids[:2],
                "actions": [
                    {"tool": "enable_catalog_skill", "skill_id": sid}
                    for sid in all_ids[:2]
                ],
                "hint": str(recipe.get("hint", "开 catalog 技能")),
                "stop": False,
                "stop_reason": "",
                "genre": genre,
            }
        if action in (
            "edit_session_core_or_tuning",
            "edit_session_core",
            "set_tuning_or_core",
            "bridge_or_tuning",
            "set_tuning_number",
        ) or _TUNING_HINTS.search(text):
            return {
                "intent": "B",
                "recipe_id": recipe_id,
                "skill_ids": [],
                "actions": [
                    {
                        "tool": "prefer",
                        "action": action or "edit_session_core_or_tuning",
                        "paths": recipe.get("paths", ""),
                        "hint": recipe.get("hint", ""),
                    }
                ],
                "hint": str(recipe.get("hint", "改会话 tuning/core 或已有桥 API")),
                "stop": False,
                "stop_reason": "",
                "genre": genre,
            }

    if _TUNING_HINTS.search(text) or _CATALOG_HINTS.search(text):
        return {
            "intent": "B",
            "recipe_id": recipe_id or "tuning",
            "skill_ids": [],
            "actions": [{"tool": "prefer", "action": "edit_session_core_or_tuning"}],
            "hint": "按数值/外观/生成链改会话副本或已有桥 API",
            "stop": False,
            "stop_reason": "",
            "genre": genre,
        }

    if _NEW_MECH_HINTS.search(text):
        return {
            "intent": "C",
            "recipe_id": recipe_id or "free_create",
            "skill_ids": [],
            "actions": [
                {
                    "tool": "write_file",
                    "path": "core/ai_sandbox/routed_effect.gd",
                    "hint": "可写会话 core/scenes/ai_sandbox；桥 API 可选捷径",
                }
            ],
            "hint": (
                "新机制：在会话 core/*.gd 与 scenes 实现用户所求玩法；"
                "ai_sandbox+桥 API、catalog/Skill 是可选捷径；实现对齐需求本身"
            ),
            "stop": False,
            "stop_reason": "",
            "genre": genre,
            "advisory": True,
        }

    # 默认：读盘后自由改会话（不保守劝退）
    return {
        "intent": "C",
        "recipe_id": recipe_id or "free_create",
        "skill_ids": [],
        "actions": [{"tool": "prefer", "action": "read_then_write_core"}],
        "hint": "未强匹配：先读会话结构，再在 core/scenes 实现用户需求；catalog/桥可选",
        "stop": False,
        "stop_reason": "",
        "genre": genre,
        "advisory": True,
    }


def format_route_for_prompt(route: dict[str, Any]) -> str:
    lines = [
        "## 意图建议（参考材料，可自主选择更优实现）",
        f"- intent: {route.get('intent')} · recipe: {route.get('recipe_id') or '—'}",
        f"- hint: {route.get('hint', '')}",
    ]
    skills = route.get("skill_ids") or []
    if skills:
        lines.append(
            f"- 可参考 catalog: {', '.join(skills)}；也可用会话 core 写等价实现"
        )
    if route.get("stop"):
        lines.append(f"- 提示：{route.get('stop_reason', '')}")
        lines.append("- 建议：用会话 GDScript 实现同等效果")
    lines.append(
        "- 门禁关注：磁盘有实现、API 真实存在、声称与磁盘一致；done 前完成写入"
    )
    return "\n".join(lines)


def enforce_route_on_actions(
    route: dict[str, Any],
    actions: list[dict[str, Any]],
) -> list[str]:
    """写前纠偏：仅拦幻想 API 路径；catalog 命中不再强制 enable（允许会话 core 另写）。"""
    errors: list[str] = []
    if str(route.get("intent", "")) != "D" or not route.get("stop"):
        return errors
    # 允许用会话 core 实现同等效果；禁止继续调用不存在的 bridge.xxx
    for a in actions:
        if not isinstance(a, dict):
            continue
        tool = str(a.get("tool", ""))
        content = str(a.get("content", ""))
        if tool == "write_file" and re.search(
            r"add_method|bridge\.[A-Za-z_]+\(", content
        ):
            # 写文件里若仍幻想 bridge 未知方法，交给 assert_apis；此处只拦 add_method
            if "add_method" in content:
                errors.append("请用会话 GDScript 实现同等效果（勿调用 bridge.add_method）")
        if tool in ("done",) and not any(
            isinstance(x, dict) and str(x.get("tool", "")) == "write_file"
            for x in actions
        ):
            # 纯 done 无写入：仍允许（game_agent 早停）；不额外报错
            pass
    return errors
