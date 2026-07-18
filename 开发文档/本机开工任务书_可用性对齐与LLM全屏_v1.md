# GameForge K12 · 本机开工任务书

> **标题**：可用性对齐 · DeepSeek 兼容 LLM · Godot 按显示器全屏  
> **版本**：v1.0  
> **日期**：2026-07-17  
> **读者**：本机 Cursor / 实现 Agent（新对话窗口直接 `@` 本文即可开工）  
> **工作区**：仓库根目录（含 `backend/` · `kiosk/` · `templates/` · `config/`）  
> **策略**：先在本机实现并验收 → 再整包部署服务器（避免与服务器分叉来回改）

---

## 0. 本文用途

1. 汇总「服务器实测版本」与「本机 v1.2 基线」的差异。  
2. 固化用户已确认的本机实现范围（勾选项）。  
3. 作为**新窗口唯一开工依据**：不依赖聊天历史。  
4. 服务器侧 `S-A5` / `S-A6` 仅作部署备注，**本迭代不实现**。

**给 Agent 的一句话**：请严格按本文 §3～§8 在本机仓库实现；完成 §8 验收清单后汇报改动文件与残留风险。

---

## 1. 背景对照（为何改本机）

### 1.1 本机基线（当前仓库）

| 项 | 状态 |
|----|------|
| 产品版本 | v1.2（tag / `VERSION` ≈ 1.2） |
| 试玩主路径 | **外置 Godot** · `POST .../play/launch` · Win32 贴窗 |
| 触控 | `templates/_edu/*_touch_overlay.gd` + `edu_workspace.py` 注入（6/7 款；shmup 原生拖） |
| LLM / nl-patch | **无**（`llm_patch_required` 恒 false；无 `llm_patch.py`） |
| Web 内嵌 | **无** `kiosk/webgames/` · 无 `embed-game.js` |
| 顶栏 | 仍有「← 展厅快玩」 |
| B6/B7 | 仍有「加载经典版」 |
| 证书 | 本机 PNG 保存 + 扫码 API（公网域名常未配） |
| LLM 配置 | `.env.example` **无** `LLM_*` |

### 1.2 服务器曾出现的能力（团队 + Kimi）

| 项 | 服务器侧 |
|----|----------|
| 入口 | `http://10.40.94.3:40001/kiosk/edu/`（内部 API `:8000`） |
| Web 内嵌试玩 | `kiosk/edu/play/` + `kiosk/webgames/{genre}` |
| NL 改参 | `POST /sessions/{id}/nl-patch` + `nl-patch-dialog.js` |
| 局域网 LLM 网关 | 曾用馆内 Qwen；鉴权曾需 `X-API-Key` |
| 可用性补丁 | 证书闪现、会话 404 重建、去快玩/经典版等（多在服务器工作区） |

### 1.3 服务器实测痛点（本机实现时要避开）

| 现象 | 教训 |
|------|------|
| 游戏默认小窗 / 停靠异常 | **默认必须外置 Godot 按显示器全屏**，不做 iframe 停靠小窗（S-B11 不做） |
| 赛车 Web 轨灰屏 | **默认不走 Web 内嵌**；外置轨保证可玩 |
| 触控「没了」 | Web 轨易丢 overlay；**主路径保留 `_edu` 触控注入** |
| 关窗不弹榜 | 外置轨必须接通 `play/status` → 日榜 |
| AI「秒成功」像假 LLM | 必须区分 `provider: llm \| stub`，禁止静默假成功 |
| 证书本机下载 vs 展厅诉求 | 本迭代改为 **强制扫码、禁止游客本机保存** |

---

## 2. 已确认勾选总表

