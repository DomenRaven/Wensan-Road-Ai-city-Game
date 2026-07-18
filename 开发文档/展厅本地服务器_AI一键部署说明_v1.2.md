# 展厅本地服务器 · AI 一键部署说明 v1.2

> **给谁看**：展厅对接负责人、现场运维、**可执行命令的 AI 智能体**  
> **目标**：在全新 Windows 本机服务器上，按本文完成 GameForge K12 v1.2 部署并开馆  
> **产品根目录**：解压后的文件夹（下文记为 `$ROOT`）  
> **操作说明书**：[`软件操作说明书_v1.2.md`](./软件操作说明书_v1.2.md)

---

## 〇、AI Agent 执行契约（必读）

你是部署 Agent。请**严格按顺序**执行，不要跳过健康检查。

1. 工作目录必须是含 `backend/`、`kiosk/`、`templates/` 的 `$ROOT`。  
2. **禁止**修改 `templates/*/core/`。  
3. **禁止**把真实密钥写入 Git；只写本地 `backend/.env`。  
4. 部署成功标准见 **§六 验收**。  
5. 所有端口见 **§一**；冲突时先释放端口再启动。

### 一键命令（首选）

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
cd $ROOT
# 将 Godot 路径换成展厅本机实际路径：
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"
```

若仅准备环境、暂不阻塞在启动控制台：

```powershell
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe" -NoBrowser
```

人工开馆也可直接双击：`$ROOT\启动游戏工坊.exe`

---

## 一、端口一览（部署必配）

| 端口 | 协议 | 进程/服务 | 绑定建议 | 用途 | 是否必须 |
|------|------|-----------|----------|------|----------|
| **8000** | HTTP | uvicorn · FastAPI | `127.0.0.1` 或 `0.0.0.0` | 会话、生成、试玩、日榜、触控键盘、证书 API | ✅ 必须 |
| **8080** | HTTP | `python -m http.server` | `127.0.0.1` | Kiosk 静态前端（A/B 链） | ✅ 必须 |
| **6379** | TCP | redis-server | `127.0.0.1` | 会话持久化 | 推荐（可降级内存） |
| **9080** | HTTP | nginx（可选） | 局域网 IP | 多终端反代 `/kiosk` + `/api` | 可选 |

### 关键 URL

| 名称 | URL |
|------|-----|
| **B 链主入口（展厅）** | http://127.0.0.1:8080/kiosk/edu/ |
| A 链快玩 | http://127.0.0.1:8080/kiosk/ |
| API OpenAPI | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |
| 日榜示例 | http://127.0.0.1:8000/leaderboard/daily/platformer |

防火墙：单机展厅仅本机环回即可；若局域网访问再放行 8080/8000 或 9080。

---

## 二、硬件与软件前置

| 项 | 要求 |
|----|------|
| OS | Windows 10/11 **64 位** |
| CPU/内存 | ≥ 4 核 / **≥ 8 GB** |
| 磁盘 | 解压后约 **300–500 MB** + `workspace` 运行空间 |
| 显示 | 横屏 1920×1080 推荐；支持触控 |
| Python | **3.11+**（安装时勾选 Add to PATH） |
| Godot | **4.6.x Standard**（不要 .NET 版）GUI exe |
| 浏览器 | Edge 或 Chrome 最新稳定版 |

可选：Redis（脚本可装便携版）、Nginx（仅 LAN/公网扫码时）。

---

## 三、交付包内容（应有）

```text
$ROOT/
├── 请先读_展厅部署与操作.md      ← 入口
├── 启动游戏工坊.exe               ← 一键启停
├── VERSION / CHANGELOG.md / README.md
├── backend/                       ← FastAPI（含 .env.example）
├── kiosk/                         ← 静态前端
├── templates/                     ← 7 款 Godot 模板
├── config/                        ← 规格与配方
├── assets/                        ← 素材
├── tools/                         ← 可选便携 Redis
├── 05-工具脚本/
│   ├── deploy_exhibition.ps1      ← AI/人工一键部署
│   ├── launch_workshop.py
│   ├── run_backend.ps1 / run_redis.ps1 / install_redis.ps1
│   ├── build_launcher.ps1
│   └── …
└── 开发文档/
    ├── 软件操作说明书_v1.2.md
    ├── 展厅本地服务器_AI一键部署说明_v1.2.md  ← 本文
    └── 部署手册_v1.2.md
