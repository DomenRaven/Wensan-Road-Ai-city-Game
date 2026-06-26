# GameForge K12 · Kiosk

> **状态（2026-06-22）**：**线 A 产品 UI v1** · L0 快速通道 ✅ · **线 B S8/S9 个性化对接 ✅**  
> **产品规格**：[`config/kiosk_ui_spec.json`](../config/kiosk_ui_spec.json)  
> **双轨计划**：[`开发文档/模板引擎/D6-D10双轨并行计划_v1.0.md`](../开发文档/模板引擎/D6-D10双轨并行计划_v1.0.md)

展厅触控双栏向导，对接 FastAPI backend。

## 线 A · 快速通道（默认）

`track_a_shortcut_flow`：**S0 可选起名 → S1 必选品类（**7 款精选**大卡片）→ S9 直启试玩**

- 品类入口：**大卡片宫格**，禁止 `<select>` 作主入口
- 触控：按钮/卡片 min-height **48px**
- 顶部：进度点 + 作品名
- 试玩：`POST /sessions/{id}/play/launch` → `templates/{genre}/` L0

## 线 B · 完整向导（S0–S9）

页脚切换「完整创作向导」进入 **S0→S7 → ★R 配方卡 → S8 → S9**。

### S8 · AI 制作

- 进入 S8 后**自动**执行：
  1. 若未确认 recap → `POST /sessions/{id}/recap`
  2. `POST /sessions/{id}/generate` → 写入 `workspace/{session_id}/`
- UI：loading  spinner + 分步文案（确认配方 / 复制模板 / 写入 config）
- **成功** → 自动进入 S9
- **失败** → 错误文案 +「**加载经典版**」（`play/launch` → `templates/{genre}/`）+「重试制作」

### S9 · 试玩

- full 模式且 generate 成功：banner 显示「你的专属版本 · workspace 已就绪」+ workspace 路径
- 作品名：session `display_name`（顶栏 + 试玩卡）
- `POST /play/launch` 优先 `workspace/{session_id}/`（由 backend B4 决定）
- shortcut 模式：仍走 `templates/{genre}/` L0

## B 链隔离（2026-06-23）

- **模板只读**：`templates/{genre}/` 永不写入；B 链仅 `copytree` → `workspace/{session_id}/`
- **启动校验**：Kiosk 打开时 `GET /bootstrap`（backend 启动时亦执行一次）
- **释放会话**：`POST /sessions/{id}/release` 或 DELETE · 同步删除 workspace 副本
- **意外退出**：`pagehide` sendBeacon release；下次开馆 bootstrap 清理孤立 workspace
- **用户互不影响**：每 session UUID 独占目录 · config merge 带路径守卫

规格：`config/kiosk_ui_spec.json` → `b_chain_isolation`

## 启动

```powershell
.\05-工具脚本\run_redis.ps1
.\05-工具脚本\run_backend.ps1
cd 仓库根目录
python -m http.server 8080
# http://127.0.0.1:8080/kiosk/
```

## 文件

| 文件 | 说明 |
|------|------|
| `index.html` | 产品布局 · 双栏 + 顶栏进度 |
| `styles.css` | 触控规格 · 宫格/卡片 · S8 loading |
| `wizard.js` | 步骤机 · 快速通道 + 完整向导 S8/S9 |

## 验收

- 线 A：`config/l1_e2e_acceptance.json` → **E2E-A-001**（选 platformer → 启动试玩）
- 线 B：同文件 → **E2E-B-001**（`python 05-工具脚本/e2e_b001_platformer.py`）
- 评审记录：[`开发文档/模板引擎/评审记录/E2E-B-001_platformer_L1.md`](../开发文档/模板引擎/评审记录/E2E-B-001_platformer_L1.md)

## LAN 部署（草案）

```powershell
.\05-工具脚本\kiosk_lan_nginx.ps1
```

## Cursor 约束

`.cursor/rules/dual-track-kiosk.mdc`
