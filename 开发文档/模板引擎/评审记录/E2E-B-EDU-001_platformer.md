# E2E-B-EDU-001 · B 链教育版 platformer · 验收记录

> **日期**：2026-06-24  
> **执行**：窗 5 · P0-E 联调验收  
> **脚本**：`05-工具脚本/e2e_b_edu_platformer.py`  
> **用例定义**：`config/l1_e2e_acceptance.json` → `E2E-B-EDU-001`

---

## 结果摘要

2026-06-24 在 `py310_torch251_cu121` + backend `:8000` + Kiosk `:8080/kiosk/edu/` 环境下完成 **E2E-B-EDU-001** 全链路验收：

- **E0–E15 自动化断言全部 PASS**（`e2e_b_edu_platformer.py` exit 0）
- **E16 MCP `run_project`**：Godot 4.6.3 · `errors: []` ✅
- **浏览器联调**：静态资源 200 · B0–B7 真 API 走通 ✅
- **pytest**：`tests/test_creative_platformer.py` PASS

代表 session：`464841a8-e01d-417b-b13b-8339ef3a0fdd`

---

## 断言表

| ID | 类型 | 检查项 | 结果 | 证据 |
|----|------|--------|------|------|
| E0 | api | `GET /bootstrap` ready | ✅ PASS | ready=true |
| E1 | api | `POST /sessions` | ✅ PASS | 201 |
| E2 | api | `POST /intent/match-genre` → platformer | ✅ PASS | confidence=1.0 |
| E3 | api | `POST wizard/S0` display_name | ✅ PASS | 「星星大冒险」 |
| E4 | api | `GET /creative/templates/platformer` | ✅ PASS | genre=platformer |
| E5 | api | `POST creative/answers` | ✅ PASS | q_move/jump/enemy/skill |
| E6 | api | `POST analyze-requirements` preset-only | ✅ PASS | 4 resolutions · jump in preview |
| E7 | api | `POST generate/v2` | ✅ PASS | ok=true · code_map 含 jump |
| E8 | filesystem | `workspace/{id}/config/game_config.json` | ✅ PASS | tuning 已合并 |
| E9 | filesystem | `core/edu_action_bridge.gd` + `platformer_hooks.gd` | ✅ PASS | generate 注入 |
| E10 | json_path | move_speed=240 · jump=-440 · patrol=65 · double_jump | ✅ PASS | game_config.json |
| E11 | session_payload | `edu_bridge_applied=true` | ✅ PASS | GET /sessions/{id} |
| E12 | filesystem_text | `project.godot` 含 `EduActionBridge=` | ✅ PASS | autoload 已补丁 |
| E13 | api_response | `code_map` 含 jump | ✅ PASS | generate/v2 |
| E14 | api | `POST /play/launch` workspace 路径 | ✅ PASS | workspace/{id} |
| E15 | api | `GET /play/actions` actions 数组 | ✅ PASS | 初始 `[]` |
| E16 | mcp | `run_project` workspace 无 ERROR | ✅ PASS | Godot 4.6.3 · errors: [] |
| E17 | manual_play | B7 跳跃/踩怪高亮 · actions 轮询 | 🔄 待展厅 | 见 §人工清单 |

---

## 浏览器联调（B0–B7）

| 阶段 | 端点 / 资源 | 结果 |
|------|-------------|------|
| B0 | `GET /bootstrap` | ✅ 200 ready |
| B0 | `http://127.0.0.1:8080/kiosk/edu/index.html` | ✅ 200 |
| B0 | `edu-wizard.js` · `code-highlight.js` · `kiosk_edu_spec.json` | ✅ 200 |
| B1 | `POST /intent/match-genre` | ✅ 200 |
| B2 | `POST /sessions/{id}/wizard/S0` | ✅ 200 |
| B4 | `GET /creative/templates/platformer` + `POST creative/answers` | ✅ 200 |
| B5 | `POST /analyze-requirements` | ✅ 200 |
| B6 | `POST /generate/v2` | ✅ 200 |
| B7 | `POST /play/launch` + `GET /play/actions?since=0` | ✅ 200 |

`code-highlight.js` 已接 `GET /sessions/{id}/play/actions` 轮询（非纯 mock）；B6/B7 保留模拟按钮作降级演示。

---

## E17 人工清单（展厅 ≥120s）

| 检查项 | API/配置侧 | Browser 试玩 |
|--------|------------|--------------|
| 左侧代码剧场 B5 流畅滚动 | ✅ code_theater.jsonl 已加载 | ☐ 待展厅 |
| 跳跃触发 jump 高亮 | ✅ code_map.jump · hooks 已挂载 | ☐ 待 Godot 窗口试玩 |
| 踩怪触发 stomp_enemy 高亮 | ✅ code_map.stomp_enemy | ☐ 待 Godot 窗口试玩 |
| `.edu_actions.jsonl` ↔ `/play/actions` 一致 | ✅ 桥接文件存在 | ☐ 操作后轮询验证 |

---

## 硬约束复核

- `templates/platformer/core/` **未修改**（仅 workspace 副本注入 `_edu` 桥）
- `generate/v2` 写入仅限 `workspace/{session_id}/`
- `edu_bridge_applied` 与会话 payload 一致

---

## 验证命令

```powershell
# E2E 自动化（需 backend :8000）
python 05-工具脚本/e2e_b_edu_platformer.py http://127.0.0.1:8000

# pytest 回归
cd backend
$env:PYTHONPATH="."
python -m pytest tests/test_creative_platformer.py -q

# Kiosk 静态 + 浏览器
python -m http.server 8080
# http://127.0.0.1:8080/kiosk/edu/

# MCP（workspace 路径替换为 E2E session_id）
# run_project → workspace/{session_id}
```

---

*窗 5 · P0-E · 2026-06-24*
