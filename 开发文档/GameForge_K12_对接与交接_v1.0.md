# GameForge K12 · 对接与交接 v1.1

> **用途**：展厅 Kiosk ↔ Backend ↔ Godot 模板 ↔ Cursor Agent 的**统一对接说明**与**续工 Prompt**  
> **更新**：2026-06-22 · **真实状态：L0 ✅ · Kiosk 产品 / E2E ❌**  
> **双轨**：[`模板引擎/D6-D10双轨并行计划_v1.0.md`](./模板引擎/D6-D10双轨并行计划_v1.0.md) ★

---

## 一、进度总览（2026-06-22）

### 1.1 里程碑（真实）

| 维度 | 进度 | 说明 |
|------|------|------|
| **11 L0 preset** | ✅ **100%** | MCP `errors: []` |
| 文档 / 配置 / RAG | ✅ | + 双轨约束 JSON 五件 |
| **game_config.schema** | ✅ | `templates/_schema/` |
| Godot MCP | ✅ | 4.6.3 |
| backend FastAPI | ~85% | Session + wizard + launch · **缺 /generate** |
| **Kiosk 产品 UI** | ❌ **~5%** | 仅灰盒 `kiosk/` · 非 v1.1 引导流程 |
| **个性化 E2E** | ❌ **0%** | payload 未落 workspace config |
| assets | ✅ | 29 包 · previews 11/11 |
| Redis / 短压测 | ✅ / 🔄 | soak 30min 🔲 |

### 1.2 十一品类 L0（评审分）

| slug | 分 | slug | 分 |
|------|-----|------|-----|
| platformer | 88 | survivor | 87 |
| tower_defense | 86 | fighting | 86 |
| shmup | 84 | parkour | 85 |
| shooter | 88 | life_sim | 87 |
| pingpong | 97 | sports_race | 87 |
| racing | 87 | | |

评审记录：`开发文档/模板引擎/评审记录/{genre}_L0.md`

### 1.3 补齐轮次（2026-06-20 已完成）

| 项 | 位置 |
|----|------|
| 卖塔 50% 返还 | `templates/tower_defense/` 右键卖塔 |
| path_validator BFS | `core/path_validator.gd` |
| tuning ±30% clamp | platformer / td / survivor `game_config_loader` |
| shmup 纯代码星空 | `scroll_background.gd` |
| platformer 安全贴图 | `theme_sprite.gd` |
| survivor 对象池 | 敌 48 · 宝石 64 |
| Kiosk 灰盒 | `kiosk/index.html` |

---

## 二、系统架构

```text
┌─────────────────┐     HTTP      ┌──────────────────┐
│  kiosk/         │ ────────────► │  backend/        │
│  index.html     │   :8000       │  FastAPI         │
│  (展厅终端)      │               │  Session≤10      │
└────────┬────────┘               └────────┬─────────┘
         │                                  │
         │  S8 配方 → 复制模板              │ wizard_steps.json
         ▼                                  │ genre_registry.json
┌─────────────────┐               ┌────────▼─────────┐
│ templates/      │ ◄── MCP ──────│ Cursor Agent     │
│ {genre}/        │   run_project │ 只改 game_config │
│ core/ 🔒        │               └──────────────────┘
│ config/ ✅      │
└─────────────────┘
         │
         ▼
   Godot 4.6.3 试玩 / Windows exe（待导出脚本）
```

**数据流**：S0 起名 → S1 选品类 → S2 玩法子模式 → S3–S7 主题/手感/技能 → ★R 配方 → S8 AI 写 `game_config.json` → S9 试玩。

---

## 三、Backend 对接

### 3.1 启动

```powershell
.\05-工具脚本\run_backend.ps1
# OpenAPI: http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/health
```

