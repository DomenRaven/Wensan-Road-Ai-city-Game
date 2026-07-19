# Reference Skills · 来源与裁剪说明

> 本包为**人工策展**，非运行时爬虫。吸收公开资料中的可复用原则后，按 GameForge 七品类会话副本路径重写。

## 白名单来源（2026-07-19）

| 源 | URL / 标识 | 吸收什么 | 明确不吸收 |
|----|------------|----------|------------|
| GD-Agentic-Skills · godot-master | https://github.com/thedivergentai/gd-agentic-skills | 强类型、信号总线节制、MCP 验证、稳妥取节点 | 联机、庞大 ECS、与本模板冲突的目录重构 |
| GD-Agentic-Skills · foundations | 同上 repo | snake_case 文件 / PascalCase 节点、%UniqueName 思想 | 「按 feature 重排整个 templates」 |
| Godot 官方 GDScript 风格指南 | docs.godotengine.org | 命名与类型习惯 | — |
| GodotAgentTools / godot-mcp 实践 | 社区 MCP 项目说明 | 「先结构后行为、跑项目验错」 | 在会话外改 editor 全局 |
| 本仓库 playbook | `backend/.../genre_context.py` | 品类真实接线与工作法 | — |
| 本仓库热修 | HF-8/9/10/11 等 | 软继续、玩家健康、开放读盘 | — |

## 对本产品的裁剪

1. 可写范围仅会话 workspace；templates 只读参考。  
2. 找玩家：`group=player` 或桥 `get_player_node()`；乒乓用 `PlayerPaddle`。  
3. 最小 targeted 编辑；保留碰撞/收集/信号链。  
4. 单机触屏试玩；桥 API 以契约列表为准。  
5. Catalog enable 可作捷径；带条件需求在会话脚本写出条件本身。  
