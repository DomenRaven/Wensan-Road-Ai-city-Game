# 更新日志

本文件记录 [文三路 AI 游戏创作工坊](https://github.com/DomenRaven/Wensan-Road-Ai-city-Game) 的版本里程碑。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [1.0] - 2026-06-24

### 说明

展陈 P0 技术收工基线：**11 款 L0 模板**、**7 款精选 R2**、**B 链教育版 kiosk**（B0–B7）、A 链快玩、后端 FastAPI、冻结快照与 E17 人工试玩验收。

### 包含

- **A 链**：`/kiosk/` 七款精选快玩（S0→S9）
- **B 链**：`/kiosk/edu/` 教育向导（意图 → 配方 → 代码剧场 → Godot 试玩高亮）
- **模板**：`templates/` 十一品类 + `_edu` 钩子与桥接
- **后端**：`backend/` 会话、生成、试玩 launch、actions 轮询
- **工具**：`05-工具脚本/` E2E、冻结快照、RAG、资源脚本
- **文档**：`开发文档/` 全套规格与展陈 P0 窗口记录
- **UI**：B 链深邃星空背景、品类 HTML 动画预览

### 回退到此版本

```powershell
git fetch github --tags
git checkout v1.0
```

或在当前分支上硬回退（**会丢弃未提交改动**）：

```powershell
git reset --hard v1.0
```

建议先打备份分支：`git branch backup-before-rollback`

---

[1.0]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.0
