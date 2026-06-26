# 更新日志

本文件记录 [文三路 AI 游戏创作工坊](https://github.com/DomenRaven/Wensan-Road-Ai-city-Game) 的版本里程碑。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

---

## [未发布] · P3-1 + P3-1-FIX（2026-06-26）

### 新增

- **P3-1 蓝白主题**：`kiosk_edu_spec` v1.1 · B/A 链蓝白 CSS · 橙金星空 · `edu-create-ambient.js` · B6 试玩卡片
- **P3-1-FIX 讲解员演示区**：七款 `GENRE_DEMO_ACTIONS` · `.pane-right-stack` · survivor 高亮补丁 · shmup B7 无「受伤」

### 变更

- `kiosk/edu/edu-wizard.js` · `code-highlight.js` · `templates/_edu/survivor_hooks.gd` · `edu_action_bridge.gd`

> 正式版本号 **v1.1** 于 P3-4 全量回归后打 tag。

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

### 发布记录

| 项 | 值 |
|----|-----|
| GitHub 首推 | 2026-06-24 · `main` · 约 122 MiB / 11716 objects |
| 标签 `v1.0` | `f7f36cc` |
| `main` HEAD | `7425914`（含 `push_github.ps1`） |
| 状态快照 | `开发文档/模板引擎/快照/6.24_v1.0_GitHub收工状态快照_v1.0.md` |

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
