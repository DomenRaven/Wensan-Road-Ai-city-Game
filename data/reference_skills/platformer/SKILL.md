# Reference · platformer

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 主场景 | `scenes/main.tscn` |
| 关卡 | `core/level_01.gd` 程序化 `_build_procedural_content` / `_add_coin` |
| 管理 | `core/game_manager.gd`（金币计数） |
| 玩家 | `core/player_platformer.gd`（group=player） |
| 收集 | `core/collectible.gd` → collected → manager |
| 敌人 | `scenes/patrol_enemy.tscn` 等；光球 `enemy_orb.gd` → `player.notify_hazard` |

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 加金币/变多 | 调 `coin_chance` 或 `_add_coin` 循环（走收集链） |
| 每 N 金币无敌加速 | game_manager 计数或桥 watch_coins + 会话逻辑 |
| 二段跳/下砸 | `has_skill("double_jump"|"ground_pound")` + 桥下落段；触屏说明 |
| 怪物变小 | 缩 AnimatedSprite/Sprite 视觉；碰撞体保持原大小 |

## 工作法

- 改已有脚本：先 read，再最小 targeted 编辑，保留收集链与受伤链  
- 找玩家：group=player 或桥 get_player_node()  
