"""对话意图 → 可执行沙箱规则（确定性编译）。

目标：用户与 LLM 对话即可落地玩法，不依赖开发者事后修。
LLM 可增强文案/图标/脚本；本模块保证常见中文诉求一定写成 bridge 能执行的规则。
"""

from __future__ import annotations

import re
from typing import Any

from app.services.config_builder import (
    get_path,
    load_optional_skills_catalog,
    load_optional_skills_entries,
    load_optional_skills_max,
)


def _default_skill_svg(skill_id: str) -> str:
    presets: dict[str, str] = {
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
    }
    if skill_id in presets:
        return presets[skill_id]
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

# 能力目录：对话可承诺的玩法（桥原生或预制技能）
CAPABILITY_CATALOG: list[dict[str, str]] = [
    {
        "id": "double_jump",
        "title": "二段跳",
        "how": "跳起后在空中下落时再按「跳」触发第二次跳跃；左上角有图标即已启用",
    },
    {
        "id": "ground_pound",
        "title": "下砸",
        "how": "空中下落时再按「跳」可下砸",
    },
    {
        "id": "coin_streak_buff",
        "title": "金币连击增益",
        "how": "每吃满 N 个金币：无敌 + 加速 + 发光特效 + 顶部倒计时",
    },
    {
        "id": "invincible_longer",
        "title": "受伤无敌更久",
        "how": "被碰后闪烁无敌时间变长",
    },
    {
        "id": "move_faster",
        "title": "跑得更快",
        "how": "左右移动速度提高",
    },
    {
        "id": "jump_higher",
        "title": "跳得更高",
        "how": "起跳初速度更大",
    },
    {
        "id": "skill_icon",
        "title": "技能图标",
        "how": "左上角显示技能 SVG 图标",
    },
]


def catalog_for_prompt() -> str:
    lines = ["【对话可落地的能力（用户说中文即可）】"]
    for item in CAPABILITY_CATALOG:
        lines.append(f"- {item['id']} · {item['title']}：试玩时 {item['how']}")
    lines.append(
        "复杂需求可写 sandbox_rules.* / core/ai_sandbox 新文件，"
        "亦可改会话副本 core（勿碰 templates）。改完必须重开游戏才会生效。"
    )
    return "\n".join(lines)


def _merge_change(
    changes: list[dict[str, Any]],
    path: str,
    before: Any,
    after: Any,
) -> None:
    for c in changes:
        if str(c.get("path")) == path:
            c["after"] = after
            return
    changes.append({"path": path, "before": before, "after": after})


def _has_file(files: list[dict[str, str]], suffix: str) -> bool:
    return any(str(f.get("filename", "")).endswith(suffix) for f in files)


# 笼统「多加技能」类诉求
_MORE_SKILLS_PHRASES: tuple[str, ...] = (
    "技能太少",
    "技能不够",
    "技能少",
    "多加技能",
    "加点技能",
    "再加技能",
    "有趣的技能",
    "更多技能",
    "多开技能",
    "技能多一点",
    "再多点技能",
    "多来点技能",
    "没有技能",
    "加技能",
    "开技能",
    "多给点技能",
    "技能好玩",
)


def _wants_more_skills(text: str) -> bool:
    if any(p in text for p in _MORE_SKILLS_PHRASES):
        return True
    # 「飞机技能太少了 / 多加有趣的技能」等：含技能 + 增减/有趣语气
    if "技能" in text and any(
        w in text for w in ("多", "加", "开", "要", "给", "有趣", "好玩", "少", "不够")
    ):
        return True
    return False


