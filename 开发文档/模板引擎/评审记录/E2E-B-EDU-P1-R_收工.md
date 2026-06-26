# E2E-B-EDU-P1-R · P1-R 窗9–13 收工记录

> **日期**：2026-06-24  
> **执行**：窗 13 · P1-R 浏览器冒烟 + 整合清单 12/12  
> **脚本**：`05-工具脚本/e2e_b_edu_browser_smoke.py`  
> **用例定义**：`config/l1_e2e_acceptance.json` → `E2E-B-EDU-BROWSER`

---

## P1 12/12 摘要

| 阶段 | 范围 | 状态 |
|------|------|------|
| P1 窗1–8 | 六款配置 + hooks + HTTP E2E + MCP | ✅ |
| P1-R 窗9 | P1-04 意图词表 + B1 七芯片 | ✅ |
| P1-R 窗10 | P1-05/06 B4 skill_pick + B2 API | ✅ |
| P1-R 窗11 | P1-08 POST `/play/action` | ✅ pytest 4/4 |
| P1-R 窗12 | P1-09 `?mode=edu` 分流 + 返回链 | ✅ |
| P1-R 窗13 | 浏览器冒烟七款 + 文档回写 | ✅ **本记录** |

**整合清单**：[`6.24_整合任务清单_v1.0.md`](../6.24_整合任务清单_v1.0.md) P1-04~09 全 ✅ · 进度 **12/12**

**施工手册 §六**：6/6（含 #5 kiosk/edu 换意图进 B4）

---

## 浏览器冒烟（#6）

**实现路径**：Playwright（Chromium headless）· 打开 `http://127.0.0.1:8080/kiosk/edu/`  
**首条 platformer**：`http://127.0.0.1:8080/kiosk/?mode=edu` → `location.replace('edu/')` 已断言

**结果**：**7/7 PASS** · `mode=playwright` · exit 0

| slug | case_id | B1 意图 | B2 作品名 | B4 要点 | generate/v2 | #workName |
|------|---------|---------|-----------|---------|-------------|-----------|
| platformer | E2E-B-EDU-001 | 我想玩马里奥闯关 | 星星大冒险 | q_skill: double_jump | ✅ | ✅ |
| shmup | E2E-B-EDU-002 | 我想打飞机 | 雷霆小队 | q_skill: bomb | ✅ | ✅ |
| survivor | E2E-B-EDU-003 | 割草打怪 | 糖果幸存者 | q_skill: magnet | ✅ | ✅ |
| pingpong | E2E-B-EDU-004 | 乒乓球 | 弹弹乐 | q_skill: curve_ball | ✅ | ✅ |
| fighting | E2E-B-EDU-005 | 格斗双人 | 像素拳王 | **4×single_choice · 无 skill** | ✅ | ✅ |
| parkour | E2E-B-EDU-006 | 跑酷 | 无尽奔跑 | q_skill: slide | ✅ | ✅ |
| racing | E2E-B-EDU-007 | 赛车 | 欢乐赛车 | q_skill: boost | ✅ | ✅ |

**向量来源**：`e2e_b_edu_batch.SLUG_CASES`（import 复用 · 未复制 answers）· platformer 对齐 `e2e_b_edu_platformer.py`

**fighting 确认**：`b4_skill_count: 0` · `fighting_no_skill: true` · 未点击 `.skill-chip`

---

## 回归命令输出

### 浏览器冒烟（本窗主验）

```powershell
# 前置：run_backend.ps1 :8000 · python -m http.server 8080
python 05-工具脚本/e2e_b_edu_browser_smoke.py --kiosk http://127.0.0.1:8080 --api http://127.0.0.1:8000
# → 7/7 PASS · mode=playwright
```

### HTTP 批量（窗8 回归）

```powershell
python 05-工具脚本/e2e_b_edu_batch.py --api http://127.0.0.1:8000
# → 6/6 PASS
```

### play/action（窗11 回归）

```powershell
python -m pytest backend/tests/test_play_action.py -q
# → 4 passed
```

---

## 遗留（不挡 P1 12/12）

| ID | 项 | 说明 |
|----|-----|------|
| E17 | 人工展厅试玩 | platformer B7 跳/踩怪高亮 ≥1 次 · ≥120s · Godot 实机 |
| P2 | NLU/LLM | `match-genre` 低置信追问 · `llm_patch` · 展后可砍 |
| 6.23 D6 | A 链 Kiosk 深联调 | 与 6.24 并行 · 非 P1-R 范围 |
| 6.23 D7 | Windows exe 导出 | 展陈演示导出 |

---

## 交付物清单

| 路径 | 说明 |
|------|------|
| `05-工具脚本/e2e_b_edu_browser_smoke.py` | 新建 · Playwright + HTTP 降级 |
| `config/l1_e2e_acceptance.json` | 新增 `E2E-B-EDU-BROWSER` |
| `开发文档/模板引擎/6.24_整合任务清单_v1.0.md` | P1 12/12 |
| `开发文档/模板引擎/工作状态记录_v1.0.md` | §6.24 窗9–13 全 ✅ |
| `开发文档/模板引擎/6.24_P1_六款并行施工手册_v1.0.md` | §六 6/6 |
| `开发文档/模板引擎/6.24_文件映射表_v1.0.md` | browser 脚本 · play/action · entry_modes |
| `开发文档/模板引擎/6.24_P1-R_总控对接与启动_v1.0.md` | 仪表盘 P1-R 全 ✅ |

---

*窗 13 · P1-R 收工 · 2026-06-24*
