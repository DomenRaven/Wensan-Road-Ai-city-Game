# Reference · parkour

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 玩家 | `core/player_runner.gd` + `scenes/player.tscn`（CharacterBody2D · group=player） |
| Hooks | `core/parkour_hooks.gd`（group 接线） |
| 障碍/收集 | `obstacle_spawner` / `collectible_spawner` |
| Catalog | double_jump / slide |

## 找玩家

- group=player / 桥 get_player_node()；开局在 GameRoot 下  

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 二段跳/滑铲 | skill + 确认 `_playing`/set_playing；桥可补下落段二段跳 |
| 加速 | 桥或最小改速度字段 |
| 看得见不能跳 | 查 `_playing` / 输入 / 碰撞；根节点保持可见 |

## 工作法

- 无敌闪烁只改 `_sprite.modulate.a` 并恢复  
- 改 runner：最小 targeted 编辑  