```

**不应出现在交付包中**：`.git`、`秒哒游戏原型`、`03-背景与调研`、`backend/.venv`、`05-工具脚本/_dev_archive`。

---

## 四、逐步部署（Agent 检查清单）

### Step 1 · 解压

解压 zip 到例如 `D:\GameForge-K12\`，该目录即为 `$ROOT`。

### Step 2 · 安装 Python / Godot（若本机没有）

- Python：https://www.python.org/downloads/ → Windows 64-bit → **Add to PATH**  
- Godot 4.6 Standard：https://godotengine.org/download/windows/  
- 验证：

```powershell
python --version
& "C:\Godot\Godot_v4.6.3-stable_win64.exe" --version
```

### Step 3 · 配置 GODOT_PATH

```powershell
cd $ROOT
Copy-Item backend\.env.example backend\.env -Force
# 用本机路径替换下一行，或交给 deploy 脚本 -GodotPath 参数写入
notepad backend\.env
```

必填示例：

```env
GODOT_PATH=C:\Godot\Godot_v4.6.3-stable_win64.exe
REDIS_URL=redis://127.0.0.1:6379/0
ALLOW_MEMORY_FALLBACK=true
```

### Step 4 · 一键部署并启动

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"
```

脚本会：检查结构 → 写 `.env` → 尝试 Redis → 创建 `backend/.venv` 并 pip → 启动 **:8000 + :8080** → 打开浏览器。

### Step 5 · 健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8080/kiosk/edu/ -UseBasicParsing | Select-Object StatusCode
```

期望：`status=ok` · Kiosk `200`。

---

## 五、手动启动（调试备选）

**终端 1 · API**

```powershell
cd $ROOT
.\05-工具脚本\run_backend.ps1
```

**终端 2 · Kiosk（工作目录必须是 $ROOT）**

```powershell
cd $ROOT
python -m http.server 8080 --bind 127.0.0.1
```

---

## 六、验收标准（部署完成定义）

全部通过才可交馆方签字：

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | `/health` | JSON `status=ok` |
| 2 | B 链页 | `http://127.0.0.1:8080/kiosk/edu/` 可打开 |
| 3 | B1→B2 | 可选品类、可填名字 |
| 4 | B4→B6 | 配方提交后出证书 |
| 5 | 试玩 | Godot 窗启动；触屏可玩至少一款 |
| 6 | 日榜 | 关闭 Godot 后弹出榜或页眉可开榜 |
| 7 | 端口 | **8000**、**8080** 监听中 |

可选冒烟（开发机）：

```powershell
python 05-工具脚本\validate_creative_templates.py
python 05-工具脚本\e2e_b_edu_batch.py http://127.0.0.1:8000
```

---

## 七、可选：局域网 / 证书扫码

| 场景 | 做法 | 端口 |
|------|------|------|
| 同 Wi‑Fi 副屏 | `kiosk_lan_nginx.ps1` + 改 `config/kiosk_edu_spec.json` 的 `api_base` | **9080** |
| 手机扫码下证书 | 配 `PUBLIC_API_BASE` + nginx 反代 `/public/certificates/` | 公网 443 / 馆内约定 |

详见 [`部署手册_v1.2.md`](./部署手册_v1.2.md) §十、§十四。  
**v1.2 现状**：证书 **本机 PNG 保存**已可用；公网扫码待展馆域名。

---

## 八、停止与卸载

- 停止：启动器窗口按 Enter，或结束 `uvicorn` / `python -m http.server` 进程。  
- 卸载：停止服务后删除 `$ROOT` 即可（可保留 Godot/Python 系统安装）。  
- 勿删除他人共用的 Godot 安装目录，除非确认无人使用。

---

## 九、故障排查（Agent）

| 错误信号 | 动作 |
|----------|------|
| `Address already in use` :8000/:8080 | 结束占用 PID 后重跑 deploy |
| `play/launch` 503 | 校正 `GODOT_PATH` 后重启 API |
| Kiosk 白屏 / 配置 404 | 确认 http.server 的 cwd 是 `$ROOT` 不是 `kiosk/` |
| `session_backend: memory` | Redis 未启；可继续展厅，重启 API 会丢会话 |
| 触控键盘无效 | 必须走 `:8080/kiosk/edu/`；检查 `/kiosk/touch-keyboard/show` |

---

## 十、版本与联系索引

| 文档 | 路径 |
|------|------|
| 本部署说明 | `开发文档/展厅本地服务器_AI一键部署说明_v1.2.md` |
| 操作说明书 | `开发文档/软件操作说明书_v1.2.md` |
| 完整部署手册 | `开发文档/部署手册_v1.2.md` |
| 功能验收表 | 根目录 `AI学习小游戏创作-功能验收文档.docx`（若随包） |

---

*v1.2 · 2026-07-17 · 供 AI Agent / 展厅本地服务器一键部署*
