# AI 小游戏创作工坊 · 自动化执行控制文档 v1.2

> **文档类型**：Agent / CI 全流程执行手册  
> **读者**：Cursor Agent、Claude Code、GPT-5 Coding Agent  
> **人类读者**：项目负责人（D 日验收 · 解锁下一日）  
> **生效条件**：开发执行规范 v1.2 + 十天上线路线 v1.2 已建立 ✅  
> **v1.2 变更**：**D10 硬性上线** · **10 并发** · **11 品类 L0** · FastAPI+Redis **D1 必做**（取消 Phase 3 推迟）

---

## §0 Agent 使命与执行协议

### 0.1 使命

将已审核规范 **转化为 11 类 Godot preset + 展厅服务器编排链路**，维持文档↔代码双向同步，**按 D1–D10 日历执行、关键 Gate 人工 Review**。

### 0.2 一句话约束

**产品 = 「AI 教育区 · 展厅 11 类单机小游戏 · 10 人同时试玩」** — D10 必答：11 品类 preset 能否在终端 **≤3min 开玩**？

### 0.3 每次会话启动序列（强制）

```text
0. RESOLVE  §3.1 repo_root
0b. RAG     复杂任务前先 `query_rag.py "{主题}" -k 5`
1. READ    本文档 §1 + §3.1
2. READ    {docs}/AI生成小游戏_十天上线路线_v1.2.md
3. READ    {docs}/AI生成小游戏_开发执行规范_v1.0.md
4. LOAD    §12 快照 — 确认 day_unlock
5. VERIFY  godot-mcp: get_godot_version → 4.6.3.stable
6. SCAN    templates/ backend/ workspace/ genre_registry.json
7. LOAD    §3 — 仅当前 Day pending 任务
8. CHECK   §2 门控
9. EXEC    单任务；§0.6 文件上限
10. VERIFY §6 shell 命令 exit 0 或 MCP 工具成功
11. UPDATE §12 任务 status
12. REPORT §8 模板
```

### 0.4 全局禁止

| ID | 禁止行为 |
|----|----------|
| F-01 | 新建联机/存档/内购/广告系统 |
| F-02 | 使用 C# Godot（.NET 版） |
| F-03 | 以 HTML5 为主演示路径（仅作降级） |
| F-04 | 单次会话修改多个品类模板 |
| F-05 | 手写大量 .tscn XML（优先脚本 instantiate 或 MCP） |
| F-06 | GDScript 无类型注解 |
| F-07 | 引入暴力/恐怖/赌博素材或逻辑 |
| F-08 | 跳过 MCP run_project 验证即标记 done |
| F-09 | 未经 day_unlock 执行下一 Day |
| F-10 | verify 失败超过 2 次仍继续（须 §11.1 blocked） |
| F-11 | 重构超出当前 task scope 的文件 |

### 0.5 技术栈锁定（v1.2 · D1 起全栈）

| 层 | v1.2 | 不可替换为 |
|----|------|------------|
| 游戏引擎 | Godot 4.6 Standard + GDScript | Unity / Unreal / C# Godot |
| AI 编码 | Cursor Agent + godot-mcp + **RAG** | 纯网页 Chat |
| 配置契约 | `game_config.json` core/tuning/theme | 全量改 .gd |
| 终端 | 浏览器/Kiosk `/lobby` `/play` | 裸 exe 无编排 |
| 后端 | **FastAPI 0.111 + Redis**（Session≤10） | Flask |
| 反代 | nginx | 裸端口暴露 |
| 素材 | Kenney CC0 + assets/ | 随机网络图源 |
| 导出 | Godot run > Windows .exe | Web 优先 |

### 0.6 单任务修改上限

```yaml
single_task_limits:
  create_files_max: 12
  modify_files_max: 18
  delete_files_max: 3
```

---

## §1 文档索引