| ID | 结论 | 摘要 |
|----|------|------|
| **S-A1** | ✅ 要（重定义） | 启动时 **Godot 窗口按真实显示器全屏/铺满**；读实际屏尺寸（测试横屏、展厅竖屏） |
| **S-A2** | ✅ | `llm_patch` + `POST .../nl-patch`，**DeepSeek / OpenAI 兼容** |
| **S-A3** | ✅ | `nl-patch-dialog.js` AI 改代码 UI |
| **S-A4** | ✅ | `GET .../webgame-config` 等配方下发能力（**可选轨**；默认试玩仍 S-A1） |
| **S-A5** | ⏸ 服务器部署时再做 | `:40001` 安全静态服 |
| **S-A6** | ⏸ 服务器部署时再做 | API 随页面主机推导 |
| **S-B1** | ✅ | 证书自动闪现，时长 **3 秒**（不是 1.5s） |
| **S-B2** | ✅ | 多局最高分写榜 + 关窗自动弹榜 |
| **S-B3** | ✅ | 「重新试玩」可靠启动 |
| **S-B4** | ✅ | 证书 html2canvas / `color-mix` 等崩溃修复 |
| **S-B5** | ✅ | 移除「加载经典版」 |
| **S-B6** | ✅ | AI 按钮在右栏讲解演示下方并放大 |
| **S-B7** | ✅ | UI 明示 llm / stub |
| **S-B8** | ✅ | AI 过程复用 B5 同系动画 |
| **S-B9** | ✅ | 移除「← 展厅快玩」 |
| **S-B10** | ✅ | 会话 404 重建 / 起名保存失败修复 |
| **S-B11** | ❌ 不做 | 不做 iframe 停靠；全屏见 S-A1 |
| **N-1** | ✅ | 与 S-A1 合并：全屏 + 读显示器 |
| **N-2** | ✅ | 赛车等外置轨加载正常（非灰屏） |
| **N-3** | ✅ | **禁止本机保存证书；强制扫码下载** |
| **N-4** | ✅ | 关 Godot 有关闭态 + 弹榜 |
| **N-5** | ✅ | 真 LLM；改完重玩吃新参数 |
| **N-6** | ✅ | 主轨外置 Godot + 触控 overlay |

---

## 3. 硬约束（红线）

1. **禁止修改 `templates/*/core/`**。触控与教育钩子仅 `templates/_edu/` + `edu_workspace` 注入。  
2. 禁止新建：联机、存档、内购、广告、商城。  
3. 面向约 14 岁以下：无暴力血腥恐怖强化；文案儿童可读。  
4. 配方 / nl-patch 数值必须走钳制（默认 ±30%；nl-patch 可按现有白名单更严，如 ±15%，但不得越出规格）。  
5. nl-patch 白名单：**仅** `tuning.*`、`theme.*`（及项目已约定的等价路径）；不得改 core 脚本。  
6. 最小改动：禁止无关大重构、禁止大范围格式化。  
7. 前端改动后更新 `kiosk/edu/index.html` 中脚本 `?v=` 缓存戳。  
8. 真实密钥只写本地 `backend/.env`，可更新 `.env.example` 占位，**不提交真实 Key**。  
9. **不要**在本迭代实现 S-A5/S-A6；可在本文或短备注中写部署步骤即可。  
10. 未用户明确要求时 **不 `git commit`**。  
11. 若改动触及 `config/frozen_*.json` 覆盖文件：实现后注明路径，**不擅自 re-freeze**（等人确认再跑 freeze 脚本）。

---

## 4. 功能规格（逐项）

### 4.1 S-A1 / N-1 · Godot 按显示器全屏

**目标**：点击「开始试玩 / 重新试玩 / 用新参数试玩」时，本机拉起的 Godot **默认全屏或铺满当前显示器工作区**，禁止默认小窗。

**要求**：

- 几何必须来自**真实显示器**：前端上报屏幕 / `client_viewport` / 浏览器所在屏；后端 Win32 枚举窗并 `SetWindowPos` 或等价全屏。  
- **测试机可能横屏，展厅部署多为竖屏**——禁止写死 1920×1080 或固定横竖；按「游戏所在那块屏」的当前宽高与方向适配。  
- 与现有 `orientation.js`、godot-zone 上报字段对齐；竖屏/横屏切换后再次 launch 仍正确。  
- 归位/全屏失败：不阻断试玩，但 UI 有可读提示。

**非目标**：S-B11 式 iframe 停靠小窗；不要把 Web 内嵌设为默认。

---

### 4.2 N-6 · 触控主路径

- 主试玩轨 = **外置 Godot** + generate/v2 注入的 `_edu/*_touch_overlay.gd`（既有 6 款 + shmup 策略保持）。  
- 验收：至少抽测 platformer / parkour / racing 触控可玩。  
- 不得为了 Web 轨删掉或跳过 overlay 注入。

---

### 4.3 N-4 · 关窗状态 + 弹榜

- 轮询 `play/status`（或等价）检测 Godot 进程结束。  
- UI 明确「游戏已关闭 / 未在运行」（禁止仍显示「请到游戏窗口试玩」死态）。  
- 触发日榜逻辑（见 S-B2）。

---

### 4.4 N-2 · 赛车等加载

- 外置轨下 racing（及其他品类）画面正常，非灰屏。  
- 若实现 S-A4 的 Web 辅助能力，Web 灰屏**不得**影响默认外置 launch。

---

### 4.5 S-A4 · webgame-config（可选轨能力）

