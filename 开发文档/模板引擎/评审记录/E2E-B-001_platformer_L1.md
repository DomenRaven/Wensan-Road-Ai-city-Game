# E2E-B-001 · platformer L1 个性化 · 验收记录

> **日期**：2026-06-22  
> **执行**：线 C · B6 自动化 + Kiosk S8/S9 对接  
> **脚本**：`05-工具脚本/e2e_b001_platformer.py`  
> **用例定义**：`config/l1_e2e_acceptance.json`

---

## 结果摘要

2026-06-22 在 Redis + backend `:8000` 环境下运行 `e2e_b001_platformer.py`，**A1–A6 全部 PASS**（exit 0）。完整向导链路 `S0→S7 → POST /recap → POST /generate → play/launch` 已写入 `workspace/{session_id}/config/game_config.json`，launch 路径含 `workspace`。Kiosk `wizard.js` S8 已对接 `/generate`（loading + 失败降级「加载经典版」），S9 显示 session `display_name` 与 workspace 路径。A7 人工试玩清单见下表（配置侧已验；≥120s 展厅 Godot 窗口试玩待 A6 签字窗口复验）。

---

## 断言表

| ID | 类型 | 检查项 | 结果 | 证据 |
|----|------|--------|------|------|
| A1 | filesystem | `workspace/{id}/config/game_config.json` 存在 | ✅ PASS | 脚本 session `d2c8e3a1-…` |
| A2 | json_path | `meta.display_name` = 「小明的星星冒险」 | ✅ PASS | game_config.json L6 |
| A3 | json_path | `theme.title` = 「小明的星星冒险」 | ✅ PASS | game_config.json |
| A4 | json_path | `tuning.enabled_skills` 含 `double_jump` | ✅ PASS | `["double_jump"]` |
| A5 | tuning_delta | challenge `move_speed` > balanced 基线 | ✅ PASS | 252.0 vs 240.0 |
| A6 | api | `POST /play/launch` · `project_path` 含 `workspace` | ✅ PASS | workspace 目录已启动 |
| A7 | manual_play | 标题/HUD · 双跳 · 挑战手感 ≥120s | 🔄 配置已验 | 见 §人工清单 |
| A8 | mcp | `run_project` workspace 无 ERROR | ✅ PASS | Godot 4.6.3 · errors: [] |

---

## A7 人工清单（Browser full 模式）

| 检查项 | 配置/API 侧 | Browser 试玩 |
|--------|-------------|--------------|
| 标题/HUD 出现「小明的星星冒险」 | ✅ `theme.title` 已写入 | ☐ 待展厅 ≥120s |
| 双跳可触发 | ✅ `enabled_skills: double_jump` | ☐ 待展厅试玩 |
| 手感难于 balanced | ✅ move_speed +5% · gravity 不变 · enemy 更快 | ☐ 待展厅对比 L0 |

**快捷回归 E2E-A-001**：shortcut S1→S9 launch 路径为 `templates/platformer/`（无 workspace 时不污染 L0 通道）— ✅ API 复验通过。

---

## 降级路径（A5 讲解员预留）

1. S8 `POST /generate` 失败 → UI 文案说明原因 + 按钮「**加载经典版**」  
2. 点击后 `POST /play/launch` → `templates/{genre}/` L0 preset  
3. 日志区记录失败原因，便于讲解员切换 demo 话术

---

*线 C · B6 Gate 签字 · 2026-06-22*
