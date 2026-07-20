# GameForge K12 · 服务器部署 · AI 智能体自动部署手册 v1.3

> **读者**：Cursor / Claude / Codex 等**可执行命令的部署智能体**，以及接手展厅服务器的同事  
> **目标**：在全新 Windows 服务器上，解压本交付包 → 一键部署 → 健康验收 →（**另任务**）补齐二维码  
> **产品版本**：见根目录 `VERSION`（当前 **1.2**）  
> **配套人工文档**：[`软件操作说明书_v1.2.md`](./软件操作说明书_v1.2.md) · [`部署手册_v1.2.md`](./部署手册_v1.2.md)  
> **入口**：解压后先读根目录 [`请先读_展厅部署与操作.md`](../请先读_展厅部署与操作.md)

---

## 0. 给部署 Agent 的执行契约（必读）

你是**服务器部署 Agent**。严格按顺序执行，不要跳过健康检查。

1. 工作目录 `$ROOT` 必须同时含：`backend/`、`kiosk/`、`templates/`、`config/`、`VERSION`。  
2. **禁止**修改 `templates/*/core/**`（玩法冻结源）。  
3. **禁止**把真实 `LLM_API_KEY` / 密钥提交进 Git；只写入本机 `backend/.env`。  
4. **禁止**假定「二维码已可用」——见 **§8 交付缺口**；基础部署验收通过 ≠ 二维码验收通过。  
5. 端口冲突时先释放再启动；成功标准见 **§6**。  
6. 全部命令默认 PowerShell；若环境无 Python/Godot，先安装再继续。

### 一键部署（首选，复制即跑）

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
cd $ROOT   # 换成解压后的真实路径，例如 D:\GameForge-K12
# 将 Godot 路径换成本机实际路径：
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 `
  -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"
```

仅准备环境、暂不卡在启动控制台：

```powershell
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 `
  -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe" -NoBrowser
```

人工开馆也可双击：`$ROOT\启动游戏工坊.exe`（须已配置 `backend\.env` 的 `GODOT_PATH`）。

---

## 1. 交付包应有内容

```text
$ROOT/
├── 请先读_展厅部署与操作.md          ← 人类入口
├── 启动游戏工坊.exe                   ← 一键启停（若随包）
├── VERSION / CHANGELOG.md / README.md / 文档目录说明.md
├── backend/                           ← FastAPI（含 .env.example；无 .venv / 无 .env）
├── kiosk/                             ← 静态前端（B 链 edu 为主）
├── templates/                         ← 七品类 Godot 模板 + _edu 桥
├── config/                            ← 契约 / 规格 / 配方
├── assets/                            ← 素材
├── data/
│   ├── reference_skills/              ← AI 改游戏参考 Skill（策展包）
│   └── learned_skills/                ← 空库或最小结构（运行时写入）
├── tools/                             ← 可选便携 Redis
├── workspace/                         ← 空目录（会话运行时）
├── 05-工具脚本/
│   ├── deploy_exhibition.ps1          ← ★ 一键部署
│   ├── launch_workshop.py / build_launcher.ps1
│   ├── run_backend.ps1 / run_redis.ps1 / install_redis.ps1
│   ├── apply_exhibition_config.ps1 / kiosk_lan_nginx.ps1
│   ├── validate_creative_templates.py
│   ├── e2e_b_edu_batch.py / e2e_recipe_a_certificate.py
│   └── …
└── 开发文档/
    ├── 服务器部署_AI智能体自动部署手册_v1.3.md  ← ★ 本文
    ├── 展厅本地服务器_AI一键部署说明_v1.2.md
    ├── 部署手册_v1.2.md
    └── 软件操作说明书_v1.2.md
