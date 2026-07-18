# 更新日志

本文件记录 [文三路 AI 游戏创作工坊](https://github.com/DomenRaven/Wensan-Road-Ai-city-Game) 的版本里程碑。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

> 工作树快照（相对 tag `v1.2`）：[`开发文档/AI改游戏智能体_工作进度与快照_2026-07-18.md`](开发文档/AI改游戏智能体_工作进度与快照_2026-07-18.md)

### 变更

- **智能体自由创作**：契约/提示改为「会话 core/scenes 主路径；桥与 catalog 为捷径」；幻想 API 不再硬劝退，改为继续让 LLM 用 GDScript 实现；默认意图走自由创作
- **去伪降级**：有 `LLM_API_KEY` 时 **只走** `run_game_agent`（失败重试后诚实 `provider=agent`）；**禁止**再掉进旧 `_call_llm` / stub；无 Key 才用离线 stub
- **对话对齐 DeepSeek 体验**：本轮原话置顶；强制 `understanding` + `goals[]`；多 goals 覆盖 summary；同会话带历史；UI 展示理解/拆解
- **故障反馈**：人物消失/白屏等 → Intent B 诊断修盘，禁止叠无关 buff；故障局 done 门禁软化
- **门禁纳入 Godot 冒烟自愈**：本轮改 `.gd/.tscn` 强制 `dry_run_godot`，错误（含 `at:` 定位）回灌 LLM；`None/True/False` 静态拦截
- **HF-8 不上锁**：轮次/门禁耗尽 → `_salvage_agent_return` 尽力交付或回滚保加载，禁「没改成」劝退
- **HF-9（进行中）**：坏 JSON 仍上锁 + 回滚到「已坏可加载」基线却假安慰——见热修手册；本提交先落文档，代码紧随
- **项目瘦身**：清理 workspace 运行时报告/证书令牌、根目录重复部署手册与一次性验收 docx、pytest 缓存与 learned_skills 体验运行时

### 新增

- **掉落物快车道（shmup）**：激光/炸弹「掉落才开」与通用掉落（爱心等）语义分流；`assert_drop_loot_done`
- **七品类真·LLM E2E**：`05-工具脚本/e2e_7_18_live_three_tasks.py`（7×3 全绿）
- **热修手册**：`开发文档/7.18_AI改游戏智能体_热修手册.md`（HF-1…HF-9）
- **P0-通用工作流（条件通过）**：`intent_router`（A/B/C/D）· 七品类契约 `runtime` · `assert_catalog_runtime` · 桥 `ensure_touch_action` · Agent 注入路由
- 单测扩：`test_intent_router` / `test_agent_contracts` / `test_catalog_express_all_genres` 等
- **Live 可感知矩阵** `05-工具脚本/live_perceivable_matrix.py`

### 既有变更

- Kiosk nl-patch：禁自动 `onReplay`，保留「现在重开游戏」
- **L3 收紧**：`assert_catalog_runtime` 去掉「无 core 即放行」
- **shmup 触屏收敛**：炸弹/激光走桥 HUD

### 文档

- **AI 改游戏智能体需求升至 v1.2**；工作方向锁定 / 映射 / 施工 / 开工 v3
- **进度·足迹·快照**：`开发文档/AI改游戏智能体_工作进度与快照_2026-07-18.md`
- 索引：`文档目录说明.md` / `README.md` / `.cursor/rules/godot-mini-game.mdc`

### 建议人手补签

- 展厅实机：新开一局 → 短对话 → 手动重开 → 点屏技能可感（旧 workspace 需重做才注入）

---

## [1.2] - 2026-07-06

### 新增

- **P4-B 七款全触控**：platformer / parkour / survivor / pingpong / shmup / racing / fighting 触控 overlay · `e2e_b_edu_batch` 6/6
- **P4-C 展厅 UI**：B1 碰撞泡泡 · B2 名字填空 · 揭幕烟花 · B4 卡片轮播 · B5 品类剧场 · 证书 PNG+扫码 · 七款日榜
- **日榜 API**：`leaderboard_daily` · `leaderboard.js` · 七款 hooks 记分 · 页眉榜单钮
- **触控键盘热修**：`touch-keyboard.js` · `tabtip_native` · `?v=7.4-c07-14` / `7.4-c08-02`

### 变更

- `kiosk/edu/` 全线 UI 组件与 `edu-styles.css` 局部 accent（全页保持蓝白）
- `e2e_recipe_a_certificate.py` · `e2e_b_edu_batch.py` 适配 P4-C 新向导流
- `backend/` 会话补丁 · 证书公网 token · 日榜持久化
- **部署手册 v1.2** · **启动游戏工坊.exe 启动器 v1.2**（端口复用 · bind 127.0.0.1）

### 说明

- **P4-A Godot 内嵌**：挂起 · 继续 v1.1 P3-3 外置窗
- **C-08 扫码**：API 就绪 · **展馆公网域名待配**
- **templates/core**：未改
- **tag `v1.2`**：已打 tag / push（2026-07-06）
- **部署包**：`请先读_展厅部署与操作.md` · `软件操作说明书_v1.2` · `展厅本地服务器_AI一键部署说明_v1.2` · `deploy_exhibition.ps1` / `pack_exhibition_delivery.ps1`

| 项 | 值 |
|----|-----|
| 收工评审 | `开发文档/模板引擎/评审记录/7.4_验收记录.md` |
| 状态快照 | `开发文档/模板引擎/快照/7.4_收工后状态快照_v1.0.md` |
| 功能验收 | 根目录 `AI学习小游戏创作-功能验收文档.docx` v1.2 |
| 部署手册 | `开发文档/部署手册_v1.2.md` |

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

[1.2]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.2
[1.1]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.1
[1.0]: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game/releases/tag/v1.0