- 实现或补齐：`GET /sessions/{id}/webgame-config`（及前端如需写入 `localStorage` / 配置下发的辅助）。  
- **默认「开始试玩」不走 iframe**；本项为兼容/预留。  
- 可不引入完整 `kiosk/webgames/` 大资源，除非验收明确需要；优先 API + 接口契约完整。

---

### 4.6 S-A2 · nl-patch 后端（DeepSeek 兼容）

**新增**（名称可微调，职责不变）：

- `backend/app/services/creative/llm_patch.py`  
- 路由：`POST /sessions/{session_id}/nl-patch`  
- 行为：读 workspace `game_config.json` → LLM 或 stub 生成白名单 patch → 钳制 → 写回 → 返回变更摘要 + **`provider`**

**环境变量**（写入 `Settings` + `backend/.env.example`）：

```env
# DeepSeek 官方示例（OpenAI 兼容）
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=
LLM_MODEL=deepseek-chat

# 馆内兼容网关示例（可选）
# LLM_BASE_URL=http://10.x.x.x:10010/v1
# LLM_API_KEY=
# LLM_MODEL=your-model-id
```

**调用约定**：

| 项 | 约定 |
|----|------|
| 协议 | OpenAI / DeepSeek 兼容 Chat Completions |
| URL | `POST {LLM_BASE_URL}/chat/completions`；若 `LLM_BASE_URL` 已以 `/v1` 结尾则接到该前缀 |
| Header | 必发 `Authorization: Bearer {LLM_API_KEY}`；建议同时发 `X-API-Key: {LLM_API_KEY}` 以兼容部分网关 |
| Body | `model` / `messages` / 适度 `temperature`；要求模型只输出可解析的 JSON patch |
| 成功 | HTTP 业务成功且应用 patch；`provider: "llm"` |
| 无 Key / 超时 / 非 2xx / 解析失败 | `provider: "stub"` 或明确错误；**禁止** 200 + 假装 llm |
| 安全 | 只改白名单路径；拒绝「改 core / 加联机」类超纲 |

**测试**：`backend/tests/` 增加 nl-patch 白名单与 stub 用例（memory store + tmp_path）；有 Key 时可选手工测 DeepSeek。

---

### 4.7 S-A3 / S-B6 / S-B7 / S-B8 / N-5 · AI 改代码前端

- 新增 `kiosk/edu/nl-patch-dialog.js`（并在 `index.html` 引入）。  
- **位置**：右侧「讲解员演示」按钮下方；竖屏随右栏/下方主操作区；按钮放大（建议 min-height ≥ 56px，触控友好）。  
- **显隐**：**仅 B6/B7** 显示；**B5 代码剧场阶段不得出现**（S-B12 原诉求，并入本条）。  
- **三态建议**：输入 → 加载（复用 B5 `build-wait` / theater-overlays 同系动画）→ 结果。  
- **结果文案**：明确「AI 大模型已改」vs「本地快速规则 / 可重试」；绑定 `provider`。  
- **完成后**：提供显眼「▶ 用新参数试玩」；并与工具栏「重新试玩」共用启动通路；必须 `force` relaunch，使 Godot 读到最新 `game_config.json`。

---

### 4.8 S-B1 · 证书自动闪现 3 秒

- `generate/v2` 成功进入 B6（或剧场结束进入完成态）时自动展示证书。  
- 模式 `auto_flash`：**停留约 3 秒**后自动关闭。  
- 闪现态：**不显示**「保存证书」等操作按钮；不阻断「开始试玩」。  
- 手动「查看证书」走完整模式（但完整模式的下载策略见 N-3）。

---

### 4.9 N-3 · 强制扫码，禁止本机保存

- **去掉或默认隐藏**游客向「保存证书到本机」主按钮。  
- 引导：**手机扫二维码**下载；二维码 = `PUBLIC_API_BASE`（或 bootstrap 下发的 public base）+ `/public/certificates/{token}`。  
- 上传 PNG 到后端、发 token 的服务端流程保留（扫码需要）。  
- **未配置 `PUBLIC_API_BASE`**：不得把「本机另存为」当成功主路径；展示「展馆扫码下载暂未开通 / 请配置可访问下载地址」；可用隐藏调试开关（默认关）供开发。  
- 自动闪现 3s 仍无保存钮。  
- 修复 S-B4：避免 `color-mix()` 等导致 html2canvas 崩溃（若仍需服务端侧生成预览图，以保证二维码链路）。

---

### 4.10 S-B2 · 多局最高分 + 自动弹榜

