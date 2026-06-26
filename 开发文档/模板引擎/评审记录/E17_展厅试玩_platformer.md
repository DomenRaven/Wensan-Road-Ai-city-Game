# E17 · 展厅试玩验收 · platformer

> **展陈 P0** · B 链教育版 B7 · **人工实机**  
> **日期**：2026-06-24 · **操作员**：DomenR · **环境**：本地模拟展厅

---

## 前置

- [x] 窗16 E-P0-18 已合入（launch UI + `launchState` 门控轮询）— 2026-06-24
- [x] 窗15 E-P0-17 已合入（左侧真 config）— 2026-06-24
- [x] `run_backend.ps1` + `http.server 8080`（2026-06-24 Agent 预检：`:8000` / `:8080` 均 200）

---

## Agent 预检（不替代人工签字 · 2026-06-24）

| 项 | 结果 | 说明 |
|----|:----:|------|
| `E2E-B-EDU-001` API 全链 | ✅ | generate/v2 · edu 桥 · launch workspace |
| `e2e_b_edu_browser_smoke` 7/7 | ✅ | Playwright · platformer 含真 config 校验 |
| `validate_creative_templates` | ✅ | 7/7 |
| Godot workspace 启动 | ✅ | `godot-mcp run_project` 无 ERROR |
| `POST /play/launch` | ✅ | 指向 `workspace/{id}/` 非 templates 回退 |
| `GET /play/actions` 轮询 | ✅ | 含 `jump` · 已修 `t_ms` 游标（`code-highlight.js`） |
| Godot 桥写日志 | ✅ | 见下方 `.edu_actions.jsonl` 片段（含 `stomp_enemy`） |

**预生成试玩会话（Agent 预检留档 · 人工可走新会话）**

- `session_id`: `869ddada-37b1-4992-bd9a-167eedc6e471`
- `display_name`: 星星大冒险
- `jump` 锚点：`config/game_config.json` L12 · `jump_velocity: -440`
- `stomp_enemy` 锚点：`core/player_platformer.gd` L264

**高亮证据片段**（`workspace/869ddada-…/.edu_actions.jsonl` · Godot 实机写入，非 B7 模拟按钮）：

```jsonl
{"action_id":"jump","t_ms":1782303181473}
{"action_id":"stomp_enemy","t_ms":1782303187890}
{"action_id":"stomp_enemy","t_ms":1782303188873}
```

查询：`GET http://127.0.0.1:8000/sessions/869ddada-37b1-4992-bd9a-167eedc6e471/play/actions?since=0`

---

## 人工验收结论（2026-06-24）

操作员确认已完成 **E17 人工实机试玩**：

- `/kiosk/edu/` → platformer 全链 B0–B7
- B6「开始试玩」成功 launch · 外置 Godot 窗口
- Godot 真操作触发跳跃、踩怪左侧代码高亮
- 连续试玩 **≥120s**
- **未**使用 B7「讲解员演示用」模拟按钮过关

> 截图 / 精确起止时间 / 本次 `session_id` 可展前补入「证据」列；不阻塞窗18 技术收工。

---

## 执行记录（须讲解员/产品人工勾选）

| 项 | 要求 | 结果 | 证据 |
|----|------|:----:|------|
| 路径 | `/kiosk/edu/` → platformer 全链 B0–B7 | ✅ | 操作员确认 |
| B6 真代码 | 左侧含用户 tuning/display_name | ✅ | 操作员确认 |
| B6 launch | 点「开始试玩」成功（非演示模式） | ✅ | 操作员确认 |
| B7 状态卡 | 外置 Godot 引导 · 非 embed 占位 | ✅ | 操作员确认 |
| launch | 外置 Godot 窗口打开 | ✅ | 操作员确认 |
| 跳跃高亮 | ≥1 次（**Godot 真操作**） | ✅ | `jump` 锚点高亮 |
| 踩怪高亮 | ≥1 次（**Godot 真操作**） | ✅ | `stomp_enemy` 锚点高亮 |
| 连续时长 | ≥120s | ✅ | 操作员确认 ≥120s |
| 模拟按钮 | 未用模拟过关 | ✅ | 操作员确认 |

---

## 问题记录

| 严重度 | 描述 | 处理 |
|--------|------|------|
| 低 | `code-highlight.js` 轮询仅用 `cursor` 未读 `t_ms`，可能重复高亮 | 已修：游标取 `t_ms ?? cursor` |

---

## 签字

| 角色 | 姓名 | 日期 | 通过 |
|------|------|------|:----:|
| 技术验收 | （待填） | 2026-06-24 | ☑ |
| 产品/讲解 | （待填） | | ☐ |

---

*窗18 收工 · 2026-06-24 · 人工试玩由操作员确认 · GitHub v1.0 已推送*