```

**不应出现在交付包中**：`.git`、`.cursor`、`秒哒游戏原型/`、`03-背景与调研/`、`reports/`、`backend/.venv`、`backend/.env`、`05-工具脚本/_dev_archive/`、开发用 Live 探针脚本。

---

## 2. 端口与 URL

| 端口 | 进程 | 绑定建议 | 用途 | 必须 |
|------|------|----------|------|------|
| **8000** | uvicorn · FastAPI | `127.0.0.1` 或 `0.0.0.0` | API / 会话 / 试玩 / 日榜 / 触控键盘 / 证书 | ✅ |
| **8080** | `python -m http.server` | `127.0.0.1` | Kiosk 静态前端 | ✅ |
| **6379** | redis-server | `127.0.0.1` | 会话持久化 | 推荐 |
| **9080** | nginx（可选） | 局域网 IP | 反代 `/kiosk` + `/api` | 可选 |
| **443/80** | 公网反代（可选） | 公网 | **仅二维码补齐任务需要** | §8 |

| 名称 | URL |
|------|-----|
| **展厅主入口（B 链）** | http://127.0.0.1:8080/kiosk/edu/ |
| A 链快玩 | http://127.0.0.1:8080/kiosk/ |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

---

## 3. 前置条件

| 项 | 要求 |
|----|------|
| OS | Windows 10/11 **64 位** |
| CPU / 内存 | ≥ 4 核 / **≥ 8 GB** |
| 磁盘 | 解压后约 300–600 MB + `workspace` 运行空间 |
| 显示 | 横屏 1920×1080；支持触控更佳 |
| Python | **3.11+**（安装勾选 Add to PATH） |
| Godot | **4.6.x Standard**（不要 .NET 版）GUI exe |
| 浏览器 | Edge 或 Chrome 最新稳定版 |
| LLM（可选） | DeepSeek 等 OpenAI 兼容 Key；无 Key 时 AI 改游戏走离线 stub（UI 须诚实） |

---

## 4. 逐步部署清单（Agent 逐步勾选）

### Step 1 · 解压

解压 zip → `$ROOT`（例：`D:\GameForge-K12\`）。确认 §1 目录齐全。

### Step 2 · 安装 Python / Godot（若缺失）

```powershell
python --version
# Godot：下载 Standard win64，记录 exe 绝对路径，例如：
# C:\Godot\Godot_v4.6.3-stable_win64.exe
& "C:\Godot\Godot_v4.6.3-stable_win64.exe" --version
```

### Step 3 · 配置 `backend/.env`

```powershell
cd $ROOT
Copy-Item backend\.env.example backend\.env -Force
```

**最低必填**：

```env
GODOT_PATH=C:\Godot\Godot_v4.6.3-stable_win64.exe
REDIS_URL=redis://127.0.0.1:6379/0
ALLOW_MEMORY_FALLBACK=true
```

**教学并发（7.20 · 必写；勿依赖代码默认 max_sessions=10）**：

```env
MAX_SESSIONS=70
MAX_CONCURRENT_AGENTS=6
AGENT_QUEUE_WAIT_SEC=90
PLAY_LAUNCH_MODE=server
```

- 机房共享盘试玩：`PLAY_LAUNCH_MODE=local_share`（见 `7.20_教学机房_S2路B_部署检查清单_草案.md`）  
- 验收：`GET /health` 中 `max_sessions>=70` 且 `play_launch_mode` 符合部署意图  

**有 LLM 时追加**（勿提交仓库）：

```env
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

> `PUBLIC_API_BASE`：**不要**在基础部署阶段假装已配好。二维码见 §8。

### Step 4 · 一键部署

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 `
  -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"
```

脚本职责：检查结构 → 写 `.env` → 尝试 Redis → 创建 `backend/.venv` + pip → 启动 **:8000 + :8080** → 打开浏览器。

### Step 5 · 健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8080/kiosk/edu/ -UseBasicParsing | Select-Object StatusCode
```

期望：`status=ok`（或等价健康字段）· Kiosk HTTP **200**。

### Step 6 · 冒烟（推荐）

```powershell
python 05-工具脚本\validate_creative_templates.py
# 可选（需服务已起）：
python 05-工具脚本\e2e_b_edu_batch.py http://127.0.0.1:8000
```

---

## 5. 手动启停（调试）

**API**

```powershell
cd $ROOT
.\05-工具脚本\run_backend.ps1
```

**Kiosk**（cwd 必须是 `$ROOT`，不是 `kiosk/`）

```powershell
cd $ROOT
python -m http.server 8080 --bind 127.0.0.1
```

停止：启动器窗口按 Enter，或结束 `uvicorn` / `http.server` 进程。

---

## 6. 基础部署验收（开馆最低线）

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | `/health` | 可达且正常 |
| 2 | B 链页 | `http://127.0.0.1:8080/kiosk/edu/` 可打开 |
| 3 | B1→B2 | 可选品类、可填名字 |
| 4 | 配方→证书区 | 可走到证书步骤；**本机保存 PNG**可用即可 |
| 5 | 试玩 | Godot 窗启动；至少一款触屏可玩 |
| 6 | 日榜 | 关 Godot 后可出榜或页眉可开榜 |
| 7 | 端口 | **8000**、**8080** 监听中 |
| 8 | AI 改游戏（有 Key） | 发送一句改玩法指令 → `provider=agent` 或诚实失败；无 Key → stub 诚实 |

**注意**：上表通过 **不包含**「手机扫码下载证书」。二维码见下一节。

---

## 7. AI 改游戏智能体（随包能力）

- 有 `LLM_API_KEY`：会话内 LLM 多工具改 `workspace/{session}/`；禁改模板 `core`。  
- 材料：`data/reference_skills/`；回主页可 harvest 到 `data/learned_skills/`（**有效才入库**）。  
- 刷新/异常退出：`POST /sessions/{id}/release` 默认**只清盘、不 harvest**。  
- 前端超时约 420s；后端墙钟约 360s。  
- 细节：`开发文档/工作方向锁定_AI改游戏智能体_v1.md` · `7.19_…_新窗对接_…md`。

---

## 8. ⚠ 交付缺口 · 二维码功能未实装（须服务器智能体补齐）

### 8.1 现状声明（对同事 / 对 Agent 统一口径）

