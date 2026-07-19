# 文三路 AI 游戏创作工坊 · Wensan Road AI City Game

> **版本**：**1.2**（见 [`VERSION`](VERSION) · [`CHANGELOG.md`](CHANGELOG.md) · tag **`v1.2`**）  
> **GitHub**：https://github.com/DomenRaven/Wensan-Road-Ai-city-Game  
> **展厅入口文档**：[`请先读_展厅部署与操作.md`](请先读_展厅部署与操作.md)  
> **操作说明书**：[`开发文档/软件操作说明书_v1.2.md`](开发文档/软件操作说明书_v1.2.md)  
> **AI 一键部署**：[`开发文档/展厅本地服务器_AI一键部署说明_v1.2.md`](开发文档/展厅本地服务器_AI一键部署说明_v1.2.md)  
> **部署手册**：[`开发文档/部署手册_v1.2.md`](开发文档/部署手册_v1.2.md)  
> **当前开发主线**：[`开发文档/工作方向锁定_AI改游戏智能体_v1.md`](开发文档/工作方向锁定_AI改游戏智能体_v1.md) · 当前 P0 [`HF-12 安全读写闭环`](开发文档/7.19_AI改游戏智能体_HF-12_安全读写闭环_待修复与施工方案.md) · 开工 [`7.19 开工提示词 v1.2`](开发文档/7.19_AI改游戏智能体_秒哒式自由创作_开工提示词_v1.0.md) · 需求 [`AI改游戏智能体需求_v1.md`](开发文档/AI改游戏智能体需求_v1.md)

面向 K12 展厅的 **AI 小游戏创作工坊**：孩子用自然语言选品类、填配方，系统生成 Godot 游戏并试玩；支持触屏、日榜、证书 PNG。开发期优先完善 **AI 短对话改会话游戏** 智能体（通用落地工作流）。

---

## 端口

| 端口 | 服务 |
|------|------|
| **8000** | FastAPI 后端 |
| **8080** | Kiosk 静态前端 |
| **6379** | Redis（可选） |
| **9080** | Nginx 局域网反代（可选） |

主入口：http://127.0.0.1:8080/kiosk/edu/

---

## 快速启动

```powershell
# AI / 运维一键（替换为展厅本机 Godot 路径）
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"

# 或双击根目录
.\启动游戏工坊.exe
```

| 入口 | URL |
|------|-----|
| B 链教育版 | http://127.0.0.1:8080/kiosk/edu/ |
| A 链快玩 | http://127.0.0.1:8080/kiosk/ |
| API 文档 | http://127.0.0.1:8000/docs |

**环境**：Godot **4.6 Standard** · Python 3.11+ · Windows 10/11

---

## 七款游戏

横版闯关 · 街机飞机 · 生存升级 · 乒乓球 · 格斗对战 · 跑酷 · 欢乐赛车

---

## 仓库结构（展厅精简）

| 目录 | 说明 |
|------|------|
| `templates/` | 7 款 Godot 模板（`core/` 预制勿改） |
| `kiosk/` | 展厅前端（A 链 + `edu/` B 链） |
| `backend/` | FastAPI |
| `config/` | 规格与配方 |
| `assets/` | Kenney CC0 与素材 |
| `05-工具脚本/` | 部署、启动、冒烟验收 |
| `开发文档/` | 操作 / 部署说明书 |

开发期一次性脚本已移至 `05-工具脚本/_dev_archive/`（交付包不含）。

---

## 打包展厅交付 zip

```powershell
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\pack_exhibition_delivery.ps1
```

输出：`交付/GameForge-K12-v1.2-展厅部署包-YYYYMMDD.zip`

---

*文三路 AI 教育区 · GameForge K12 · v1.2 · 2026*
