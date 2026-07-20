# AI 改游戏智能体 · 文件映射表 v1

> **对齐**：需求 v1.2 · 施工规范 v1  
> **原则**：改智能体只动下表「可写」列；玩法冻结源只读  

---

## 1. 总览分层

| 层 | 路径模式 | 读写 | 职责 |
|----|----------|------|------|
| 契约 | `config/agent_contracts/{genre}.json` | 可写 | 能力面 / recipe / 禁幻想 API |
| Agent 编排 | `backend/app/services/creative/game_agent.py` | 可写 | 多轮工具、进度、调门禁 |
| 门禁 | `backend/app/services/creative/agent_contracts.py` | 可写 | 加载契约、validate、assert、progress、dry_run；**HF-14** evidence 接线；**HF-15** `assert_presentation_predicates`（P0 ✅） |
| Live 盯盘 | `backend/app/services/creative/agent_live_trace.py` · `05-工具脚本/watch_agent_live.py` | 可写 | 会话 `live_trace.jsonl` 实时监视 |
| 品类说明 | `backend/app/services/creative/genre_context.py` | 可写 | playbook + 注入契约摘要 |
| 入口 API | `backend/app/services/creative/llm_patch.py` · `routers/nl_patch.py` | 可写 | 有 Key→仅 agent；无 Key→stub；进度 GET |
| 会话写权限 | `backend/app/services/agent_workspace.py` | 可写 | 路径红线、禁危险 GD |
| 经验库 | `backend/app/services/creative/learned_skills.py` | 可写 | harvest / 检索 / 降权 / 晋升提案 |
| 意图编译 | `backend/app/services/creative/sandbox_intent.py` | 可写 | stub/补齐用 |
| 意图路由 | `backend/app/services/creative/intent_router.py` | 可写 | A/B/C/D 确定性路由与纠偏 |
| Edu 注入 | `backend/app/services/edu_workspace.py` | 可写 | 复制桥/触控到 workspace、改 main.tscn |
| 桥运行时 | `templates/_edu/ai_sandbox_bridge.gd` | **可写** | 真 API、catalog 激活、着色/护盾 |
| 触控 | `templates/_edu/*_touch_overlay.gd` | **可写** | 品类触屏（目标收敛为通用 API） |
| 窗控件 | `templates/_edu/window_chrome_overlay.gd` | **可写** | 关闭/小窗（半尺寸；无复位） |
| 品类 hooks | `templates/_edu/{genre}_hooks.gd` | 可写 | B7 埋点，非玩法主逻辑 |
| 玩法冻结 | `templates/{genre}/core/**` | **只读** | 禁止改 |
| 会话副本 | `workspace/{session}/**` | Agent 可写 | 本局唯一施工面 |
| 长期库 | `data/learned_skills/**` | 服务写 | 不随 session 销毁 |
| Kiosk | `kiosk/edu/nl-patch-dialog.js` · `llm-create-wait.js` | 可写 | 对话、进度、手动重开；超时 420s；认 gate/partial/rounds |
| 配置 | `backend/app/config.py` | 可写 | `agent_max_rounds=16` · 软续杯 +16 · 墙钟 360s |
| Reference | `data/reference_skills/**` | 可写（策展） | 只读注入 Agent；非 express |
| Live 探针 | `05-工具脚本/e2e_7_19_live_three_tasks.py` | 可写 | HF-13 七品类×3；报告 `reports/live_three_tasks/` |
| 单案探针 | `05-工具脚本/sandbox_llm_inject_probe.py` | 可写 | 注入/Live 深挖 messages |
| 启动窗 | `godot_launcher.py` · `godot_window_layout.py` | 可写 | 全屏 + TOPMOST |
| 单测 | `backend/tests/test_agent_*.py` · `test_hf12_*` · `test_hf13_*` · `test_hf14_evidence.py` · `test_hf15_oracle_layers.py` | 可写 | 门禁/契约/保真/evidence/L2 |
| HF-15 文档切片 | `开发文档/7.20_AI改游戏智能体_预言机分层_*` | 可写 | 需求/施工/执行/开工/映射 |

---

## 2. 按工作流步骤映射

