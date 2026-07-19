# Reference · survivor

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 玩家 | `core/player_survivor.gd` + `scenes/player.tscn`（Area2D · `_ready` add_to_group("player")） |
| 武器 | `core/auto_weapon.gd` |
| 刷怪 | `core/horde_spawner.gd` |
| XP | `scenes/xp_gem.tscn` |
| Hooks | `core/survivor_hooks.gd` |
| Catalog | magnet / nova |

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 吸经验 | magnet 技能 + 吸附半径真实变化；图标/how_to_play |
| 清屏/新星 | nova 接线或会话写范围伤害 |
| 新武器机制 | 会话改 auto_weapon / 沙箱；保留 add_to_group("player") |

## 工作法

- 最小编辑玩家脚本；找玩家用 group/桥  
