# 更新日志

本文件记录 [文三路 AI 游戏创作工坊](https://github.com/DomenRaven/Wensan-Road-Ai-city-Game) 的版本里程碑。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

> 工作树快照（相对 tag `v1.2`）：[`开发文档/AI改游戏智能体_工作进度与快照_2026-07-20.md`](开发文档/AI改游戏智能体_工作进度与快照_2026-07-20.md)（HEAD `a0f7b31`）

### 变更

- **7.21 教学案例 · 机房 S2-路B 部署**：[`7.21_教学案例_机房S2路B部署_工作历程与经验_2026-07-21.md`](开发文档/7.21_教学案例_机房S2路B部署_工作历程与经验_2026-07-21.md) · Skill [`.cursor/skills/gameforge-lab-s2-deploy/`](.cursor/skills/gameforge-lab-s2-deploy/SKILL.md) · 服务器 §1–§7 · §9 · v1.0.1 · deploy v2 · 双账号
- **7.21 学生机批量 deploy v2**：一键脚本先 `net use Z:` 再 `Z:\_tools` 复制；修复 UNC 直拷 / `net delete` 误中断；[`学生机_巡检表.md`](机房部署现场记录/学生机_巡检表.md) 含 TEST1/SMB 说明
- **7.21 教学机房 §9 PASS + 助手 v1.0.1 热修**：首台学生机全链路验收（登录 → 试玩自动开 Godot → 首轮关窗弹榜 → AI 改代码 → release）；修复 Windows `Path("Z:")` 映射 bug（`Z:session` → `Z:\session`）；现场记录 [`机房部署现场记录/2026-07-21_§9验收与助手v1.0.1热修.md`](机房部署现场记录/2026-07-21_§9验收与助手v1.0.1热修.md) · 学生机一键部署脚本入 [`学生机_巡检表.md`](机房部署现场记录/学生机_巡检表.md)
- **7.21 教学机房助手（S2-路B）**：`GameForgeLabHelper.exe` + `lab_godot_helper.py`（本机 `:17890` 开 Godot / 关窗榜单）；`GameForgeLabServer.exe` + `launch_lab_server.py`（服务器 `0.0.0.0` 启 API/Kiosk）；打包 `pack_lab_helper_zip.ps1` · `build_lab_server_launcher.ps1`；Kiosk `edu-wizard.js` LB-2 首轮自动弹榜；部署文档 `7.21_教学机房_*` · 现场记录 `机房部署现场记录/`
- **7.21 总控续工 + 交付包刷新**：[`7.20_AI改游戏智能体_新窗对接_总控续工_2026-07-21.md`](开发文档/7.20_AI改游戏智能体_新窗对接_总控续工_2026-07-21.md)；机房 S2-路B 检查清单索引；`pack_exhibition_delivery` → `GameForge-K12-v1.2-server-20260721.zip`
- **教学案例（2026-07-20）**：[`7.20_教学案例_Agent预言机与虚空Done闭环_工作历程与经验_2026-07-20.md`](开发文档/7.20_教学案例_Agent预言机与虚空Done闭环_工作历程与经验_2026-07-20.md)；Cursor Skill `.cursor/skills/gameforge-agent-oracle-gates/`
- **HF-15.1 虚空 Done / 同错早停（P0 已落地）**：非法 evidence（`.tscn` 当 symbol、`wired_by` 含 `->`）硬拒；新符号须本轮 `written_paths`；同错≥3 强制 partial 早停；`replace_text` 附 `symbols_added`；`self_check` 未过则同轮 `done` 合并门禁。单测 `test_hf15_1_hollow_done.py`；验收簇 **28 passed**（hf15_1+hf15+hf14）。规范：`开发文档/7.20_AI改游戏智能体_HF-15.1_虚空Done早停_*`
- **HF-15 预言机分层 P0 已落地**：`assert_presentation_predicates` + L1 多 caller/间接/拒非法 `wired_by`；接入 `run_done_gates`；`_PRESENTATION_WORK_TIP`；单测 `test_hf15_oracle_layers.py`。验收簇 **22 passed**。总纲 G13。规范：`开发文档/7.20_AI改游戏智能体_预言机分层_*`
- **HF-14 证据验收闭环（S1–S5 已落地）**：`done`/`self_check` 交 `evidence[]`；`assert_evidence_wired` 机器核定义+`_process`/Timer 接线；反馈轮无真 diff / 近亲 summary 硬回灌；tip 改为 wired_by 导向。合成单测 `tests/test_hf14_evidence.py`。规范：`开发文档/7.20_AI改游戏智能体_证据验收闭环_*`
- **Agent Live 盯盘**：`.agent/live_trace.jsonl` + `05-工具脚本/watch_agent_live.py`（须跟最新 session）
- **HF-14 立项纪要（保留）**：纠偏 AG-1（半成品接线，非语义套错）；校验见 `7.20_HF-14_文档真实性与一致性校验_2026-07-20.md`
- **可用性热修 LB-2 / Diff / 无敌探针（2026-07-20）**：仅首轮未改局关窗自动弹榜（AI 改成功后关闭）；改后全文改动文件标记加粗 + hunk context 浅绿消斑马线（见 `开发文档/7.20_可用性热修_榜单Diff与无敌探针_2026-07-20.md`）
- **服务器部署包刷新**：清理 reports/探针缓存；Live 探针脚本归档 `_dev_archive`；`pack_exhibition_delivery.ps1` 含 `data/reference_skills`；新增 [`服务器部署_AI智能体自动部署手册_v1.3.md`](开发文档/服务器部署_AI智能体自动部署手册_v1.3.md)（明确**二维码未实装**须服务器 Agent 补齐）
- **人工可用性基本通过（2026-07-19）**：讲解员本机可用性收口（HF-12 §9.3）；状态文档/开工词/锁定口径同步；pytest **272**；下一手软短板热修
- **异常退出清盘不入库**：`POST /sessions/{id}/release` 默认 `harvest=false`（刷新/关页/beacon 只删 workspace）；讲解员回主页/重置显式 `?harvest=true` 才写 learned_skills；`DELETE` 仍默认 harvest
- **HF-13 Live 首轮闭环 + 文档/前后端对齐**：校准 `e2e_7_19_live_three_tasks.py`；七品类×3 报告齐（r1–r3）；`lint_tscn_godot4` +【换路催写】；对接/锁定/总纲/快照/开工词基线同步；`NlPatchResponse` 透出 `partial`/`agent_rounds`/`rolled_back`；kiosk 徽章对齐；墙钟 360s ↔ 前端超时 420s
- **HF-13 立项**：七品类×三任务真 LLM 并发探针施工规范 + 开工提示词（`开发文档/7.19_…_HF-13_*`）；测→盯→修→再测；交付物=通用 Agent
- **文档口径总同步（2026-07-19）**：对接 / 锁定 / HF-12 DoD / 热修 / 快照 / 开工词对齐；代表 Live（pingpong `144435` · platformer `145357` · shmup `144900` · parkour `140701`）记为保真收口；展厅触屏签字仍暂停
- **HF-12 replace 换行对齐**：`replace_text` 自动对齐 CRLF/LF；唯一命中时陈旧 hash 软忽略；多轮未落盘通用【施工催写】；Live `platformer_coin_condition`（`20260719-145357`）由读盘空转改为 4 轮过门
- **HF-12 通用关键链保真**：`gameplay_critical_paths` 禁 stub 整写（缺失从模板恢复）；done 扫描关键锚点；掉落读盘空转催 `apply_shmup_drop_loot_chain`；Live 探针 `pingpong_color_feedback` 已变为仅改 `ball.gd` 最小 patch（`20260719-144435`）
- **文档分类索引**：`开发文档/README.md` 按时间/功能/类型重写；锁定「探针→通用 Agent」、禁止专修单品类尽善尽美
- **运维清洗**：Learned 脏条目 35→19；inject_probe 仅留 5 份基线；workspace 运行时垃圾清空；旧 Live smoke 归档至 `_dev_archive`；`reports/` 入 `.gitignore`
- **LLM 注入文案泛化清理**：全局 system 去掉 shmup「打敌机→捡掉落」窄句与 ball/laser 示例偏置；可玩性/掉落轮次 tip 正向化；鼠标跟机冲突 Intent 门控 `genre==shmup`；Reference `agent_loop` 强调 `replace_text` 优先
- **HF-12 安全读写闭环（自动闭环已落地）**：分页 read/search/replace；结构化 observations；函数/信号/export/onready/关键链保真；每次代码 mutation 后 Godot 校验与动作回滚；salvage 不交未验收文件；drop-loot LLM 工具化并修正非 shmup 泛化；Catalog 隔离；高信号树；Reference 索引；条件路由优先 C；生产入口离线 probe 9/9；Live 探针持续轮换；**266 passed, 2 skipped**；展厅人工签字仍暂停
- **7.19 总纲落地（代码）**：`max_rounds=16` + 软续杯 +16 + 墙钟 **360s**；关 catalog express；harvest 否定态不入库；Reference Skill 注入；脏 Learned 降权；**条件门禁**（每N/加快禁仅 enable）；前端 nl-patch 超时 420s；**HF-11 开放读盘**（取消 B≡窄故障提示、本局改动注入、salvage 去「脚步」；LLM 可读提示改为正向工作法）
- **7.19 总纲（文档）**：有 Key 第 1 轮起 LLM 多工具全开；放宽硬轮次；读盘优先；终局未修复不准有效 Learned Skill；Reference 策展包（见 `开发文档/7.19_AI改游戏智能体_总体设计需求_v1.0.md` · `data/reference_skills/`）
- **7.19 秒哒式自由创作（主路径 + HF-12 自动闭环已落地）**：有 Key 时禁止 catalog 点名快车道；Catalog 降为 Skill 参考；整句 goals 优先；下一门槛为 Live/人工矩阵
- **智能体自由创作**：契约/提示改为「会话 core/scenes 主路径」；幻想 API 不再硬劝退；默认意图走自由创作
- **去伪降级**：有 `LLM_API_KEY` 时 **只走** `run_game_agent`（失败重试后诚实 `provider=agent`）；**禁止**再掉进旧 `_call_llm` / stub；无 Key 才用离线 stub
- **对话对齐 DeepSeek 体验**：本轮原话置顶；强制 `understanding` + `goals[]`；多 goals 覆盖 summary；同会话带历史；UI 展示理解/拆解
- **故障反馈**：人物消失/白屏等 → Intent B 诊断修盘，禁止叠无关 buff；故障局 done 门禁软化
- **门禁纳入 Godot 冒烟自愈**：本轮改 `.gd/.tscn` 强制 `dry_run_godot`，错误（含 `at:` 定位）回灌 LLM；`None/True/False` 静态拦截
- **HF-8 不上锁**：轮次/门禁耗尽 → `_salvage_agent_return` 尽力交付或回滚保加载，禁「没改成」劝退
- **HF-9 失败语义闭环**：坏 JSON/业务异常软继续；故障局回滚诚实话术
- **HF-10 玩家可见/可控（七品类）**：静态门禁 + write 拦截 + last_playable；覆盖七品类（含 PlayerPaddle）
- **项目瘦身**：清理 workspace 运行时报告/证书令牌、根目录重复部署手册与一次性验收 docx、pytest 缓存与 learned_skills 体验运行时

### 新增

- **HF-12 施工与验收 SSOT**：`开发文档/7.19_AI改游戏智能体_HF-12_安全读写闭环_待修复与施工方案.md`（自动闭环已完成；保留 Live/人工矩阵）
- **7.19 总纲 + Reference Skills**：`开发文档/7.19_AI改游戏智能体_总体设计需求_v1.0.md` · `data/reference_skills/`（七品类 + 通识，对照本仓库微调）
- **7.19 文档包**：秒哒式需求说明 / 执行规范 / 开工提示词（`开发文档/7.19_AI改游戏智能体_秒哒式自由创作_*_v1.0.md`）
- **掉落物快车道（shmup）**：激光/炸弹「掉落才开」与通用掉落（爱心等）语义分流；`assert_drop_loot_done`
- **七品类真·LLM E2E**：`05-工具脚本/e2e_7_18_live_three_tasks.py`（7×3 全绿）
- **热修手册**：`开发文档/7.18_AI改游戏智能体_热修手册.md`（HF-1…HF-10）
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