| 优先级 | 路径变量 | 用途 |
|--------|----------|------|
| P0 | `{docs}/AI生成小游戏_十天上线路线_v1.2.md` | **D10 主排期** |
| P0 | `{docs}/AI生成小游戏_自动化执行控制文档_v1.0.md` | 本文件 |
| P0 | `{docs}/AI生成小游戏_开发执行规范_v1.0.md` | 总索引 |
| P1 | `{docs}/AI生成小游戏_技术选型与开发计划_v1.0.md` | 硬件+模块 |
| P1 | `{docs}/AI生成小游戏_功能点明细与开发计划_v1.0.md` | 功能 ID |
| P1 | `{docs}/架构/系统架构说明_v1.0.md` | 四层架构 |
| P2 | `{repo_root}/.cursor/mcp.json` | godot-mcp |
| P2 | `{repo_root}/.cursor/rules/*.mdc` | GDScript 约束 |
| P1 | `{docs}/AI生成小游戏_技术方案独立评审_v1.0.md` | 评审依据 |
| P2 | `{repo_root}/03-背景与调研/rag/index/gameforge_rag.db` | RAG 索引 |
| P2 | `{repo_root}/05-工具脚本/query_rag.py` | RAG 查询 |

路径变量：

```yaml
repo_root: "E:\\文三路AI馆\\2.ai生成游戏"
docs: "{repo_root}/开发文档"
godot_path: "F:\\Godot\\Godot_v4.6.3-stable_win64.exe\\Godot_v4.6.3-stable_win64_console.exe"
templates: "{repo_root}/templates"
backend: "{repo_root}/backend"
genre_registry: "{repo_root}/config/genre_registry.json"
workspace: "{repo_root}/workspace"
exports: "{repo_root}/exports"
```

---

## §2 门控系统（Gates）

| Gate ID | PASS 条件 | 阻塞 |
|---------|-----------|------|
| **G-RAG** | `query_rag.py` 有命中 | D3+ 模板任务 |
| **G-DOC** | P0 文档存在 | 全部 |
| **G-MCP** | get_godot_version + list_projects 成功 | D3 代码任务 |
| **G-BE-1** | FastAPI `/health` + Redis ping | D3 模板 |
| **G-TPL-A** | platformer + tower_defense + shmup L0 | D4 批次 B |
| **G-TPL-11** | **11/11** 品类 MCP run 无 ERROR | D6 联调 |
| **G-CONC-10** | 10 Session 创建 + **≥8 同时 PLAY** 30min | D8 AI L1 |
| **G-LAUNCH-10** | D10 验收清单全绿 | 正式上线 |
| **G-DAY-N** | 人类 Review Day N | Day N+1 |

---

## §3 十天任务编排（D1–D10）

> 详表见 [`AI生成小游戏_十天上线路线_v1.2.md`](./AI生成小游戏_十天上线路线_v1.2.md) §四。

### Day 0 · 文档与环境（已完成 ~95%）

| Task | 描述 | Verify | Status |
|------|------|--------|--------|
| D0-T1 | 文档体系 v1.2 | 十天上线路线 + 同步 | ✅ |
| D0-T2 | mcp.json GODOT_PATH | MCP 4.6.3.stable | ✅ |
| D0-T3 | .cursor/rules | core_locked | ✅ |
| D0-T4 | 调研 + RAG | **1348** chunks | ✅ |
| D0-T5 | genre_registry.json | 11 品类注册 | 🔲 |

### Day 1 · 服务器骨架

| Task | 描述 | Verify |
|------|------|--------|
| D1-T1 | `backend/` FastAPI 脚手架 | `curl /health` 200 |
| D1-T2 | Redis Session 模型 max=10 | redis-cli ping |
| D1-T3 | `config/genre_registry.json` | 11 slug 可读 |
| D1-T4 | 部署脚本草案 | docker-compose 或 ps1 |

### Day 2 · 并发底座

| Task | 描述 | Verify |
|------|------|--------|
| D2-T1 | Session 创建/销毁/心跳 API | 10 连接无崩溃 |
| D2-T2 | 排队 + 容量拒绝 | 第 11 连接 429 |
| D2-T3 | nginx 反代 | 局域网可访问 |

### Day 3 · 模板批次 A

| Task | 描述 | Verify |
|------|------|--------|
| D3-T1 | `platformer` L0 demo_preset | run_project 无 ERROR |
| D3-T2 | `tower_defense` L0 | 同上 |
| D3-T3 | `shmup` L0 | 同上 |

### Day 4 · 模板批次 B

| Task | 描述 | Verify |
|------|------|--------|
| D4-T1 | `shooter`（TPS/FPS tuning） | run PASS |
| D4-T2 | `survivor` · `fighting` · `parkour` | 各 run PASS |

### Day 5 · 模板批次 C → 11/11

