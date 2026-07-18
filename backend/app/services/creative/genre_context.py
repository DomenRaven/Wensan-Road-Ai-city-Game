"""各品类项目结构与接线说明 · 注入 LLM（可改会话 core；templates 只读）。"""

from __future__ import annotations

from pathlib import Path

from app.services.config_builder import load_optional_skills_entries, load_optional_skills_max
from app.services.creative.agent_contracts import format_contract_for_prompt, load_contract

# 人工维护接线 playbook；深度对齐 platformer；禁止「禁止改会话 core」旧表述。
_GENRE_PLAYBOOK: dict[str, str] = {
    "platformer": """
【platformer 玩法接线】
- 主场景 res://scenes/main.tscn；GameManager / player_platformer.gd（CharacterBody2D）
- 金币 collectible.gd：信号 collected；二段跳/下砸：has_skill("double_jump"|"ground_pound")
- 桥已对下落段补二段跳；数值类 buff 仅当用户明确要求时再加
- 前所未有需求：在会话 core/scenes **现场实现**用户要的机制；catalog/桥是捷径不是天花板
- 需求对齐：summary 声称的能力必须落在磁盘上；勿用无关玩法顶替后口头交差
- 【可改】会话副本 core/*.gd、config、scenes；【禁止】templates/**
- 新机制：优先写可运行的 GDScript 并挂到场景；ai_sandbox+桥可选
""".strip(),
    "shmup": """
【shmup 玩法接线 · 与 platformer 同级深度】
- 主场景射击；玩家 Area2D · core/player_ship.gd（group=player）；get_player() 可能 null → 用 get_player_node()
- 自动射击；左右移动；子弹池 core/bullet_pool.gd → spawn_player_bullet / spawn_enemy_bullet
- 子弹外观 core/bullet.gd activate()；改颜色勿发明 set_color——用桥 tint_player_bullets / rainbow_player_bullets
- 预制技能仅 bomb、laser_beam（enabled_skills）；输入见 skills/*.gd
- 护盾：【不是】catalog 技能；机体捡道具 "shield" 或桥 grant_temp_shield(seconds)
- 【鼠标冲突】飞机用左键跟机；点技能按钮会抢输入。须 patch_mouse_steer_guard / 会话 player_ship 守卫；禁止只重复 enable 技能
- 前所未有需求：会话 core/scenes 现场写；catalog/桥是捷径
- 【可改】会话 core/player_ship.gd、bullet.gd、bullet_pool.gd、config、scenes；【禁止】templates/**
- 示例「五颜六色子弹」：ai_sandbox + rainbow_player_bullets，或直接改 bullet 生成链
- 【展厅硬性】how_to_play 写「点屏幕下方 炸弹/激光 按钮」；ShmupTouch 只负责移动，技能键走桥 HUD
""".strip(),
    "survivor": """
【survivor】割草幸存者；玩家移动自动攻击；catalog：magnet / nova（捷径）。
- 前所未有需求：会话 core/scenes 现场实现；勿被 catalog 限死
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "parkour": """
【parkour】跑酷冲刺；catalog：double_jump / slide（捷径）。
- 二段跳下落段可由桥补齐；加速可用桥或改会话 core
- 前所未有需求：会话 core/scenes 现场写
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "pingpong": """
【pingpong】乒乓；catalog：power_smash / curve_ball（捷径）。
- 改球速用 tuning / 会话 core；前所未有需求现场写会话副本
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "fighting": """
【fighting】格斗擂台；catalog：block_parry / special_uppercut（捷径）。
- 临时霸体可用桥；新招式/新规则用会话 core 写；无血腥
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "racing": """
【racing】欢乐赛车；catalog：boost / drift_snap（捷径）。
- 氮气感可用桥或开 boost；新赛道要素用会话 core/scenes 写
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
}


def _list_rel_files(root: Path, sub: str, limit: int = 40) -> list[str]:
    base = root / sub
    if not base.is_dir():
        return []
    out: list[str] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".gd", ".tscn", ".json", ".png", ".svg"}:
            continue
        out.append(path.relative_to(root).as_posix())
        if len(out) >= limit:
            break
    return out


def build_genre_llm_context(templates_dir: Path, genre: str) -> str:
    """生成发给 LLM 的品类结构说明（扫描 + playbook + Contract）。"""
    root = templates_dir / genre
    lines: list[str] = [
        f"## 本局品类结构（genre={genre}）",
        "红线：禁止修改 templates/**；会话 workspace 内可改 core/**、config/**、scenes/**、assets/**。",
        "done 前必须通过门禁：无幻想 API、声称对齐磁盘、how_to_play 含重开提示。",
        "",
    ]
    if root.is_dir():
        core_files = _list_rel_files(root, "core", 35)
        scene_files = _list_rel_files(root, "scenes", 15)
        cfg = root / "config" / "game_config.json"
        lines.append("### 关键文件（模板只读参考；改的是会话副本）")
        if core_files:
            lines.append("core/：")
            lines.extend(f"- {p}" for p in core_files)
        if scene_files:
            lines.append("scenes/：")
            lines.extend(f"- {p}" for p in scene_files)
        if cfg.is_file():
            lines.append("- config/game_config.json（tuning / theme / enabled_skills）")
        lines.append("")
    skills = load_optional_skills_entries(genre)
    lines.append(f"### 预制技能（最多 {load_optional_skills_max()} 个，写 tuning.enabled_skills）")
    if skills:
        for sid, label, desc in skills:
            lines.append(f"- {sid} · {label}：{desc}")
    else:
        lines.append("- （无）")
    lines.append("")
    playbook = _GENRE_PLAYBOOK.get(genre, "")
    if playbook:
        lines.append("### 接线 playbook")
        lines.append(playbook)
        lines.append("")
    contract = load_contract(genre)
    lines.append(format_contract_for_prompt(contract))
    return "\n".join(lines)


def genre_context_as_system_suffix(templates_dir: Path, genre: str) -> str:
    try:
        return build_genre_llm_context(templates_dir, genre)
    except OSError:
        return (
            f"genre={genre}（结构扫描失败）。仍禁止改 templates；"
            "可改会话 core/config/scenes；沙箱仅用契约桥 API。"
        )
