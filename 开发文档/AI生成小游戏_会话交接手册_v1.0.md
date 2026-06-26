# AI 小游戏创作工坊 · 会话交接手册 v1.1

> **用途**：新 Cursor 窗口 / 新同事 **零上下文续工**  
> **更新**：2026-06-21 · D6 polish · 执行清单对齐  
> **按序执行**：[`模板引擎/D6-D10执行工作清单_v1.0.md`](./模板引擎/D6-D10执行工作清单_v1.0.md) ★

---

## 1. 项目一句话

K12 展厅 **10 分钟** 创作小游戏：S0–S9 向导 → AI 只改 `game_config.json` → Godot 试玩。  
**D10 硬标准**：11 品类 L0 preset ✅ + 10 并发稳定 🔲。

---

## 2. 当前进度快照

```
#0  L0 + D6 polish     ██████████  ✅
#1–#5  Kiosk           ██░░░░░░░░  🔄  当前 #1
文档/配置/RAG           ██████████  100%
assets/                 ████████░░   78%  JumperPack ✅
Godot MCP               ██████████  100%
backend/                ███████░░░   70%  Redis 未装
templates/              ██████████  100%  11/11 L0 ✅
```

| 里程碑 | 状态 |
|--------|------|
| 11 L0 模板 | **11/11 ✅** |
| 补齐轮（schema·td卖塔·pool·星空等） | ✅ 见工作状态记录 |
| 下一阶段 | **#1 Kiosk S0–S7** · #11 Redis · #14 L1 E2E |

---

## 3. 仓库关键路径

| 路径 | 说明 |
|------|------|
| **`D6-D10执行工作清单_v1.0.md`** | ★ **按序执行 · 当前 #1** |
| **`GameForge_K12_对接与交接_v1.0.md`** | 对接 + Prompt |
| `templates/*` | 11/11 L0 · MCP PASS |
| `templates/_schema/game_config.schema.json` | 配置 JSON Schema |
| `templates/_examples/` | 11 品类示例 config |
| `kiosk/index.html` | 展厅灰盒 v0.1 |
| `backend/` | FastAPI · `README.md` |
| `config/wizard_steps.json` | S0–S9 + ★R |
| `模板引擎/L0模板待完善清单_v1.0.md` | 已知缺口 |
| `模板引擎/工作状态记录_v1.0.md` | 补齐进度 |

---

## 4. 快速启动

```powershell
# 后端
.\05-工具脚本\run_backend.ps1

# Kiosk 灰盒（浏览器打开）
start kiosk/index.html

# Godot MCP 验收（任一品类）
# run_project → templates/{genre} → errors: []
```

---

## 5. 约束

- 单次会话只改一个 `templates/{genre}/`（或 kiosk/、backend/ 单模块）
- AI 创作 **只改** `config/game_config.json` 的 tuning / theme / enabled_skills
- **禁止改** `templates/{genre}/core/`
- 生成前 `python 05-工具脚本/query_rag.py "{主题}" -k 5`

---

## 6. 待办 TOP5

1. **#1–#4** Kiosk S0–★R–S9 + 预览  
2. **#6–#8** P0 素材七包 · life_sim/fighting theme  
3. **#11–#12** Redis + 10 并发压测  
4. **#14–#17** L1 五类 E2E + tuning_mapper  
5. **#5** Windows exe 导出

---

## 7. 新窗口交接 Prompt

完整版见 [`GameForge_K12_对接与交接_v1.0.md` §七](./GameForge_K12_对接与交接_v1.0.md)。

```text
你是 GameForge K12 续工 Agent。先读：
1. 开发文档/模板引擎/D6-D10执行工作清单_v1.0.md  ← 按 # 执行
2. 开发文档/GameForge_K12_对接与交接_v1.0.md
3. 开发文档/模板引擎/L0模板待完善清单_v1.0.md

快照（2026-06-21）：
- 11/11 L0 ✅ · #0 D6 polish ✅ · 当前 **#1 Kiosk S0–S7**

任务：[填写清单 #]

约束：单模板目录 · 只改 game_config.json · MCP errors 空
```

---

*v1.2 · 2026-06-21*
