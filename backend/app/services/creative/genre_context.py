"""各品类项目结构与接线说明 · 注入 LLM（可改会话 core；templates 只读）。"""

from __future__ import annotations

from pathlib import Path

from app.services.config_builder import load_optional_skills_entries, load_optional_skills_max
from app.services.creative.agent_contracts import format_contract_for_prompt, load_contract

# 人工维护接线 playbook；深度对齐 platformer；禁止「禁止改会话 core」旧表述。
_GENRE_PLAYBOOK: dict[str, str] = {
    "platformer": """
【platformer 玩法接线 · 精确架构（改前先 read_file 对应文件）】
- 主场景 res://scenes/main.tscn；GameManager(core/game_manager.gd) + core/level_01.gd 程序化建关
- 【金币】不是手摆在场景里，而是 core/level_01.gd 的 `_build_procedural_content()` 按 `_level_profile.coin_chance` 调 `_add_coin(pos)` 程序化生成。
  · 要「加金币 / 金币变多」：调大 level 的 coin_chance（`_build_level_profile` 里 `coin_chance`），或在 `_build_procedural_content` 循环里多调 `_add_coin(...)`；**别新建独立场景摆金币**，那样不会进收集链
  · 收集链：collectible.gd `_on_body_entered`(player 组)→`collected` 信号→level `_register_collectible_with_manager`→game_manager `_on_collectible_collected()`（`_coins += 1`）。要「每 N 金币触发」在 game_manager 计数或用桥 watch_coins
- 【敌人/受伤】敌人场景 scenes/patrol_enemy.tscn / tough / jumper / turret；红怪光球 core/enemy_orb.gd 命中调 `player.notify_hazard("enemy")`；玩家受伤在 player_platformer.gd `notify_hazard()`（有 `_is_invincible`/`_hurt_area`/`_stomp_area`）
  · 要「怪物变小」：只改敌人 **AnimatedSprite2D/Sprite2D 的 scale 或帧**；**绝不要**改敌人 CharacterBody2D 根节点或 CollisionShape2D 的 scale/大小——那会破坏踩踏判定、碰撞与受伤（子弹卡住/不扣血就是这样来的）
- 二段跳/下砸：has_skill("double_jump"|"ground_pound")；桥已对下落段补二段跳
- 【铁律】改已有 core/*.gd 用**最小 targeted 编辑**：read_file 后只改相关函数/行，禁止整文件重写（会丢碰撞/受伤/信号/收集逻辑，导致金币收不到、子弹卡住不扣血）
- 找玩家：group=player 或 AiSandboxBridge.get_player_node()；开局在 LevelRoot 下，**禁止** ../Player、/root/Main/Player
- 禁止玩家根 visible=false / modulate.a=0 / queue_free；无敌闪烁只改 Sprite 且须恢复
- 需求对齐：summary 声称的能力必须真落在对应文件（加金币→level_01.gd 有改；勿口头声称）
- 【可改】会话副本 core/*.gd、config、scenes；【禁止】templates/**
""".strip(),
    "shmup": """
【shmup 玩法接线 · 与 platformer 同级深度】
- 主场景射击；玩家 Area2D · core/player_ship.gd + scenes/player.tscn（group=player）
- 开局后挂载：/root/Main/GameRoot/<game>/Player（不在 Main 直属！）
- 找玩家：get_tree().get_nodes_in_group("player") 或 AiSandboxBridge.get_player_node()；
  **禁止** get_node("../Player")、/root/Main/Player（会找不到节点，后续乱改易让人物消失）
- hooks：core/shmup_hooks.gd 用 group 接线；勿臆造相对路径；勿对玩家 visible=false / queue_free
- 自动射击；左右移动；子弹池 core/bullet_pool.gd → spawn_player_bullet / spawn_enemy_bullet
- 子弹外观 core/bullet.gd activate()；改颜色勿发明 set_color——用桥 tint_player_bullets / rainbow_player_bullets
- 预制技能仅 bomb、laser_beam（enabled_skills）；输入见 skills/*.gd
- 护盾：【不是】catalog 技能；机体捡道具 "shield" 或桥 grant_temp_shield(seconds)；ShieldSprite.visible 可 false，**玩家根节点不可**
- 【鼠标冲突】飞机用左键跟机；点技能按钮会抢输入。须 patch_mouse_steer_guard / 会话 player_ship 守卫；禁止只重复 enable 技能
- 【铁律】改 player_ship.gd 用最小 targeted 编辑，禁整文件重写（会丢碰撞/射击/无敌闪烁恢复）
- 【可改】会话 core/player_ship.gd、bullet.gd、bullet_pool.gd、config、scenes；【禁止】templates/**
- 示例「五颜六色子弹」：ai_sandbox + rainbow_player_bullets，或直接改 bullet 生成链
- 【展厅硬性】按钮技能：how_to_play 写「点屏幕下方 炸弹/激光 按钮」；ShmupTouch 只负责移动
- 【掉落物例外】用户要「敌机掉落才开」：powerup_types 加 laser/bomb + apply_powerup 内
  追加 GameConfig.enabled_skills 并 AiSandboxBridge.ensure_touch_skill_buttons；
  勿动 enemy_spawner/main.tscn；how_to_play 写「打敌机→捡掉落」；禁 enable_catalog 冒充
""".strip(),
    "survivor": """
【survivor 玩法接线】
- 玩家：core/player_survivor.gd + scenes/player.tscn（Area2D；_ready 里 add_to_group("player")）
- 开局后在 GameRoot 动态实例下；找玩家用 group=player / get_player_node()；禁止 ../Player、/root/Main/Player
- hooks：core/survivor_hooks.gd；禁对玩家 visible=false / queue_free；禁删 add_to_group("player")
- catalog：magnet / nova（捷径）；新机制写会话 core；【铁律】最小编辑，禁整写玩家脚本
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "parkour": """
【parkour 玩法接线 · 精确架构】
- 玩家：core/player_runner.gd + scenes/player.tscn（CharacterBody2D · group=player · 默认约 (100,300)）
- 开局后挂载：/root/Main/GameRoot/<game>/Player（不在 Main 直属！）
- 找玩家：get_nodes_in_group("player") 或 AiSandboxBridge.get_player_node()；
  **禁止** get_node("../Player")、/root/Main/Player（EduHooks 相对 Main 找不到 Player）
- hooks：core/parkour_hooks.gd 已用 group 接线；改机制优先写 ai_sandbox / 桥 API，少改 hooks 路径
- 操控依赖 player_runner 的 `_playing` / set_playing；搞坏会「看得见也可能不能跳」
- 无敌闪烁只改 `_sprite.modulate.a` 且须恢复；禁止玩家根 visible=false / modulate.a=0 / queue_free
- catalog 捷径：double_jump / slide；二段跳下落段可由桥补齐；加速可用桥或最小改 player_runner
- 【铁律】改 player_runner.gd / player.tscn 用最小 targeted 编辑，禁整文件重写
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "pingpong": """
【pingpong 玩法接线】
- 操控拍：scenes/game.tscn 的 PlayerPaddle + core/paddle.gd（不是 scenes/player.tscn）
- 接线：match_controller.gd 的 $PlayerPaddle；禁止 get_node("../Player") / /root/Main/Player
- 保留 PlayerPaddle 下 Visual/Sprite；勿 visible=false 藏拍；catalog：power_smash / curve_ball
- 【铁律】最小编辑 paddle/match_controller/ball；【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "fighting": """
【fighting 玩法接线】
- 玩家：core/player_fighter.gd（继承 fighter.gd）+ scenes/player.tscn（group=player · AnimatedSprite2D）
- 开局在擂台实例下；找玩家用 group=player / get_player_node()；禁止 ../Player、/root/Main/Player
- hooks：core/fighting_hooks.gd；禁玩家根 visible=false / queue_free；catalog：block_parry / special_uppercut
- 临时霸体可用桥；新招式写会话 core；无血腥；【铁律】最小编辑，禁整写 fighter/player_fighter
- 【可改】会话 core/config/scenes；【禁止】templates/**
""".strip(),
    "racing": """
【racing 玩法接线】
- 玩家车：core/car_topdown.gd + scenes/player.tscn（Node2D · group=player · Sprite2D）
- 开局在 GameRoot 下；找车用 group=player / get_player_node()；禁止 ../Player、/root/Main/Player
- hooks：core/racing_hooks.gd；禁玩家根 visible=false / queue_free；catalog：boost / drift_snap
- 【铁律】最小编辑 car_topdown / player.tscn；【可改】会话 core/config/scenes；【禁止】templates/**
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