**手机扫码下载证书的端到端能力，在本交付包中视为未实装、未验收。**

可能存在前端 `qrcodejs`、token API、中继上传等**半成品或雏形**，**不得**当作已交付功能。  
讲解员演示以**本机保存证书 PNG**为准。

你（服务器侧 Cursor / Claude Agent）在完成 §4–§6 基础部署后，**必须另开任务补齐二维码**，直到手机可扫码下载同图 PNG。

### 8.2 补齐任务目标

> 游客在展厅大屏点「保存证书」→ 出现可扫二维码 → 手机浏览器打开 → **下载到与大屏一致的证书 PNG**。

### 8.3 建议实施步骤（由服务器 Agent 自主完成）

1. **摸清现状**  
   - 读：`kiosk/edu/certificate.js`、`backend/app/routers/public_certificates.py`、`backend/app/services/certificate_tokens.py`、`certificate_relay.py`、`backend/.env.example`。  
   - 调：`GET /health` 是否含 `ready_for_public_qr` 之类字段；无则自行补齐探测。  
2. **选定公网可达基址**  
   - 配置 `backend/.env`：`PUBLIC_API_BASE=https://你的展馆域名`（须手机可访问，勿用 `127.0.0.1`）。  
3. **反代**  
   - Nginx（或等价）将公网 HTTPS 反代到本机 `:8000`，至少暴露：  
     - `/public/certificates/{token}`  
     - 如需：`/api`、健康检查  
   - 参考：`05-工具脚本/nginx_exhibition.conf.example` · `部署手册_v1.2.md` §十四。  
4. **二维码内容**  
   - 二维码必须编码 **公网 HTTPS URL**（`PUBLIC_API_BASE` + token 路径），禁止编码环回地址。  
5. **缺啥补啥**  
   - 若前端无可靠二维码渲染、上传失败、token 过期策略缺失、CORS/HTTPS 证书问题：在会话副本式改动范围内修复并自测（优先 `_edu` / kiosk / backend 证书链路；**仍禁止改 `templates/*/core`**）。  
6. **验收（二维码专用）**  

| # | 检查 | 通过 |
|---|------|------|
| Q1 | 大屏保存证书 | 弹出二维码面板（非仅纯文本兜底，除非产品同意） |
| Q2 | 手机扫码 | 打开 HTTPS 页面，无证书错误（或馆方认可的内网 CA） |
| Q3 | 下载 | 得到 PNG，内容与大屏证书一致 |
| Q4 | 过期/错误 token | 返回明确 404/410，不泄其它会话数据 |
| Q5 | 文档 | 更新本机 `backend/.env.example` 注释 + 在服务器运维备忘记下域名与反代 |

7. **完成后**向同事口头/书面确认：「二维码已补齐并通过 Q1–Q5」；未完成前开馆话术仍只用本机 PNG。

### 8.4 明确不在基础部署范围

- 不要求基础 `deploy_exhibition.ps1` 自动配公网域名。  
- 不要求交付包自带有效 TLS 证书。  
- 未完成 §8 不得在对外材料中写「支持扫码带走」。

---

## 9. 故障排查（Agent）

| 信号 | 动作 |
|------|------|
| `Address already in use` :8000/:8080 | 查 PID 结束占用后重跑 deploy |
| `play/launch` 503 | 校正 `GODOT_PATH` 后重启 API |
| Kiosk 白屏 / 配置 404 | http.server 的 cwd 必须是 `$ROOT` |
| `session_backend: memory` | Redis 未启；可展厅，重启 API 丢会话 |
| 触控键盘无效 | 必须走 `:8080/kiosk/edu/`；查 `/kiosk/touch-keyboard/*` |
| AI 改游戏全 stub | 查 `LLM_API_KEY` 是否写入 `.env` 且已重启 API |
| 扫码打不开 | **属 §8 缺口**；查 `PUBLIC_API_BASE` 是否手机可达 |

---

## 10. 红线

- 禁止改 `templates/{genre}/core/**`  
- 禁止把密钥写入交付包再二次分发  
- 禁止 catalog express 伪快车道冒充 AI 能力（产品主线）  
- 禁止声称二维码已交付而未通过 §8.3 Q1–Q5  

---

## 11. 文档索引

| 文档 | 用途 |
|------|------|
| **本文** | AI 自动部署 + 二维码补齐任务书 |
| `展厅本地服务器_AI一键部署说明_v1.2.md` | 旧版一键说明（可对照） |
| `部署手册_v1.2.md` | 完整环境 / nginx / 排障 |
| `软件操作说明书_v1.2.md` | 讲解员日常 |
| `工作方向锁定_AI改游戏智能体_v1.md` | AI 改游戏主线口径 |

---

## 12. 修订

| 日期 | 说明 |
|------|------|
| 2026-07-19 | v1.3：面向 Cursor/Claude 自动部署；明确二维码未实装须服务器 Agent 补齐；对齐 AI 改游戏随包能力 |

---

*复制本文件给服务器侧智能体，作为部署与二维码补齐的唯一开工说明即可。*
