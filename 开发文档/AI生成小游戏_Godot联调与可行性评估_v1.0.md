# AI 小游戏创作工坊 · Godot 联调与可行性评估 v1.0

> **日期**：2026-06-19（D1）  
> **问题**：人类语言 + AI Agent + Godot 4.6 是否足够支撑 D10 目标？  
> **结论**：**足够支撑 L0/L1 目标**；L2 全链需 backend + 预制 core，风险在 **工期与 10 并发 GPU**，不在工具链本身。

---

## 1. 联调环境

| 项 | 值 |
|----|-----|
| Godot | **4.6.3.stable**（`F:\Godot\...`） |
| MCP | `@coding-solo/godot-mcp` via `.cursor/mcp.json` |
| GPU | NVIDIA RTX 4060 Laptop · Vulkan Forward+ |
| 测试工程 | `tools/godot_smoke/` |

---

## 2. 联调结果

### 2.1 MCP 工具

| 工具 | 结果 |
|------|------|
| `get_godot_version` | ✅ `4.6.3.stable.official` |
| `run_project` | ✅ 启动成功 |
| `get_debug_output` | ✅ 无 ERROR |
| `stop_project` | ✅ 正常停止 |

### 2.2 运行日志（摘要）

```
Godot Engine v4.6.3.stable.official
Vulkan 1.4.329 - Forward+ - Using Device #0: NVIDIA RTX 4060
GameForge smoke test: Godot 4.6 MCP run OK
```

**errors 数组为空** → 满足 workspace 规则「godot-mcp run_project 且无 ERROR」。

### 2.3 真实品类模板 run

| 品类 | 状态 |
|------|------|
| platformer | ✅ MCP errors 空 |
| tower_defense | ✅ MCP errors 空 |
| shmup | ✅ MCP errors 空 |
| shooter | ✅ MCP errors 空 |
| survivor | ✅ MCP errors 空 |
| fighting | ✅ MCP errors 空 |
| parkour | ✅ MCP errors 空 |
| life_sim | ✅ MCP errors 空 |
| sports_race | ✅ MCP errors 空 |
| pingpong | ✅ MCP errors 空 |
| racing | ✅ MCP errors 空 |

---

## 3. 可行性评估：人类 + Agent + Godot

### 3.1 总评

| 目标档 | 可行性 | 说明 |
|--------|--------|------|
| **L0** 11 类 preset | **高（75%）** | 预制 core + Kenney 素材已齐；Agent 复制模板、挂场景 |
| **L1** 5 类 AI 换 config | **高（80%）** | 只改 JSON；Cursor Rules 已约束 |
| **L2** S0–S9 全向导 + 生图 | **中（50%）** | 依赖 backend + Kiosk；生图可降级 |
| **10 并发试玩** | **中（60%）** | GPU/内存瓶颈；cap=6 试玩 + 排队可接受 |

**综合**：**人类语言 + Cursor Agent + Godot MCP** 组合 **可以** 在 6/30 前交付 **D10 硬验收**（11 L0 + 稳定展陈），前提是：

1. **core 由 Agent 按规格预制**，不让观众/AI 现场写玩法逻辑  
2. **AI 只改 `game_config.json`**，fix 轮次 ≤2  
3. **10 并发** 采用试玩 cap + 队列，不追求 10 路全 GPU 满负荷  

### 3.2 各环节评估

| 环节 | 人类语言 | AI Agent | Godot | 评分 |
|------|----------|----------|-------|------|
| 需求→文档 | 口述/调研 | 整理 RAG、写规格 | — | ✅ 已验证 |
| 素材→工程 | 指定风格 | 下载、路径映射 | 导入 PNG/OTF | ✅ D1 完成 |
| 玩法→代码 | 选手感卡片 | 写 core（一次性） | GDScript 强类型 | 🔲 D3 验证 |
| 个性化→config | S0–S7 点选 | 合并 JSON、改 tuning/theme | 读 config 运行时 | 🔲 D8 验证 |
| 验收→运行 | 试玩 | MCP run_project | 引擎 | ✅ smoke PASS |
| 展陈→并发 | 讲解员复位 | Session 编排 | exe 池 | 🔲 D7 验证 |

### 3.3 优势

- **Godot 4.6 + GDScript** 适合 2D 小品；启动快、导出 Windows exe 成熟  
- **godot-mcp** 可自动化 run/fix 循环，符合「AI 透明厨房」  
- **Kenney CC0** 已覆盖 11 品类主视觉，减少 AI 生图依赖  
- **config 驱动** 降低 AI 改坏 core 的风险  

### 3.4 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| 11 模板 12 天写不完 | 高 | L0 only；批次 A/B/C；platformer 先行 |
| Agent 改越界 core | 中 | Cursor Rules + schema 校验 |
| MCP fix 循环超时 | 中 | fix≤2 → demo_preset |
| 10 路 Godot OOM | 高 | 试玩≤6 · 双机备选 |
| 中文 UI 字体 | 低 | 思源黑体 CN 已下载 |
| Kenney 官网直链失效 | 低 | 改用 OpenGameArt 镜像（已实践） |

### 3.5 不建议依赖的能力

- ❌ 纯自然语言 **现场生成** 新玩法机制（超出 10min）  
- ❌ 单 Session **合并两个 template**（已禁止，用 play_variants）  
- ❌ 无预制 core 的「零代码全生成」  

---

## 4. 与 D10 Gate 对照

| Gate | 工具链能否支撑 | 备注 |
|------|----------------|------|
| G-BE-1 后端 | Agent 可 scaffold FastAPI | D1–D2 |
| G-TPL-11 全品类 | Agent + MCP 逐类验收 | D3–D5 关键路径 |
| G-CONC-10 压测 | 需运维脚本，非 MCP 单点 | D7 |
| G-LAUNCH-10 | 可行 | 6/28 预验收 + 6/30 上线 |

---

## 5. 建议动作（按优先级）

1. **D2**：`templates/platformer/` 最小 L0 + MCP run  
2. **D2**：`backend/` Session 骨架  
3. **D3 起**：每完成一类即 MCP 验收，不积压到 D5  
4. **D7 前**：在目标服务器 GPU 上实测 6 路并发  

---

## 6. 附录：smoke 工程路径

```
tools/godot_smoke/
├── project.godot
├── main.tscn
└── main.gd
```

复测命令：Cursor 调用 godot MCP `run_project`，projectPath 指向上列目录。

---

*v1.0 · D1 Godot 联调与可行性 · 2026-06-19*
