# Reference · pingpong

> `verified_against_templates: true`（架构对齐，非单局试玩证明）

## 真结构（改前 read）

| 角色 | 路径 |
|------|------|
| 操控拍 | `scenes/game.tscn` → **PlayerPaddle** + `core/paddle.gd` |
| 球 | `core/ball.gd`（`_hit_count` / `hits_per_speed_ramp`） |
| 对局 | `core/match_controller.gd`（`$PlayerPaddle`） |
| AI 拍 | `core/ai_paddle.gd` |
| Catalog 脚本 | `core/skills/power_smash.gd`、`curve_ball` 等 |

## 找节点

- 用 match 里的 PlayerPaddle（不是 `scenes/player.tscn`）  
- 保留拍下 Visual/Sprite；根节点保持可见  

## 常见需求落点

| 用户说法 | 推荐落点 |
|----------|----------|
| 大力扣杀 | 读 `power_smash.gd` + paddle/ball；确认触屏按钮与球速 |
| 每接 3 球扣杀一次、球很快 | 在 paddle/ball 做接球计数充能；触发后抬球速；可调 AI 反应 |
| 球越打越快 | 调 `hits_per_speed_ramp`（config 或 ball 逻辑） |
| 外观/状态没恢复 | 读本局近期改动的 paddle/ball，核对状态是否成对开闭 |

## 工作法

- 改 paddle / ball / match_controller：先 read，再最小编辑  
- 反馈类：对照用户原话与本局近期写入做差分  
