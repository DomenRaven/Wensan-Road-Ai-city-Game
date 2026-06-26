# 文三路 AI 游戏创作工坊 · Wensan Road AI City Game

> **版本**：**1.0**（见 [`VERSION`](VERSION) · [`CHANGELOG.md`](CHANGELOG.md)）  
> **GitHub**：https://github.com/DomenRaven/Wensan-Road-Ai-city-Game · 标签 **`v1.0`** · 2026-06-24 已推送  
> **场内 Gitea**（可选）：`gameforge-k12` @ `http://10.70.160.61:3002/3240103625/zwm.git`  
> **状态快照**：[`开发文档/模板引擎/快照/6.24_v1.0_GitHub收工状态快照_v1.0.md`](开发文档/模板引擎/快照/6.24_v1.0_GitHub收工状态快照_v1.0.md)

面向 K12 展厅的 **AI 小游戏创作工坊**：孩子用自然语言选品类、填配方，系统生成 Godot 游戏并试玩；左侧可见真实 `game_config.json` 与操作联动高亮。

---

## 快速启动

```powershell
# 1. 后端 API
.\05-工具脚本\run_backend.ps1

# 2. 静态 Kiosk（另开终端）
cd e:\文三路AI馆\2.ai生成游戏
python -m http.server 8080
```

| 入口 | URL | 用途 |
|------|-----|------|
| A 链快玩 | http://127.0.0.1:8080/kiosk/ | 七款精选成品快体验 |
| B 链教育版 | http://127.0.0.1:8080/kiosk/edu/ | 创作 → 制作 → 试玩全链 |
| API 文档 | http://127.0.0.1:8000/docs | FastAPI |

**环境**：Godot **4.6** · Python 3.11+ · 见 `backend/README.md`

---

## 仓库结构

| 目录 | 说明 |
|------|------|
| `templates/` | 十一品类 Godot 模板（`core/` 预制，用户改 `config/game_config.json`） |
| `kiosk/` | 展厅前端（A 链 + `edu/` B 链） |
| `backend/` | FastAPI 会话、生成、试玩 |
| `config/` | kiosk 规格、配方模板、代码锚点 |
| `assets/` | Kenney CC0 与项目素材 |
| `05-工具脚本/` | E2E、冻结快照、RAG、部署脚本 |
| `开发文档/` | 需求、执行手册、评审记录 |

---

## 版本与回退

- 当前发布：**v1.0**（标签 `v1.0`）
- 回退：`git checkout v1.0` 或 `git reset --hard v1.0`（先备份分支）
- 详细说明：[`CHANGELOG.md`](CHANGELOG.md) · [`未来教育_ai生成游戏_推送指南.md`](未来教育_ai生成游戏_推送指南.md)

---

## 文档入口

- [开发文档索引](开发文档/README.md)
- [**甲方 P3 升级方案（含 LLM 评估）**](开发文档/模板引擎/6.26_甲方升级方案与LLM评估_v1.0.md)
- [B 链教育版需求](开发文档/模板引擎/6.24_B链教育版用户旅程与需求规格_v1.0.md)
- [展陈 P0 执行手册](开发文档/模板引擎/6.24_展陈P0_执行手册_v1.0.md)

---

*文三路 AI 教育区 · GameForge K12 · 2026*