### 3.2 核心 API

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/health` | 健康 · `session_backend` · 活跃 Session 数 |
| POST | `/sessions` | 创建 Session（body: `display_name`, `genre`）· 满则 429 |
| GET | `/sessions/{id}` | Session 详情 + wizard 进度 |
| DELETE | `/sessions/{id}` | 复位删除 |
| GET | `/wizard/steps` | S0–S9 + ★R 步骤定义 |
| GET | `/genres` | 11 品类 registry |
| GET | `/genres/{genre}/play-variants` | S2 子模式 |
| POST | `/play-variants/resolve` | `{genre, variant_id}` → 可能跨品类跳转 |
| POST | `/sessions/{id}/wizard/{step_id}` | body: `{data: {...}}` |
| GET | `/sessions/{id}/recap` | ★R 配方摘要 |
| POST | `/sessions/{id}/play/launch` | S9 试玩（当前 L0；线 B 优先 workspace） |
| POST | `/sessions/{id}/generate` | **线 B 待实现** · 复制模板 + 写 config |

契约见 [`config/wizard_payload_mapping.json`](../config/wizard_payload_mapping.json)。

### 3.3 Wizard 步骤 data 字段

| step | 必填 data |
|------|-----------|
| S0 | `display_name` |
| S1 | `genre` (slug) |
| S2 | `play_variant_id` |
| S3 | `style_pack`, `mood_keywords` |
| S4 | `character` object |
| S5 | `props` array |
| S6 | `feel_id`: easy \| balanced \| challenge |
| S7 | `enabled_skills` (≤2) |
| R | `{}` 确认 |

### 3.4 Session 存储

- 优先 **Redis** `redis://127.0.0.1:6379/0`
- 不可用 → **memory** 回退（`/health` → `session_backend: memory`）

---

## 四、Kiosk 对接

### 4.1 启动

```powershell
# 1. 后端
.\05-工具脚本\run_backend.ps1

# 2. 静态页（任选）
start kiosk/index.html
# 或
python -m http.server 8080
# 浏览器 http://127.0.0.1:8080/kiosk/
```

### 4.2 灰盒现状（非产品 UI）

- 双栏布局 · S0–S7 表单 · n/8 文字进度
- POST `/sessions` · wizard 各步 · GET `/recap`（**UI 为 JSON**）
- S8 仅标记 CREATE · S9 launch **templates L0**

### 4.3 待实现（双轨）

**线 A**
- [ ] 产品 UI v1（`kiosk_ui_spec.json`）
- [ ] L0 快速通道 S1→S9
- [ ] 可读 ★R 配方卡（禁 JSON dump）

**线 B**
- [ ] `POST /sessions/{id}/generate`
- [ ] config_builder · `wizard_payload_mapping.json`
- [ ] S9 优先 workspace · `E2E-B-001`

---

## 五、Godot / MCP 对接

| 项 | 值 |
|----|-----|
| 引擎 | Godot **4.6.3** stable |
| MCP | `project-0-2.ai生成游戏-godot` · `run_project` |
| 验收 | **`errors: []`**（WARNING 尽量清零） |
| 模板根 | `templates/{genre}/` |
| AI 可改 | **仅** `config/game_config.json` → tuning / theme / enabled_skills |
| AI 禁止 | `templates/{genre}/core/` ·  repo 根 `core/` |

### 5.1 配置契约

- Schema：`templates/_schema/game_config.schema.json`
- 示例：`templates/_examples/{genre}_game_config.json`
- 主题路径：`assets/theme_paths.json`

### 5.2 素材加载约定

- `.tscn` **不嵌入** Kenney PNG
- 运行时 `theme.*_sprite` + `Image.load_from_file` + 色块 fallback（见 `theme_sprite.gd` 模式）
- junction：`templates/{genre}/assets/kenney/` → 全局 `assets/kenney/`

---

## 六、Agent / 创作对接

### 6.1 硬约束（`.cursor/rules/godot-mini-game.mdc`）

1. 单次会话只改 **一个** `templates/{genre}/`
2. **禁止**改 repo 根 `core/`
3. 用户创作时只改 `config/game_config.json`
4. 生成前：`python 05-工具脚本/query_rag.py "{主题}" -k 5`
5. tuning 调整 ±30%（loader clamp 已部分品类启用）
6. 完成后 **godot-mcp run_project** 无 ERROR

### 6.2 L1 换皮流程（D8 目标）

```text
1. POST /sessions → 获得 session_id + genre
2. 复制 templates/{genre}/ → workspace/{session_id}/
3. Agent 只改 workspace/.../config/game_config.json
4. tuning_mapper 映射 feel_id / 用户话术 → tuning 数值
5. MCP run_project(workspace) → 试玩
```

---

## 七、续工 Prompt（复制即用）

### 7.1 通用续工 Agent