- 同一试玩会话内可多局；提交日榜时取**本会话最高分**（按品类主排序键，与现有 `leaderboard` 一致）。  
- 关 Godot 窗后自动弹今日榜（与 N-4 衔接）。  
- 讲解场景可接受「关窗弹一次」；避免无分数空弹（无有效 `run_complete` 时可跳过或提示）。

---

### 4.11 S-B3 · 重新试玩

- 统一 `launchCurrentGame({ reason })`（名称可调）：供开始试玩 / 重新试玩 / AI 改完再玩。  
- 防连点；loading/disabled；失败儿童可读。  
- 行为 = S-A1 全屏 launch + 最新 workspace。

---

### 4.12 S-B5 / S-B9 · 移除按钮

- 删除「加载经典版」DOM、事件、文案、死代码。  
- 删除顶栏「← 展厅快玩」DOM 与相关 CSS；布局无空洞。  
- 保留「今日榜单」「重新开始」。

---

### 4.13 S-B10 · 会话重建

- 根因对齐服务器修复经验：`ensureSession` 遇 404 **必须清除旧 session_id** 再创建。  
- 「完成创作 / 重新开始 / release」后完整 bootstrap + `POST /sessions`。  
- PATCH / wizard 等写操作遇 `Session not found`：自动重建并重试一次，或强制回 B0 并提示；禁止红字「保存失败」死局。  
- 不硬刷新走完「完成 → 再起名」必须通过。

---

### 4.14 S-B4 · 证书光栅化

- 排查证书相关 CSS（含 `color-mix`、不支持的色值）；改为 html2canvas 可处理的颜色（如预计算 rgba）。  
- 保证证书层在需要光栅化时不抛错（即使 N-3 弱化本机下载，上传/预览仍可能需要）。

---

## 5. 明确不做（本迭代）

| 项 | 说明 |
|----|------|
| S-A5 | `serve_lan_kiosk.py` / 固定 `:40001`（服务器部署再做） |
| S-A6 | LAN 下 API 随主机（服务器部署再做） |
| S-B11 | iframe 停靠小窗 |
| Web 内嵌作默认试玩 | 与 N-6 / S-A1 冲突 |
| 改 `templates/*/core/` | 红线 |
| 擅自 re-freeze | 只汇报 |
| git commit | 除非用户要求 |
| 公网域名实装 | 配置项预留；展馆域名由运维填 `PUBLIC_API_BASE` |

---

## 6. 建议实现顺序

```text
1. S-B10 会话重建
2. S-B5 + S-B9 移除按钮
3. S-A1 / N-1 全屏按显示器 + S-B3 统一 launch
4. N-4 关窗态 + S-B2 最高分弹榜
5. S-B1（3s 闪证书）+ S-B4 + N-3 强制扫码
6. S-A2 nl-patch 后端（DeepSeek）
7. S-A3 + S-B6/7/8 + N-5 AI UI 与 relaunch
8. S-A4 webgame-config（默认不接 UI 主按钮）
9. N-6 触控回归 · N-2 赛车等外置冒烟
10. 通跑 §8 验收 · 写改动清单
```

---

## 7. 关键文件地图（勘察入口）

| 区域 | 路径 |
|------|------|
| B 链主控 | `kiosk/edu/edu-wizard.js` |
| 会话 | `kiosk/edu/session.js` |
| 证书 | `kiosk/edu/certificate.js` · `edu-styles.css` |
| 日榜 | `kiosk/edu/leaderboard.js` |
| 顶栏/引入 | `kiosk/edu/index.html` |
| 剧场动画复用 | `kiosk/edu/build-wait.js` · `theater-overlays/` |
| 试玩 API | `backend/app/routers/play.py` · `sessions.py` |
| 启动/贴窗 | `backend/app/services/godot_launcher.py` · `godot_window_layout.py`（以仓库实名为准） |
| 教育注入 | `backend/app/services/edu_workspace.py` |
| 创作分析 | `backend/app/services/creative/` |
| 配置 | `backend/app/config.py` · `backend/.env.example` |
| 触控 | `templates/_edu/*_touch_overlay.gd` |
| 操作说明 | `开发文档/软件操作说明书_v1.2.md` |

---

## 8. 本机验收清单（全部勾选才算完成）

### 8.1 流程与 UI

- [ ] B0→B7 主路径可走通（意图 → 起名 → 问卷 → 剧场 → 完成）  
- [ ] B5 代码剧场期间 **无**「AI 改代码」  
- [ ] 进 B6 后证书自动闪现约 **3 秒** 后消失，闪现态无保存钮，可点「开始试玩」  
- [ ] 无「← 展厅快玩」  
- [ ] 无「加载经典版」  

