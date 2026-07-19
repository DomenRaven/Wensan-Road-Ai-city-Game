# Reference · racing

> `verified_against_templates: true`

## 真结构

| 角色 | 路径 |
|------|------|
| 玩家车 | `core/car_topdown.gd` + `scenes/player.tscn`（Node2D · group=player） |
| 赛道滚动 | `core/road_scroller.gd` |
| 圈数 | `core/lap_counter.gd` |
| NPC | `core/npc_car.gd` |
| Hooks | `core/racing_hooks.gd` |
| Catalog | boost / drift_snap |

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 加速/漂移 | skills + 车速/漂移参数真实变化 + 触屏说明 |
| 更快/更漂 | 最小改 car_topdown 速度/摩擦力字段或 config |
| 车看不见 | 读近期改动；根节点保持可见，只改 Sprite |

## 工作法

- 找车用 group/桥；改车脚本最小 targeted 编辑  
