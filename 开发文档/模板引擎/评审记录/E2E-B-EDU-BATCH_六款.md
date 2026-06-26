# E2E-B-EDU-BATCH · B 链教育版六款品类 · 验收记录

> **日期**：2026-06-24  
> **执行**：窗 8 · P1 E2E/MCP 扩展  
> **脚本**：`05-工具脚本/e2e_b_edu_batch.py`  
> **用例定义**：`config/l1_e2e_acceptance.json` → `E2E-B-EDU-BATCH`（含 E2E-B-EDU-002~007）

---

## 结果摘要

2026-06-24 在 backend `:8000` 环境下完成 **六款品类** B 链教育版批量验收：

- **6/6 自动化断言全部 PASS**（`e2e_b_edu_batch.py` exit 0）
- **B16 MCP `run_project` 抽测**：shmup · racing · Godot 4.6.3 · `errors: []` ✅
- **硬约束**：`templates/{slug}/core/` 未修改 · 仅 workspace 注入 edu 桥

---

## 各款结果表

| case_id | slug | intent | session_id | B8–B15 | B16 MCP |
|---------|------|--------|------------|--------|---------|
| E2E-B-EDU-002 | shmup | 我想打飞机 | `670e4c16-a5f9-44ab-ada4-ab9de61eb573` | ✅ PASS | ✅ errors: [] |
| E2E-B-EDU-003 | survivor | 割草打怪 | `af2e4493-fa37-4f23-a520-2945c181277e` | ✅ PASS | — |
| E2E-B-EDU-004 | pingpong | 乒乓球 | `12e85964-6b8f-43e2-88ff-13e3fa890b1b` | ✅ PASS | — |
| E2E-B-EDU-005 | fighting | 格斗双人 | `c60eb72c-47a9-44c7-bf69-c1ab854f9bb1` | ✅ PASS | — |
| E2E-B-EDU-006 | parkour | 跑酷 | `4eae3883-e442-430b-aa85-7d7966cc79cd` | ✅ PASS | — |
| E2E-B-EDU-007 | racing | 赛车 | `b6cf623b-8df2-433e-bc95-8b8f02b97189` | ✅ PASS | ✅ errors: [] |

**BATCH 汇总**：`6/6 PASS` · `l1_e2e_acceptance.json` status → `pass_b8_b16`

---

## 断言覆盖（每款）

| ID | 检查项 | 六款 |
|----|--------|------|
| B8 | `workspace/{id}/config/game_config.json` | ✅ |
| B9 | `edu_action_bridge.gd` + `{slug}_hooks.gd` | ✅ |
| B10 | creative_answers → tuning 合并 | ✅ |
| B11 | `edu_bridge_applied=true` | ✅ |
| B12 | `project.godot` 含 `EduActionBridge=` | ✅ |
| B13 | `generate/v2` ok · code_map 非空 | ✅ |
| B14 | `play/launch` workspace 路径 | ✅ |
| B15 | `GET /play/actions` actions 数组 | ✅ |
| B16 | MCP `run_project` 无 ERROR（shmup · racing） | ✅ |

---

## 已知局限（非 FAIL）

- pingpong `power_smash`：hooks 预埋，实机可能无上报
- fighting / racing：部分 action 为启发式检测
- shmup `fire` 双发可能 2 次上报

---

## 验证命令

```powershell
# 需 run_backend.ps1 常驻 :8000
python 05-工具脚本/e2e_b_edu_batch.py http://127.0.0.1:8000

# MCP 抽测（替换 session_id）
# run_project → workspace/670e4c16-a5f9-44ab-ada4-ab9de61eb573  (shmup)
# run_project → workspace/b6cf623b-8df2-433e-bc95-8b8f02b97189  (racing)
```

---

*窗 8 · P1 · 2026-06-24*
