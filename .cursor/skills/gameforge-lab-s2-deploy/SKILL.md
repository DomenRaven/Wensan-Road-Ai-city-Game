---
name: gameforge-lab-s2-deploy
description: >-
  GameForge K12 teaching lab S2-路B deployment: server 0.0.0.0, SMB Z: drive,
  GameForgeLabHelper v1.0.1, local_share play launch, student batch deploy v2.
  Use when deploying classroom servers/student PCs, diagnosing Godot not launching,
  net use / Copy-Item failures, or updating 机房部署现场记录.
---

# GameForge · 机房 S2-路B 部署 Skill

## 何时用本 Skill

- 教室服务器 **`PLAY_LAUNCH_MODE=local_share`** · IP 为实测 LAN（原 `10.71.121.18` 或 **学生机兼服务器** 探测 IP）  
- 学生机批量 deploy · §8/§9 · 助手 `:17890`  
- 现象：「本机试玩就绪」但 Godot 不弹 · `Copy-Item \\...` 找不到 · `net delete` 中断  
- 写/对齐 `7.21_教学机房_*` · `机房部署现场记录/`  

**经验母本**：`开发文档/7.21_教学案例_机房S2路B部署_工作历程与经验_2026-07-21.md`

## 架构一口径

- **浏览器** → 服务器 API/Kiosk（`0.0.0.0:8000/8080`）  
- **试玩** → API 只回 `project_path` → 本机助手 `POST :17890/launch` → Godot 开 **Z:\{session}**  
- **两套账号**：Windows SMB（`net use Z:`）≠ GameForge 网页登录  

## 红线

- 机房常驻用 **`GameForgeLabServer.exe --server-ip <LAN>`**，勿用 `启动游戏工坊.exe`（127.0.0.1）  
- 禁止改 `templates/*/core/**`  
- 禁止删 `learning.db`  
- 助手须 **v1.0.1+**（`local_drive_root()` 修 `Z:\` 路径）  

## 学生机 deploy v2 顺序（不可打乱）

1. `cmd /c "net use Z: /delete /y >nul 2>&1"`（静默，新机无 Z: 正常）  
2. `net use Z: \\10.71.121.18\GameForgeWorkspace /user:<Windows用户>`  
3. `Test-Path Z:\_tools\{GameForgeLabHelper.exe, launch-session-godot.ps1, Godot\...}`  
4. `Copy-Item` → `C:\GameForge\`  
5. `GameForgeLabHelper.exe deploy --skip-net-use`  
6. 启动助手 · `/health` → `version=1.0.1`  

**完整脚本**：`机房部署现场记录/学生机_巡检表.md`

## 诊断速查

| 现象 | 先查 |
|------|------|
| Win11 SMB 满（错误 71） | `Get-SmbSession` Count≈20 · ≤20 台同时 Z: |
| UNC Copy-Item 找不到 | 先 `net use Z:`，勿 UNC 直拷 |
| `net delete` 找不到网络连接 | 新机正常；用 cmd 静默 delete，勿 Stop 中断 |
| `/launch` → `Z:session` 无 `\` | 助手 < 1.0.1，更新 `_tools` |
| UI「试玩就绪」非「已启动」 | 助手 `/launch` 失败；看 PowerShell 非 UI |
| 手动 ps1 能开浏览器不能 | 助手 launch 或浏览器拦截 localhost |

**launch 验收**：

```powershell
Invoke-RestMethod http://127.0.0.1:17890/health
# local_path 须 Z:\xxx
Invoke-RestMethod http://127.0.0.1:17890/launch -Method POST -ContentType application/json `
  -Body (@{ project_path="<SessionPath>"; force=$true } | ConvertTo-Json)
```

## 服务器验收

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health   # play_launch_mode=local_share
Test-Path "E:\project\GameForge-K12\workspace\_tools\GameForgeLabHelper.exe"
Test-Path "E:\project\GameForge-K12\workspace\_tools\Godot\Godot_v4.6.3-stable_win64.exe"
```

pytest 门禁簇（Agent 基线，非机房专用）：`backend` 下 hf14/15/15.1 · **28 passed**

## 文档索引

| 用途 | 路径 |
|------|------|
| 执行任务 | `开发文档/7.21_教学机房_执行任务清单_2026-07-21.md` |
| PowerShell 手册 | `开发文档/7.21_教学机房S2路B_PowerShell按序执行手册_2026-07-21.md` |
| 冻结快照 | `开发文档/7.21_教学机房S2路B_冻结快照_2026-07-21.md` |
| 学生机兼服务器 Cursor 词 | `开发文档/7.21_教学机房_学生机兼服务器_Cursor开工提示词_2026-07-21.md` |
| deploy v2 脚本 | `05-工具脚本/deploy_lab_student_v2.ps1` |
| 新窗对接 | `开发文档/7.21_教学机房_工作总结与新窗对接_2026-07-21.md` |
| §9 足迹 | `机房部署现场记录/2026-07-21_§9验收与助手v1.0.1热修.md` |

## 改代码范围（机房轨）

- `05-工具脚本/lab_godot_helper.py` · `launch_lab_server.py` · 打包 ps1  
- `kiosk/edu/edu-wizard.js` · `config/kiosk_edu_spec.json`  
- `机房部署现场记录/` · `开发文档/7.21_*`  
- **勿** 与 Agent HF 施工混在同一会话（除非用户显式切换）
