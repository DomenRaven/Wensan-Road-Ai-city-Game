# AI 小游戏创作工坊 · 自动化执行控制文档 v1.1

> **文档类型**：Agent / CI 全流程执行手册  
> **读者**：Cursor Agent、Claude Code、GPT-5 Coding Agent  
> **人类读者**：项目负责人（Wave 验收 · 解锁下一波次）  
> **生效条件**：开发执行规范 v1.1 + 技术选型 v1.1 已建立 ✅  
> **v1.1 变更**：Wave 重排为本地制作核优先；FastAPI/React 推迟 Phase 3；新增 G-RAG 门控

---

## §0 Agent 使命与执行协议

### 0.1 使命

将已审核通过的规范文档 **转化为可运行的 Godot 模板与配置驱动生成链路**，维持文档↔代码双向同步，**按 Wave 执行、Wave 间人工 Review**。展陈 Kiosk/FastAPI 在 Wave 4+ 按需追加。

### 0.2 一句话约束

**产品 = 「AI 教育区 · 10 分钟小游戏创作工坊」** — 所有产出必须能回答：这能让一个 10 岁孩子在 10 分钟内试玩到自己主题的游戏吗？

### 0.3 每次会话启动序列（强制）

```text
0. RESOLVE  §3.1 repo_root
0b. RAG     复杂任务前先 `query_rag.py "{主题}" -k 5`
1. READ    本文档 §1 + §3.1
2. READ    {docs}/AI生成小游戏_开发执行规范_v1.0.md
3. LOAD    §12 快照 — 确认 wave_unlock
4. VERIFY  godot-mcp: get_godot_version → 4.6.3.stable
5. SCAN    templates/ workspace/ .cursor/mcp.json
6. LOAD    §4 — 仅当前 Wave pending 任务
7. CHECK   §2 门控
8. EXEC    单任务；§0.6 文件上限
9. VERIFY  §7 shell 命令 exit 0 或 MCP 工具成功
10. UPDATE §12 任务 status
11. REPORT §9 模板
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
| F-09 | 未经 wave_unlock 执行下一 Wave |
| F-10 | verify 失败超过 2 次仍继续（须 §11.1 blocked） |
| F-11 | 重构超出当前 task scope 的文件 |

### 0.5 技术栈锁定（按 Phase）

| 层 | Phase 1（当前） | Phase 3（展陈） | 不可替换为 |
|----|-----------------|-----------------|------------|
| 游戏引擎 | Godot 4.6 Standard + GDScript | 同左 | Unity / Unreal / C# Godot |
| AI 编码 | Cursor Agent + godot-mcp + **RAG** | 同左 | 纯网页 Chat |
| 配置契约 | `game_config.json` core/tuning/theme | 同左 | 全量改 .gd |
| 前端 Kiosk | **Godot menu.tscn**（过渡） | React 18 + Vite 5 + TS | Vue |
| 后端 | 本地脚本 / 无服务 | FastAPI 0.111 + Redis | Flask |
| 素材 | Kenney CC0 + assets/ | 同左 | 随机网络图源 |
| 导出 | Godot run > Windows .exe > Web | 同左 | Web 优先 |

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
workspace: "{repo_root}/workspace"
exports: "{repo_root}/exports"
```

---

## §2 门控系统（Gates）

| Gate ID | PASS 条件 | 阻塞 |
|---------|-----------|------|
| **G-RAG** | `query_rag.py` 有命中 | W1 生成任务 |
| **G-DOC** | P0 文档存在 | 全部 |
| **G-MCP** | get_godot_version + list_projects 成功 | W1 代码任务 |
| **G-TPL-1** | platformer 模板 MCP run 无 ERROR | W2 多品类 |
| **G-TPL-3** | shooter + tower_defense run PASS | W3 导出 |
| **G-PROMPT** | ≥3 品类 prompts + RAG 联调 | W2 E2E |
| **G-SLA** | 连续 5 次 E2E **P90≤10min**（仅改 config） | W4 展陈 |
| **G-SCAFFOLD** | FastAPI + React 灰盒（**Phase 3 可选**） | 展陈联调 |
| **G-WAVE-N** | 人类 Review Wave N | Wave N+1 |

---

## §3 Wave 任务编排

### Wave 0 · 文档与环境（当前 ~90%）

| Task | 描述 | Verify | Status |
|------|------|--------|--------|
| W0-T1 | 文档体系 v1.1 | 文件存在 | ✅ |
| W0-T2 | mcp.json GODOT_PATH | MCP 4.6.3.stable | ✅ |
| W0-T3 | .cursor/rules | core_locked | ✅ |
| W0-T4 | 调研 + RAG | 882 chunks query | ✅ |
| W0-T5 | 独立评审 | 评审文档 | ✅ |
| W0-T6 | templates/platformer 骨架 | MCP run_project | 🔲 |

### Wave 1 · 制作核 E2E（单品类）

| Task | 描述 | Verify |
|------|------|--------|
| W1-T1 | platformer 可玩 demo（core 预制） | run_project 无 ERROR |
| W1-T2 | prompts/platformer.md + RAG 引用 | 人工可读 |
| W1-T3 | workspace 复制脚本 | `workspace/{id}` 隔离 |
| W1-T4 | **人工计时** Prompt→仅改 config→运行 | ≤10min 记录 |

### Wave 2 · 三品类 MVP

| Task | 描述 | Verify |
|------|------|--------|
| W2-T1 | shooter + tower_defense 模板 | 各 run PASS |
| W2-T2 | 三品类 demo_preset | 回退包可运行 |
| W2-T3 | tuning_mapper 脚本 | 「快点」可映射 |
| W2-T4 | 三品类各 1 次 E2E 计时 | 记录表 |

### Wave 3 · 导出与 Godot 菜单

| Task | 描述 | Verify |
|------|------|--------|
| W3-T1 | Windows export 脚本 | exports/*.exe |
| W3-T2 | Godot menu.tscn 选品类 | 本地选主题可生成 |
| W3-T3 | 20 场压测记录 | 成功率 ≥85% |
| W3-T4 | Phase 2 品类排期文档 | 4 类 backlog |

### Wave 4 · 展陈集成（Phase 3 栈 · 按需）

| Task | 描述 | Verify |
|------|------|--------|
| W4-T1 | FastAPI Session + Redis | curl 200 |
| W4-T2 | React Kiosk 灰盒 | npm run dev |
| W4-T3 | Socket 过程可视化 | 双屏同步 |
| W4-T4 | 硬件安装 + 讲解员 SOP | 现场验收 |

> W4 中双 Session、敏感词、MinIO+QR、20 场压测为展陈全量验收项，与 W3 本地压测互补。

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

# V2 — 前端（Wave 2+）
cd "E:\文三路AI馆\2.ai生成游戏\frontend"
npm run build

# V3 — 后端（Wave 2+）
cd "E:\文三路AI馆\2.ai生成游戏\backend"
python -m pytest tests/ -q
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
## Wave {N} 任务 {ID} 报告
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
wave_unlock: 0
current_wave: W0
gates:
  G-DOC: PASS
  G-MCP: PASS
  G-RAG: PASS
  G-TPL-1: PENDING
  G-SCAFFOLD: DEFERRED_PHASE3
tasks:
  W0-T1: done
  W0-T2: done
  W0-T3: done
  W0-T4: done
  W0-T5: done
  W0-T6: pending
```

---

*v1.1 · 2026-06-13 · 对齐技术选型/功能点 v1.1*
