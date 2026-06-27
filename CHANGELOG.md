# 更新日志

本文件记录 [文三路 AI 游戏创作工坊](https://github.com/DomenRaven/Wensan-Road-Ai-city-Game) 的版本里程碑。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [1.1] - 2026-06-28

### 新增

- **P3-2 横竖屏**：`orientation.js` · dual-pane 横/竖 grid · `godot-zone` 引导区
- **P3-3 Godot 窗口分区**：`play/launch` 携带 `client_viewport` · Win32 `place_by_pid` · 横屏贴右栏 · 竖屏贴主屏下半
- **RECIPE 配方+证书**：删 B4 小技能题 · tuning 增补 · B6 霓虹作品登记证书 · 打印样式
- **E2E**：`e2e_p3_godot_window_layout.py` · `e2e_recipe_a_certificate.py` · `check_recipe_alignment.py`

### 变更

- **P3-1 蓝白主题**：`kiosk_edu_spec` v1.1 · B/A 链蓝白 CSS · 橙金星空 · B6 试玩卡片
- **P3-1-FIX**：七款 `GENRE_DEMO_ACTIONS` · survivor/shmup 高亮补丁
- `kiosk/edu/edu-wizard.js` · `code-viewer.js` · `edu-styles.css` · `godot_launcher.py` · `godot_window_layout.py`
- 冻结：`frozen_recipe_v1.json` · 各品类 manifest 刷新

### 说明

- **LLM**：本期未接入 · P2 展后 backlog
- **templates/core**：未改

| 项 | 值 |
|----|-----|
| 标签 `v1.1` | 见 GitHub releases |
| 收工评审 | `开发文档/模板引擎/评审记录/6.26_P3_收工.md` |
| 状态快照 | `开发文档/模板引擎/快照/6.26_P3_收工后状态快照_v1.0.md` |

---

## [1.0] - 2026-06-24

### 说明

展陈 P0 技术收工基线：**7 款** Godot 游戏、**B 链教育版 kiosk**（B0–B7）、A 链快玩、后端 FastAPI、冻结快照与 E17 人工试玩验收。

### 包含

- **A 链**：`/kiosk/` 七款精选快玩（S0→S9）
- **B 链**：`/kiosk/edu/` 教育向导（意图 → 配方 → 代码剧场 → Godot 试玩高亮）
- **模板**：`templates/` 七款游戏 + `_edu` 钩子与桥接
- **后端**：`backend/` 会话、生成、试玩 launch、actions 轮询
- **工具**：`05-工具脚本/` E2E、冻结快照、RAG、资源脚本
- **文档**：`开发文档/` 全套规格与展陈 P0 窗口记录
- **UI**：B 链深邃星空背景、品类 HTML 动画预览

### 发布记录

| 项 | 值 |
|----|-----|
| GitHub 首推 | 2026-06-24 · `main` |
| 标签 `v1.0` | `f7f36cc` |

### 回退到此版本

```powershell
git fetch github --tags
git checkout v1.0
```

---

[1.1]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.1
[1.0]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.0
