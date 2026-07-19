# Reference · shmup

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 玩家 | `core/player_ship.gd` + `scenes/player.tscn`（group=player） |
| 子弹池 | `core/bullet_pool.gd` → spawn_player_bullet / spawn_enemy_bullet |
| 子弹外观 | `core/bullet.gd` `activate()` |
| Hooks | `core/shmup_hooks.gd` |
| Catalog | bomb / laser_beam（`core/skills/`） |
| 掉落 | `powerup_pickup` + `powerup_types`（掉落开技能走拾取链） |

## 找玩家

- `get_nodes_in_group("player")` 或桥 `get_player_node()`  
- 开局多在 `/root/Main/GameRoot/<game>/Player`  

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 激光/炸弹 | enable 或会话实现 + 触屏按钮；how_to_play「点下方按钮」 |
| 五颜六色子弹 | 桥 `rainbow_player_bullets` / tint，或改 bullet 生成链 |
| 护盾 | 道具 shield 或桥 `grant_temp_shield`；玩家根保持可见 |
| 敌机掉落才给技能 | powerup_types + apply_powerup 写 enabled_skills + ensure_touch_skill_buttons |
| 鼠标点按钮飞机乱飞 | `patch_mouse_steer_guard` / 会话守卫 |

## 工作法

- 改 `player_ship.gd`：最小 targeted 编辑，保留碰撞/射击/闪烁恢复  
