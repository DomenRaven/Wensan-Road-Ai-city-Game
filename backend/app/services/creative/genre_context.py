"""各品类项目结构与接线说明 · 注入 LLM（可改会话 core；templates 只读）。"""

from __future__ import annotations

from pathlib import Path

from app.services.config_builder import load_optional_skills_entries, load_optional_skills_max
from app.services.creative.agent_contracts import format_contract_for_prompt, load_contract

# 人工维护接线 playbook；正向工作法（改前先 read_file）
_GENRE_PLAYBOOK: dict[str, str] = {
    "platformer": """
【platformer 玩法接线 · 改前先 read_file】
- 主场景 res://scenes/main.tscn；GameManager(core/game_manager.gd) + core/level_01.gd 程序化建关
- 【金币】在 core/level_01.gd `_build_procedural_content()` 按 `_level_profile.coin_chance` 调 `_add_coin(pos)` 生成
  · 「加金币」：调大 coin_chance，或在循环里多调 `_add_coin(...)`（走收集链才会计分）
  · 收集链：collectible → level `_register_collectible_with_manager` → game_manager `_on_collectible_collected`
- 【敌人/受伤】scenes/patrol_enemy 等；命中 `player.notify_hazard`；受伤在 player_platformer.gd
  · 「怪物变小」：改敌人 Sprite/AnimatedSprite 的 scale 或帧（碰撞体保持原大小，踩踏判定才稳）
- 二段跳/下砸：has_skill("double_jump"|"ground_pound")；桥可对下落段补二段跳
- 改已有 core/*.gd：read_file 后只改相关函数/几行（保留碰撞、受伤、信号、收集）
- 找玩家：group=player 或 AiSandboxBridge.get_player_node()（开局在 LevelRoot 下）
- 闪烁类效果只改 Sprite 并恢复；根节点保持可见与 group=player
- summary 声称的能力对应磁盘改动（加金币→level_01.gd 有改）
- 可写：会话 core/*.gd、config、scenes（templates 只读参考）
""".strip(),
    "shmup": """
【shmup 玩法接线】
- 玩家 Area2D · core/player_ship.gd + scenes/player.tscn（group=player）
- 开局挂载：/root/Main/GameRoot/<game>/Player
- 找玩家：get_nodes_in_group("player") 或 AiSandboxBridge.get_player_node()
- hooks：core/shmup_hooks.gd 用 group 接线
- 自动射击；子弹池 core/bullet_pool.gd → spawn_player_bullet / spawn_enemy_bullet
- 子弹外观 core/bullet.gd activate()；改色用桥 tint_player_bullets / rainbow_player_bullets
- 预制技能：bomb、laser_beam（Skill 参考 / enabled_skills）
- 护盾：机体捡 "shield" 或桥 grant_temp_shield；ShieldSprite 可隐藏，玩家根保持可见
- 【鼠标与技能键】左键跟机会与技能按钮抢输入 → patch_mouse_steer_guard + 会话守卫
- 改 player_ship.gd：最小编辑，保留碰撞/射击/闪烁恢复
- 可写：会话 core/player_ship.gd、bullet.gd、bullet_pool.gd、config、scenes
- 按钮技能试玩：how_to_play 写「点屏幕下方 炸弹/激光 按钮」；ShmupTouch 负责移动
- 【掉落才开】powerup_types 加 laser/bomb；apply_powerup 拾取后追加 enabled_skills + ensure_touch_skill_buttons；
  how_to_play 写「打敌机→捡掉落」；保留 enemy_spawner 的 request_powerup 管道
""".strip(),
    "survivor": """
【survivor 玩法接线】
- 玩家：core/player_survivor.gd + scenes/player.tscn（Area2D；_ready 里 add_to_group("player")）
- 开局在 GameRoot 下；找玩家用 group=player / get_player_node()
- hooks：core/survivor_hooks.gd；根节点保持可见与 group=player
- catalog：magnet / nova（Skill 参考）；新机制写会话 core；最小编辑玩家脚本
- 可写：会话 core/config/scenes
""".strip(),
    "parkour": """
【parkour 玩法接线】
- 玩家：core/player_runner.gd + scenes/player.tscn（CharacterBody2D · group=player）
- 开局：/root/Main/GameRoot/<game>/Player
- 找玩家：get_nodes_in_group("player") 或 AiSandboxBridge.get_player_node()
- hooks：core/parkour_hooks.gd；改机制优先 ai_sandbox / 桥 API
- 操控依赖 `_playing` / set_playing；闪烁只改 `_sprite.modulate.a` 并恢复
- Skill 参考：double_jump / slide；加速可用桥或最小改 player_runner
- 改 player_runner / player.tscn：最小 targeted 编辑
- 可写：会话 core/config/scenes
""".strip(),
    "pingpong": """
【pingpong 玩法接线】
- 操控拍：scenes/game.tscn 的 PlayerPaddle + core/paddle.gd
- 接线：match_controller.gd 的 $PlayerPaddle；球：core/ball.gd
- 保留 PlayerPaddle 下 Visual/Sprite；根节点保持可见
- Skill 参考：power_smash / curve_ball；反馈类先读本局近期改动的 paddle/ball
- 改 paddle / match_controller / ball：最小编辑
- 可写：会话 core/config/scenes
""".strip(),
    "fighting": """
【fighting 玩法接线】
- 玩家：core/player_fighter.gd（继承 fighter.gd）+ scenes/player.tscn（group=player）
- 开局在擂台实例下；找玩家用 group=player / get_player_node()
- hooks：core/fighting_hooks.gd；根节点保持可见；Skill：block_parry / special_uppercut
- 临时霸体可用桥；新招式写会话 core；最小编辑 fighter/player_fighter
- 可写：会话 core/config/scenes
""".strip(),
    "racing": """
【racing 玩法接线】
- 玩家车：core/car_topdown.gd + scenes/player.tscn（Node2D · group=player）
- 开局在 GameRoot 下；找车用 group=player / get_player_node()
- hooks：core/racing_hooks.gd；根节点保持可见；Skill：boost / drift_snap
- 改 car_topdown / player.tscn：最小编辑
- 可写：会话 core/config/scenes
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
        "可写范围：会话 workspace 的 core/**、config/**、scenes/**、assets/**（templates 只读参考）。",
        "done 前：磁盘有实现、桥 API 真实存在、声称与磁盘一致、how_to_play 含重开提示。",
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
            f"genre={genre}（结构扫描失败）。"
            "可改会话 core/config/scenes；桥 API 以契约列表为准。"
        )