# 七品类技能中文别名 → catalog id（对话确定性落地）
_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "double_jump": ("二段跳", "双跳", "二段", "double jump", "double_jump"),
    "ground_pound": ("下砸", "砸地", "ground pound", "ground_pound"),
    "bomb": ("清屏炸弹", "炸弹", "bomb"),
    "laser_beam": ("激光", "laser"),
    "magnet": ("吸经验", "磁铁", "magnet"),
    "nova": ("环形爆发", "清屏一圈", "nova"),
    "block_parry": ("格挡", "招架", "block", "parry"),
    "special_uppercut": ("上勾拳", "勾拳", "uppercut"),
    "boost": ("氮气加速", "氮气", "boost"),
    "drift_snap": ("漂移", "drift"),
    "slide": ("滑铲", "滑行", "slide"),
    "power_smash": ("大力扣杀", "扣杀", "smash"),
    "curve_ball": ("旋转球", "曲线球", "curve"),
    "dash": ("冲刺闪避", "闪避", "dash"),
    "shield_burst": ("能量护盾", "护盾", "shield"),
    "spread_shot": ("散射", "三发散", "spread"),
}


def _enable_skill(
    changes: list[dict[str, Any]],
    new_files: list[dict[str, str]],
    applied: list[str],
    how_to_play: list[str],
    config: dict[str, Any],
    catalog: list[str],
    skill_id: str,
    how: str,
    with_icon: bool,
) -> None:
    if skill_id not in catalog:
        return
    before_raw = get_path(config, "tuning.enabled_skills")
    before: list[str] = [str(x) for x in before_raw] if isinstance(before_raw, list) else []
    for c in changes:
        if c.get("path") == "tuning.enabled_skills" and isinstance(c.get("after"), list):
            before = list(c["before"]) if isinstance(c.get("before"), list) else before
            merged = list(c["after"])
            break
    else:
        merged = list(before)
    if skill_id not in merged:
        merged.append(skill_id)
    merged = merged[: load_optional_skills_max()]
    _merge_change(changes, "tuning.enabled_skills", before, merged)
    if skill_id not in applied:
        applied.append(skill_id)
    if how and how not in how_to_play:
        how_to_play.append(how)
    if with_icon and not _has_file(new_files, f"{skill_id}.svg"):
        new_files.append(
            {
                "filename": f"icons/{skill_id}.svg",
                "content": _default_skill_svg(skill_id),
            }
        )
        if "skill_icon" not in applied:
            applied.append("skill_icon")


