# AI 小游戏创作工坊 · 项目自检对齐报告 v1.0

> **日期**：2026-06-19（D1 启动日）  
> **上线目标**：**2026-06-30**  
> **结论**：文档/配置/RAG/素材 **已对齐**；工程 **backend + 11 模板** 仍为 0%，与排期一致，**无文档漂移**

---

## 1. 排期拍板（已确认）

| 项 | 值 | 状态 |
|----|-----|------|
| **D1 启动** | 2026-06-19 | ✅ 今日 |
| **上线日** | 2026-06-30 | ✅ 12 自然日 |
| 服务器 OS | 待定（Win Server / Ubuntu） | 🔲 |
| 10 终端形态 | 待定 | 🔲 |
| 展厅 LAN | 待定 | 🔲 |

**日历映射**（D1=6/19 → D10=6/28 核心交付，**6/29–6/30 彩排+上线**）：

| D | 日期 | 里程碑 |
|---|------|--------|
| D1 | 6/19 | 素材到位 · backend 骨架 · 自检 |
| D2 | 6/20 | Redis Session≤10 |
| D3 | 6/21 | platformer · td · shmup L0 |
| D4 | 6/22 | shooter · survivor · fighting · parkour |
| D5 | 6/23 | life_sim · sports · pingpong · racing → **11/11** |
| D6–D7 | 6/24–25 | Kiosk 联调 · 10 并发压测 |
| D8 | 6/26 | L1 五类 AI 换皮 |
| D9 | 6/27 | 彩排 3 轮 |
| D10 | 6/28 | G-LAUNCH-10 预验收 |
| 缓冲 | 6/29–30 | 现场部署 · **正式上线** |

---

## 2. 文档 ↔ 配置 ↔ 代码 对齐矩阵

| 维度 | 文档 | 配置/代码 | 对齐 |
|------|------|-----------|------|
| 11 品类 | 十天上线路线 §二 · genre_registry | `config/genre_registry.json` v1.3 | ✅ |
| 玩法子模式 | 引导流程 S2 · 规格 §十三 | `config/play_variants.json` | ✅ |
| 预制技能 | 引导流程 S7 · 规格 §十二 | `config/optional_skills.json` | ✅ |
| 向导步骤 | 引导流程 v1.1 · 业务流 v1.3 | `config/wizard_steps.json` | ✅ |
| CREATE 权限 | 规格 §十一 · Cursor Rules | `.cursor/rules/godot-mini-game.mdc` | ✅ |
| 业务六态 | 系统业务流程 v1.3 | `backend/`（未建） | 🔲 待 D1 |
| 模板结构 | templates/README | `templates/*`（仅 _examples） | 🔲 待 D3 |
| core 预制 | 规格 · 各品类调研 | **无 core/ 目录** | 🔲 待 D3 首批 |
| 素材 | assets/kenney/README | `assets/` **已下载** | ✅ D1 完成 |
| RAG | build_rag_index.py | 1392 chunks | ✅ |

---

## 3. 缺口清单（按阻塞级）

### P0 · 阻塞 D3 模板

| 缺口 | 说明 | 负责 |
|------|------|------|
| `templates/{genre}/` ×11 | 无 Godot 工程 | Agent D3–D5 |
| `core/` 预制逻辑 | 每品类独立 core | Agent D3–D5 |
| `game_config.schema.json` | 未建 | Agent D3 |

### P1 · 阻塞 D6 展陈

| 缺口 | 说明 |
|------|------|
| `backend/` | FastAPI + Redis + wizard |
| Kiosk 前端 | S0–★R–S9 双栏 UI |
| `preview_patch` API | 实时预览 |

### P2 · D10 可降级

| 缺口 | 说明 |
|------|------|
| AI 生图 API | 可仅用 Kenney |
| 服务器 OS 拍板 | D2 前需定 |

---

## 4. 文档版本一致性

| 文档 | 版本 | 与 D1 对齐 |
|------|------|------------|
| 十天上线路线 | v1.2 → **v1.3 日历** | ✅ 已补日期 |
| 前期准备与待办 | v1.3 | ✅ |
| 系统业务流程 | v1.3 | ✅ |
| AI创作引导流程 | v1.1 | ✅ |
| 开发文档 README | v1.2.2 | ✅ |

**无冲突项**：D10 硬标准仍为 **11 L0 + 10 并发**；L1 五类；不改 core。

---

## 5. 今日（D1）完成项

- [x] 排期拍板：D1=6/19 · 上线=6/30
- [x] Kenney 12 包 + 字体 + 音效 下载至 `assets/`
- [x] KayKit Prototype Bits（CC0）→ `assets/third_party/`
- [x] Godot MCP 联调 smoke test **PASS**
- [x] 本自检报告 + 历史足迹 + 可行性评估

---

## 6. 明日（D2）建议

1. `backend/` FastAPI `/health` + Redis Session
2. 开始 `templates/platformer/` 首个 L0（MCP run 无 ERROR）
3. 拍板服务器 OS + 终端形态

---

*v1.0 · D1 项目自检 · 2026-06-19*
