# 品类模板库

每个品类 = **一套预制 core 逻辑** + **一份 `config/game_config.json`**。

AI 创作时：**复制整目录 → 只改 config 的 tuning/theme → 换素材**。

## 目录结构（每个品类）

```
templates/{genre}/
├── config/
│   └── game_config.json       ← AI 主要编辑目标
├── core/                      ← 🔒 人工预制，AI 禁止改
├── data/
├── scenes/
├── assets/ -> 或引用全局 assets/kenney/
└── project.godot
```

## 品类与核心预制重点

| 目录 | 核心预制（core 层） | AI 常改（tuning 层） |
|------|---------------------|----------------------|
| `shooter/` | 八向移动平滑、AABB 命中、波次刷怪 | 速度、射速、敌人数值 |
| `tower_defense/` | 网格放置规则、伤害公式、波次调度 | 塔/敌人数值、经济 |
| `racer/` | 自动跑、跳跃缓冲、障碍生成规则 | 速度、障碍密度 |
| `platformer/` | 加速摩擦、coyote、可变高度跳 | 移速、跳跃力、关卡 |
| `life_sim/` | 点击热区、线性任务链 | 任务文案、物品 |
| `puzzle/` | 物品组合规则表 | 谜题表、线索文案 |
| `casual/` | 子玩法逻辑、计分公式 | 下落速度、刷怪率 |

详细参数表见：`开发文档/模板引擎/品类核心参数规格_v1.0.md`

## 状态

| 品类 | 状态 |
|------|------|
| platformer | 🔲 W1 待建 |
| shooter | 🔲 W2 待建 |
| tower_defense | 🔲 W3 待建 |
| 其余 | 🔲 W4 待建 |
