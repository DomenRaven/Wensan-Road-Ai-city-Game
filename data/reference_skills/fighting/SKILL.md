# Reference · fighting

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 玩家 | `core/player_fighter.gd`（继承 `fighter.gd`）+ `scenes/player.tscn` |
| 敌方 | `core/enemy_fighter.gd` |
| 擂台 | `core/fight_arena.gd` |
| 判定 | `hitbox_manager.gd` / `frame_data.gd` |
| Hooks | `core/fighting_hooks.gd` |
| Catalog | block_parry / special_uppercut |

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 格挡/升龙 | 读 skills + 输入/帧数据是否可感 |
| 新招式 | 会话最小改 fighter；可用桥临时霸体 |
| 外观/可见问题 | 读本局近期改动；根节点保持可见，闪烁只改 Sprite |

## 工作法

- 最小编辑 `fighter.gd` / `player_fighter.gd`；找玩家用 group/桥  