| Task | 描述 | Verify |
|------|------|--------|
| D5-T1 | `life_sim` · `sports_race` | run PASS |
| D5-T2 | `pingpong` · `racing` | run PASS |
| D5-T3 | **G-TPL-11** 回归 | 11/11 preset |

### Day 6–10 · 联调 / 压测 / 上线

| Day | 焦点 | Gate |
|-----|------|------|
| D6 | 终端选品类→开玩；复位 SOP | 单终端 E2E ≤3min |
| D7 | 10 并发 soak 30min | **G-CONC-10** |
| D8 | L1 AI：5 类仅改 config | 每类 1 次换主题 |
| D9 | 彩排 3 轮 · 讲解员手册 | 降级链可用 |
| D10 | **展厅部署** | **G-LAUNCH-10** |

~~v1.1 Wave 0–4~~ 已合并入上表。

---

## §4 品类生成标准 Prompt 骨架

```markdown
## 硬性规则
0. 生成前先执行 `query_rag.py "{品类+主题}" -k 5`，引用检索摘要
1. 只修改 workspace/{session_id}/config/game_config.json 的 tuning 和 theme
2. 禁止修改 templates/{genre}/core/ 及 workspace 中 core/ 下任何 .gd
3. 禁止修改移动模式、命中判定类型、伤害公式、波次调度器
4. 素材路径必须从 assets/kenney/{asset_pack}/ 选取
5. tuning 调整不超过默认值 ±30%（见 模板引擎/品类核心参数规格_v1.0.md）
6. 改完执行 godot-mcp run_project 验证

## 已由编排层预填的 tuning（优先使用，勿重写逻辑）
{tuning_json}

## 用户原始需求
{user_intent}

## 你只需要
- 按需求微调 tuning 数值
- 替换 theme 贴图路径与 display_name
- 若用户无特殊要求：仅换 theme，保持默认 tuning
```

---

## §5 MCP 工具使用规范

| 场景 | 优先工具 | 备注 |
|------|----------|------|
| 验证环境 | `get_godot_version` | 每次会话开头 |
| 发现项目 | `list_projects` | path=workspace/ |
| 运行游戏 | `run_project` | 必读 debug output |
| 修错迭代 | `get_debug_output` → 改 .gd → 再 run | ≤2 轮 |
| 场景操作 | `create_scene` / `add_node` | 避免手写 tscn |
| 查结构 | `get_project_info` | 生成前 |

---

## §6 verify 命令清单

```powershell
# V0 — MCP（Agent 调用）
get_godot_version → 4.6.3.stable

# V0b — RAG
python "E:\文三路AI馆\2.ai生成游戏\05-工具脚本\query_rag.py" "platformer 跳跃手感" -k 5

# V1 — Godot CLI
& "F:\Godot\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64_console.exe" --path "E:\文三路AI馆\2.ai生成游戏\templates\platformer" --quit-after 3

# V3 — 后端（D1+）
cd "E:\文三路AI馆\2.ai生成游戏\backend"
python -m pytest tests/ -q
curl http://localhost:8000/health
```

---

## §7 失败恢复

| 症状 | 动作 |
|------|------|
| MCP 找不到 Godot | 检查 GODOT_PATH in mcp.json |
| run_project ERROR | 读日志 → 改 .gd → 再 run；2 次失败 → blocked |
| 10min 超时 | 回退 templates/{genre}/demo_preset |
| npm EPERM | npm_config_cache 改 TEMP 目录 |
| 导出失败 | 降级 Godot 窗口运行 |

---

## §8 报告模板

```markdown
## Day {N} 任务 {ID} 报告
- 状态：done / blocked
- 修改文件：{list}
- verify：{commands + exit codes}
- MCP 日志摘要：{errors or none}
- 阻塞项：{if any}
- 建议下一任务：{ID}
```

---

## §9 §12 快照（Agent 写回）

```yaml
day_unlock: 0
current_day: D0
gates:
  G-DOC: PASS
  G-MCP: PASS
  G-RAG: PASS
  G-BE-1: PENDING
  G-TPL-11: PENDING
  G-CONC-10: PENDING
  G-LAUNCH-10: PENDING
tasks:
  D0-T1: done
  D0-T2: done
  D0-T3: done
  D0-T4: done
  D0-T5: done
  D1-T1: pending
```

---

*v1.2 · 2026-06-19 · D10 上线 · 11 品类 · 10 并发*