def compile_user_intent(
    text: str,
    genre: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """把自然语言编译成 changes / new_files / applied / how_to_play。"""
    changes: list[dict[str, Any]] = []
    new_files: list[dict[str, str]] = []
    applied: list[str] = []
    how_to_play: list[str] = []
    catalog = load_optional_skills_catalog().get(genre, [])
    want_icon = any(w in text for w in ("图标", "icon", "画画", "绘制", "画一个", "画个"))
    # 开技能默认给图标，对话更完整
    with_icon = want_icon or any(w in text for w in ("技能", "开", "启用", "加上", "给我"))

    how_by_id = {item["id"]: item["how"] for item in CAPABILITY_CATALOG}
    label_by_id = {eid: label for eid, label, _desc in load_optional_skills_entries(genre)}
    for sid in catalog:
        aliases = _SKILL_ALIASES.get(sid, ())
        label = label_by_id.get(sid, "")
        hit = sid in text or any(a in text for a in aliases) or (bool(label) and label in text)
        if hit:
            how = how_by_id.get(sid, f"已启用技能「{label or sid}」，左上角可有图标")
            if sid == "double_jump":
                how = "跳起后等人物开始下落，再按一次「跳」= 二段跳"
            _enable_skill(
                changes,
                new_files,
                applied,
                how_to_play,
                config,
                catalog,
                sid,
                how,
                with_icon=with_icon or sid == "double_jump",
            )

    # 笼统「技能太少 / 多加有趣技能」→ 把本品类目录技能开满（最多 max）
    if _wants_more_skills(text) and catalog:
        labels_opened: list[str] = []
        for sid in catalog:
            label = label_by_id.get(sid, sid)
            how = how_by_id.get(sid, f"已启用「{label}」")
            if sid == "bomb":
                how = "按技能键放出清屏炸弹，清掉屏幕子弹"
            elif sid == "laser_beam":
                how = "按技能键发射穿透激光"
            before_len = len(applied)
            _enable_skill(
                changes,
                new_files,
                applied,
                how_to_play,
                config,
                catalog,
                sid,
                how,
                with_icon=True,
            )
            if sid in applied and label not in labels_opened:
                labels_opened.append(label)
            # _enable_skill 受 max 限制；若未新增则可能已满
            if len(applied) == before_len and sid not in applied:
                continue
        if labels_opened:
            tip = (
                f"已打开本关技能：{'、'.join(labels_opened)}"
                f"（最多 {load_optional_skills_max()} 个），左上角有图标；请重开游戏后试用"
            )
            if tip not in how_to_play:
                how_to_play.insert(0, tip)

    # 金币连击增益
    if any(w in text for w in ("金币", "樱桃", "coin")) and any(
        w in text for w in ("无敌", "加速", "特效", "倒计时", "buff", "增益")
    ):
        every = 5
        m = re.search(r"(\d+)\s*个", text)
        if m:
            every = max(1, min(20, int(m.group(1))))
        for token, n in (("五个", 5), ("五枚", 5), ("三个", 3), ("十个", 10)):
            if token in text:
                every = n
                break
        _merge_change(
            changes,
            "sandbox_rules.coin_every",
            get_path(config, "sandbox_rules.coin_every"),
            every,
        )
        _merge_change(
            changes,
            "sandbox_rules.coin_duration",
            get_path(config, "sandbox_rules.coin_duration"),
            3.0,
        )
        _merge_change(
            changes,
            "sandbox_rules.coin_speed_mult",
            get_path(config, "sandbox_rules.coin_speed_mult"),
            1.35,
        )
        if not _has_file(new_files, "coin_streak_buff.gd"):
            new_files.append(
                {
                    "filename": "coin_streak_buff.gd",
                    "content": _coin_streak_buff_script(every, 3.0),
                }
            )
        applied.append("coin_streak_buff")
        how_to_play.append(
            f"开始游戏后连续吃满 {every} 个金币/樱桃：会无敌、加速、发光，顶部有倒计时"
        )

    # 受伤无敌更久（纯数值）
    if any(w in text for w in ("无敌", "免伤", "闪烁")) and not any(
        w in text for w in ("金币", "樱桃", "coin")
    ):
        path = "tuning.lives.invincible_sec"
        base = get_path(config, path)
        if isinstance(base, (int, float)):
            after = round(float(base) * 1.25, 4)
            _merge_change(changes, path, base, after)
            applied.append("invincible_longer")
            how_to_play.append("被敌人碰到后，无敌闪烁时间更长")

    # 跑更快 / 跳更高 —— 留给 numeric stub/LLM，这里只记提示
    if any(w in text for w in ("跑快", "跑得快", "移动快", "速度加快", "更快")) and "coin_streak_buff" not in applied:
        applied.append("move_faster")
        how_to_play.append("左右移动会更快（需配合数值改参）")
    if ("跳" in text and "高" in text) or any(
        w in text for w in ("跳高", "跳得高", "跳更高", "跳得更高")
    ):
        applied.append("jump_higher")
        how_to_play.append("跳跃会更高（需配合数值改参）")
        # 尽力写入 jump 相关白名单数值（到上限则后续 already_applied）
        for path in (
            "tuning.player.jump_velocity",
            "tuning.jump.velocity",
            "tuning.jump.force",
            "tuning.player.jump_force",
        ):
            base = get_path(config, path)
            if isinstance(base, (int, float)) and not isinstance(base, bool):
                # 负向 jump_velocity：更负=更高
                if float(base) < 0:
                    after = round(float(base) * 1.2, 4)
                else:
                    after = round(float(base) * 1.2, 4)
                _merge_change(changes, path, base, after)
                break

    return {
        "changes": changes,
        "new_files": new_files,
        "applied_capabilities": applied,
        "how_to_play": how_to_play,
    }


def merge_compiled_into(
    primary_changes: list[dict[str, Any]],
    primary_files: list[dict[str, str]],
    compiled: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """编译结果优先保证落地；不覆盖已有同 path 的 LLM 更优数值时可保留 LLM。"""
    out_changes = list(primary_changes)
    paths = {str(c.get("path")) for c in out_changes}
    for c in compiled.get("changes", []):
        path = str(c.get("path", ""))
        if path not in paths:
            out_changes.append(c)
            paths.add(path)
        else:
            # 技能列表 / sandbox_rules 以编译为准（对话确定性）
            if path in ("tuning.enabled_skills",) or path.startswith("sandbox_rules."):
                for i, existing in enumerate(out_changes):
                    if str(existing.get("path")) == path:
                        out_changes[i] = c
                        break
    out_files = list(primary_files)
    names = {str(f.get("filename")) for f in out_files}
    for f in compiled.get("new_files", []):
        name = str(f.get("filename", ""))
        if name and name not in names:
            out_files.append(f)
            names.add(name)
    return out_changes, out_files


def infer_applied_from_patch(
    changes: list[dict[str, Any]],
    new_files: list[dict[str, str]],
) -> list[str]:
    """从最终 patch 反推已落地能力 id。"""
    applied: list[str] = []
    for c in changes:
        path = str(c.get("path", ""))
        after = c.get("after")
        if path == "tuning.enabled_skills" and isinstance(after, list):
            for sid in after:
                sid_s = str(sid)
                if sid_s not in applied:
                    applied.append(sid_s)
        if path == "sandbox_rules.coin_every" and after is not None:
            if "coin_streak_buff" not in applied:
                applied.append("coin_streak_buff")
        if path == "tuning.lives.invincible_sec":
            if "invincible_longer" not in applied:
                applied.append("invincible_longer")
    for f in new_files:
        name = str(f.get("filename", ""))
        if name.endswith(".svg") or name.endswith(".png"):
            if "skill_icon" not in applied:
                applied.append("skill_icon")
    return applied


def verify_against_request(
    text: str,
    applied: list[str],
) -> list[str]:
    """检查用户话里提到的能力是否已应用，返回缺口说明（给 LLM 再改）。"""
    gaps: list[str] = []
    if any(w in text for w in ("二段跳", "双跳", "二段")) and "double_jump" not in applied:
        gaps.append("用户要二段跳，但 enabled_skills 未包含 double_jump")
    if any(w in text for w in ("金币", "樱桃")) and any(
        w in text for w in ("无敌", "加速", "特效", "倒计时")
    ):
        if "coin_streak_buff" not in applied:
            gaps.append("用户要金币连击增益，但缺少 sandbox_rules.coin_every")
    if any(w in text for w in ("图标", "绘制", "画画")) and "skill_icon" not in applied:
        if any(w in text for w in ("二段跳", "双跳", "技能")):
            gaps.append("用户要技能图标，但未写入 icons/*.svg")
    return gaps


def how_to_play_for_applied(applied: list[str], text: str = "") -> list[str]:
    """按已落地能力生成试玩说明。"""
    by_id = {item["id"]: item["how"] for item in CAPABILITY_CATALOG}
    lines: list[str] = []
    for cap in applied:
        how = by_id.get(cap)
        if how and how not in lines:
            if cap == "coin_streak_buff":
                every = 5
                m = re.search(r"(\d+)\s*个", text)
                if m:
                    every = max(1, min(20, int(m.group(1))))
                lines.append(f"连续吃满 {every} 个金币/樱桃：无敌 + 加速 + 发光 + 顶部倒计时")
            else:
                lines.append(how)
    if not lines:
        lines.append("改参已写入；请重新启动游戏后再试玩")
    lines.append("重要：必须重新启动游戏后新规则才会生效")
    return lines