| 步骤 | 主要文件 |
|------|----------|
| 用户发话 | `kiosk/edu/nl-patch-dialog.js` → `POST /sessions/{id}/nl-patch`（超时 420s） |
| 进度轮询 | `GET /sessions/{id}/agent-progress` ← `.agent_progress.json` |
| 启动 Agent | `llm_patch.apply_nl_patch` → `game_agent.run_game_agent`（墙钟 360s；有 Key 禁 express） |
| UI 诚实展示 | `NlPatchResponse` 透出 `gate_passed`/`partial`/`agent_rounds`/`rolled_back`；前端据此徽章；未过门禁不炫 sandbox_files |
| 读契约 | `agent_contracts.load_contract` ← `config/agent_contracts/` |
| 读品类说明 | `genre_context.build_genre_llm_context` |
| 检索经验 | `learned_skills.search_learned_skills` |
| 开预制技能 | `learned_skills.enable_catalog_skill` → `workspace/.../config/game_config.json` |
| 写沙箱/core | `agent_workspace.write_workspace_file` |
| 门禁 | `run_done_gates` / `assert_claims` / `assert_apis_in_contract` / `assert_evidence_wired` /（HF-15）表现谓词 |
| 离线 stub | 仅无 `LLM_API_KEY` 时 `llm_patch` stub（有 Key 失败不降级） |
| 会话诞生注入 | `edu_workspace.apply_edu_workspace_patch` |
| 运行时效果 | `AiSandboxBridge` + 触控 overlay（已注入会话 core） |
| 重开试玩 | 前端手动 → `play/launch` → `godot_launcher` + `window_layout` |
| 回主页 | `harvest_session_experience` → 删 workspace |

---

## 3. 七品类契约与触控文件

| genre | 契约 JSON | 触控 overlay（_edu） | hooks |
|-------|-----------|----------------------|-------|
| platformer | `platformer.json` | `platformer_touch_overlay.gd` | `platformer_hooks.gd` |
| shmup | `shmup.json` | `shmup_touch_overlay.gd` | `shmup_hooks.gd` |
| survivor | `survivor.json` | `survivor_touch_overlay.gd` | `survivor_hooks.gd` |
| parkour | `parkour.json` | `parkour_touch_overlay.gd` | `parkour_hooks.gd` |
| pingpong | `pingpong.json` | `pingpong_touch_overlay.gd` | `pingpong_hooks.gd` |
| fighting | `fighting.json` | `fighting_touch_overlay.gd` | `fighting_hooks.gd` |
| racing | `racing.json` | `racing_touch_overlay.gd` | `racing_hooks.gd` |

共用：`ai_sandbox_bridge.gd` · `window_chrome_overlay.gd` · `edu_action_bridge.gd`

---

## 4. 桥公开 API（运行时可调 · 以契约为准）

通用：`get_player` / `get_player_node` / `get_game_manager` / `watch_coins` / `grant_invincibility` / `boost_move_speed` / `show_countdown` / `flash_player_fx` / `set_tuning_number`  

扩展（已有）：`tint_player_bullets` / `rainbow_player_bullets` / `grant_temp_shield` / `activate_bomb` / `activate_laser_beam` / `ensure_touch_skill_buttons` / `ensure_touch_action`  

**新增能力必须先改桥 + 写入对应 genre 契约，再允许沙箱调用。**

---

## 5. 文档映射

| 文档 | 角色 |
|------|------|
| `AI改游戏智能体需求_v1.md` | 需求权威（v1.2） |
| `AI改游戏智能体_根因分析与闭环改造_v1.md` | 为何开环失败 |
| `工作方向锁定_AI改游戏智能体_v1.md` | 主线锁定 |
| `AI改游戏智能体_施工规范手册_v1.md` | 怎么改代码 |
| `AI改游戏智能体_文件映射表_v1.md` | 本文 |
| `AI改游戏智能体_全任务开工提示词_v3.md` | Cursor 粘贴开工 |
| `AI改游戏智能体_工作进度与快照_2026-07-18.md` | 进度 / 足迹 / 工作树快照 |
| `.cursor/rules/godot-mini-game.mdc` | 仓库始终约束 |

---

## 6. 明确不在映射内（勿改当主交付）

- `templates/{genre}/core/**` 玩法源  
- `秒哒游戏原型/**`  
- `开发文档/模板引擎/**` 历史扩品类任务（已锁定）  
- `backend/.env`（本地 Key，不入库）  

---

## 修订

| 日期 | 说明 |
|------|------|
| 2026-07-18 | v1：对齐需求 v1.2 工作流分层 |
| 2026-07-18 | 入口改为「有 Key 仅 agent」；链到工作进度与快照 |
| 2026-07-19 | HF-13：e2e_7_19 / Reference / 墙钟·前端超时 / UI gate 字段 |
| 2026-07-20 | HF-14 evidence；HF-15 预言机分层文档切片与 test_hf15 待建 |
