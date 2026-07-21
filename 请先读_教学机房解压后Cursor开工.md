# GameForge K12 · 教学机房 · 解压后请先读

> **交付包**：`GameForge-K12-v1.2-lab-classroom-20260721.zip`（或同目录最新 `lab-classroom` 包）  
> **场景**：**一台学生机兼教室服务器** · 其余学生机连它 · S2-路B（`local_share`）  
> **Git 冻结标签**：`lab-s2b-freeze-20260721-v1.2`

---

## 1. 解压到哪里

推荐固定路径（与文档一致）：

```text
E:\project\GameForge-K12\
```

解压后应能看到：`backend/` · `kiosk/` · `开发文档/` · `05-工具脚本/` · `机房部署现场记录/` · `VERSION`

---

## 2. 在选中机器上安装 Cursor 后

1. 用 Cursor **打开文件夹** → 选 `E:\project\GameForge-K12`  
2. **新开对话**，打开并复制整段开工词：  
   **`开发文档/7.21_教学机房_学生机兼服务器_Cursor开工提示词_2026-07-21.md`**  
3. 粘贴发送 → Agent 会自动：测 IP · 查端口 · 配 `.env` · SMB 共享 · 发布 `_tools` · 启服 · 验收  

---

## 3. 其余学生机（不装 Cursor 也行）

服务器 Agent 验收通过后，记下 **`$ServerIp`** 与 **`$NetUser`**，在每台学生机管理员 PowerShell 执行：

```powershell
powershell -ExecutionPolicy Bypass -File "E:\project\GameForge-K12\05-工具脚本\deploy_lab_student_v2.ps1" `
  -ServerIp "<教室服务器LAN_IP>" `
  -NetUser "<LAN_IP>\<Windows_SMB用户名>"
```

或复制 **`机房部署现场记录/学生机_巡检表.md`** 内「一键部署 v2」整段（改前两行 IP/账号）。

---

## 4. 人工必带（包内不含）

| 项 | 说明 |
|----|------|
| **Godot 4.6 Standard** | 安装或 zip 解压到 `C:\Godot\`（Agent 会写 `GODOT_PATH`） |
| **LLM_API_KEY** | 写入 `backend\.env`，勿提交 Git |
| **GameForgeLabHelper.exe v1.0.1+** | 若无预编译 exe，Agent 在服务器上跑 `05-工具脚本\build_lab_helper.ps1` |
| **SMB 密码** | 本机 Windows 用户（全班可共用一个，见巡检表 TEST1 说明） |

---

## 5. 文档索引（Agent 也会读）

| 用途 | 路径 |
|------|------|
| **Cursor 开工词（服务器）** | `开发文档/7.21_教学机房_学生机兼服务器_Cursor开工提示词_2026-07-21.md` |
| PowerShell 按序手册 | `开发文档/7.21_教学机房S2路B_PowerShell按序执行手册_2026-07-21.md` |
| 学生机 deploy v2 | `机房部署现场记录/学生机_巡检表.md` |
| 经验母本 | `开发文档/7.21_教学案例_机房S2路B部署_工作历程与经验_2026-07-21.md` |
| 冻结快照 | `开发文档/7.21_教学机房S2路B_冻结快照_2026-07-21.md` |

---

## 6. 硬限制（Win11 专业版 SMB）

同一台 **Windows 11 专业版** 作 SMB 服务器时，**同时 persistent 映射 Z: 的学生机约 ≤20 台**。  
25 人课可用 **≤20 台同时连共享**；其余机可浏览器上课但试玩需等空位或换 Win Server 教室机。

学生入口（部署完成后）：`http://<教室服务器IP>:8080/kiosk/edu/`