### 8.2 试玩 · 全屏 · 触控 · 关窗

- [ ] 「开始试玩」拉起 Godot，**全屏/铺满当前显示器**（改分辨率或横竖屏仍正确）  
- [ ] 触控 overlay 抽测通过（platformer / parkour / racing）  
- [ ] racing（及抽测品类）外置轨非灰屏  
- [ ] 「重新试玩」可再次全屏启动  
- [ ] 关闭 Godot 窗口后 UI 显示已关闭，并 **自动弹日榜**  
- [ ] 同会话多局后榜上为 **最高分**  

### 8.3 AI / LLM

- [ ] AI 按钮在右栏讲解演示下方且足够大  
- [ ] 请求中有 B5 同系加载动画  
- [ ] 配置 DeepSeek（或兼容网关）Key 时 `provider=llm`，耗时合理（非无 Key 却显示大模型已改）  
- [ ] 无 Key / 失败时为 stub 或明确错误，文案不误导  
- [ ] 「用新参数试玩」后手感/配置变化可感知  

### 8.4 证书 · 会话

- [ ] 无游客主路径「保存到本机」；引导扫码；未配 `PUBLIC_API_BASE` 时提示符合 N-3  
- [ ] 「完成创作/重新开始」后 **不硬刷新** 再起名，无 `Session not found` /「保存失败」死局  
- [ ] `templates/*/core/` 无改动  

### 8.5 回归

- [ ] 「今日榜单」「重新开始」、讲解员演示按钮可用  
- [ ] `GET /health` 正常；本机 Kiosk + API 可按既有方式启动  

---

## 9. 完成汇报格式（Agent 必须按此输出）

1. **改动文件列表**（路径级）  
2. **逐 ID 状态**（已完成 / 未做 / 阻塞 + ≤3 句说明）  
3. **§8 验收勾选结果**  
4. **`.env.example` 新增项**与本地验证步骤（如何配 DeepSeek、如何开馆启动）  
5. **残留风险**（仅 P2 及以下）  
6. **是否建议进入「打包部署服务器」**：是 / 否 + 一句话理由  
7. 若触及 frozen 覆盖文件：列出路径，**等待人工确认是否 freeze**

---

## 10. 服务器部署备注（本迭代不编码）

待本机验收通过后，部署到 Linux 展厅机时再处理：

| ID | 内容 |
|----|------|
| S-A5 | 安全静态服（拦截 `/.env`、`/.git` 等），对外固定 **`http://10.40.94.3:40001`**，禁止改端口 |
| S-A6 | 前端 API 随页面主机推导；防火墙放行 `:8000` 或反代 |
| 环境 | `GODOT_PATH` 改为 Linux 二进制；`DEPLOYMENT_SERVER_OS=linux` |
| LLM | `LLM_*` 指向 DeepSeek 或馆内兼容网关；双头鉴权按需 |
| 证书 | 配置手机可达的 `PUBLIC_API_BASE`，否则扫码不可用 |
| 覆盖策略 | 用本机验收通过的版本覆盖服务器，避免继续在服务器裸改分叉 |

历史重启参考（服务器曾用，部署时按当时脚本为准）：

```bash
# 示例 · 以部署时文档为准
cd "/path/to/project"
# uvicorn :8000 + 安全静态服 :40001
```

---

## 11. 附录 · 历史问题 ID 速查（人工可用性）

| 原编号 | 对应本任务 |
|--------|------------|
| U-01 剧场后证书 | S-B1（改为 3s） |
| U-02 关窗分数榜 | S-B2 · N-4 |
| U-03 重新试玩 | S-B3 |
| U-04 证书保存/二维码 | N-3 · S-B4 |
| U-05 加载经典版 | S-B5 |
| U-06 AI 按钮位置 | S-B6 |
| U-07 假 LLM | S-B7 · N-5 · S-A2 |
| U-08 AI 动画 | S-B8 |
| U-09 改完无法再玩 | N-5 · S-B3 |
| U-10 展厅快玩 | S-B9 |
| U-11 起名 Session 404 | S-B10 |
| U-12 剧场期 AI 按钮 | 并入 S-A3 显隐 |
| 小窗 / 灰屏 / 无触控 | S-A1 · N-1 · N-2 · N-6 |

---

## 12. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-07-17 | 首版：本机开工范围固化；S-A1 重定义为 Godot 按显示器全屏；证书闪 3s；N-3 强制扫码；LLM DeepSeek 兼容；S-A5/A6 留服务器 |

---

*新窗口开工：读取本文 → 按 §6 顺序实现 → 按 §8 验收 → 按 §9 汇报。*