```text
你是 GameForge K12（文三路 AI 教育区）续工 Agent。

【先读文档 — 按序】
1. 开发文档/模板引擎/D6-D10执行工作清单_v1.0.md  ← 查当前 # 任务
2. 开发文档/GameForge_K12_对接与交接_v1.0.md
3. 开发文档/AI生成小游戏_会话交接手册_v1.0.md
4. 开发文档/模板引擎/L0模板待完善清单_v1.0.md
5. 开发文档/模板引擎/工作状态记录_v1.0.md

【项目快照 · 2026-06-22】
- D1=2026-06-19 · 上线=2026-06-30 · 剩 8 天
- templates/ 11/11 L0 ✅
- Kiosk **产品 UI 未做** · 个性化 **E2E 未通**
- 当前：**双轨并行** — 读 开发文档/模板引擎/D6-D10双轨并行计划_v1.0.md
- 约束：config/dual_track_registry.json · kiosk_ui_spec.json

【硬约束】
- 单次只改一个 templates/{genre}/（或 kiosk/、backend/ 单模块）
- AI 创作只改 config/game_config.json 的 tuning/theme/enabled_skills
- 禁止改 templates/{genre}/core/ 与 repo 根 core/
- 生成前：python 05-工具脚本/query_rag.py "{主题}" -k 5
- 改模板后：godot-mcp run_project → errors 必须为空

【我的任务】
[在此填写清单 #，例如：「#1 完善 Kiosk S0–S7 表单 + n/8 进度」]

【完成标准】
- 更新 执行清单 # 状态 · 工作状态记录 §三
- MCP 或 API 可验证
```

### 7.2 Kiosk / 前端对接

```text
任务：GameForge K12 Kiosk 对接 backend wizard API。

阅读：开发文档/GameForge_K12_对接与交接_v1.0.md §三 §四 · backend/README.md · config/wizard_steps.json

现状：kiosk/index.html 灰盒 v0.1 可 POST /sessions。

目标：[例如「实现 S0–S7 完整表单 + ★R recap 页 + 双栏进度 n/8」]

约束：CORS 已开；API base http://127.0.0.1:8000；不破坏现有 backend 契约。
```

### 7.3 L0 polish / 单品类修复

```text
任务：GameForge K12 · 补齐 templates/{genre}/ L0 待完善项。

阅读：
- 开发文档/模板引擎/L0模板待完善清单_v1.0.md §二 {genre}
- templates/{genre}/ · 评审记录/{genre}_L0.md
- 03-背景与调研/品类调研/{genre}/设计规范与实现路径.md

约束：只改 templates/{genre}/；强类型 GDScript；MCP run_project errors: []。

目标：[例如「shooter hit-stop + theme_sprite 全脚本」]
```

### 7.4 L1 换皮 E2E（D8）

```text
任务：GameForge K12 L1 换皮 E2E — {genre}。

流程：POST /sessions → 复制 templates/{genre}/ → 只改 game_config.json → tuning_mapper 联调 → MCP 试玩。

阅读：backend/tuning_mapper.py · templates/_examples/{genre}_game_config.json · optional_skills.json

验收：五类（platformer · td · shmup + 2）各完成一次 config-only 换皮且无 MCP ERROR。
```

---

## 八、文档索引

| 文档 | 用途 |
|------|------|
| **本文件** | 对接 + Prompt |
| [`D6-D10双轨并行计划_v1.0.md`](./模板引擎/D6-D10双轨并行计划_v1.0.md) | ★ 线 A+B |
| `AI生成小游戏_会话交接手册_v1.0.md` | 零上下文速览 |
| `AI生成小游戏_历史工作足迹_v1.0.md` | 时间线 |
| `模板引擎/工作状态记录_v1.0.md` | 当前轮补齐进度 |
| `模板引擎/L0模板待完善清单_v1.0.md` | 已知缺口 |
| `模板引擎/品类L0核心工程搭建工作流_v1.0.md` | L0 SOP |
| `AI生成小游戏_十天上线路线_v1.2.md` | D1–D10 排期 |
| `assets/ASSET_GAP_ANALYSIS.md` | 素材缺口 |
| `backend/README.md` | API 细节 |
| `kiosk/README.md` | 展厅前端 |

---

## 九、下一步（D6+）

> **完整顺序**：[`模板引擎/D6-D10执行工作清单_v1.0.md`](./模板引擎/D6-D10执行工作清单_v1.0.md)

| 当前应做 | 双轨 |
|----------|------|
| **线 A** 产品 UI + L0 快速试玩 + LAN | A1–A6 |
| **线 B** `/generate` + platformer E2E | B1–B6 |
| Gate 彩排 · 部署 | #18–#20 |

---

*v1.1 · 2026-06-22 · 真实状态 · 双轨约束*
