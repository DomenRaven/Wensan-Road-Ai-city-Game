# AI 改游戏智能体 · 施工规范手册 v1

> **对齐**：需求规格 **v1.2**  
> **配套**：[`文件映射表`](./AI改游戏智能体_文件映射表_v1.md) · [`开工提示词 v3`](./AI改游戏智能体_全任务开工提示词_v3.md)  
> **读者**：实现 Agent（Cursor）  

---

## 0. 施工目标

交付一条 **品类无关** 管道，使任意用户需求在会话副本上 **可感知可玩**，而非单品类补丁。

验收口诀：**配置有 · 代码通 · 接线活 · 触屏点 · 门禁过 · 手动重开。**

---

## 1. 红线

1. **禁止**改 `templates/{genre}/core/**` 等玩法冻结源。  
2. **允许**改 `templates/_edu/**`（桥、触控、chrome）并经 `edu_workspace` 注入。  
3. Agent 只写 `workspace/{session}/`。  
4. **禁止**模型发明 `add_method` / 不存在节点 API 后 `done`。  
5. **禁止**修单局 workspace 冒充系统验收。  
6. **禁止** commit / 推远程 / 提交 `.env`，除非用户明确要求。  
7. 非主线任务见 [`工作方向锁定`](./工作方向锁定_AI改游戏智能体_v1.md)，默认不做。

---

## 2. 标准施工顺序（实现 Agent 自己改仓库时）

1. 读需求 v1.2 §4 + 本手册 + 文件映射。  
2. 用 todo 拆：**路由 → 契约 runtime → 桥/触屏 → 门禁 → kiosk → 单测**。  
3. 先契约与门禁，再桥 API，再 UI；避免只补某一品类。  
4. 单测：幻想 API / 虚假声称 / 触屏 how_to_play / 契约加载。  
5. Live：换品类抽测一句需求 → 手动重开 → 可感知。  
6. `godot-mcp run_project` 无 ERROR（抽测模板或临时 workspace）。  
7. 更新需求修订记录 / CHANGELOG（若用户要求）。

---

## 3. 意图路由施工规范

### 3.1 四类意图

| 码 | 判定线索 | 强制动作 |
|----|----------|----------|
| A | 命中 catalog id/中文标签 | `enable_catalog_skill`；禁止只 write 空壳 |
| B | 更快/更慢/颜色/生成 | tuning 或会话 core 或已有桥 API |
| C | 新机制且桥已有 API | 仅 `ai_sandbox` + `apply(bridge)` |
| D | 需要新挂钩 | **停** → 扩桥真方法 + 写契约 → 再按 C |

### 3.2 实现要求（P0-通用）

- 增加确定性路由器（可规则 + LLM 辅助）：输出 `{intent, recipe_id, actions[]}`。  
- `write_file` / `done` 前校验 actions 与 recipe 一致。  
- 偏离时返回 error 文案，迫使再改。

---

## 4. 契约施工规范

文件：`config/agent_contracts/{genre}.json`

### 4.1 必填字段

同需求 §4.4；**v1.2 起 catalog_skills 建议**：

```json
{
  "id": "bomb",
  "label": "清屏炸弹",
  "desc": "...",
  "trigger": "触屏按钮「炸弹」",
  "runtime": {
    "input": "action:bomb",
    "effect": "bridge:activate_bomb",
    "touch": "overlay_or_ensure_touch_action"
  }
}
```

### 4.2 edit_recipes

每条必须含：`intent` · `action` · `paths` · `hint`。  
新增用户话术时 **先加 recipe，再改 Agent**。

### 4.3 禁止幻想列表

全局 + 品类；与 `assert_apis_in_contract` 同步。

---

## 5. 三层落地施工规范

| 层 | 允许产物 | 完成定义 |
|----|----------|----------|
| L1 | `game_config.json` 字段 | 磁盘可读且 schema 合理 |
| L2 | `core/**` 或 `ai_sandbox/*.gd` | 可解析；无禁 API |
| L3 | 桥方法被调用 / 输入能触发效果 / 触屏可见 | **玩家能操作到效果** |

**Done 规则**：声称「可玩的技能/机制」时 L1+L3 必须同时满足；仅 L1 → 门禁失败。

沙箱脚本模板：

```gdscript
extends Node
func apply(bridge) -> void:
	bridge.rainbow_player_bullets()  # 仅契约内 API
```

---

## 6. 桥与触屏施工规范

### 6.1 扩桥

1. 在 `ai_sandbox_bridge.gd` 增加 **强类型** 真方法。  
2. 写入相关 `agent_contracts/*.json` 的 `bridge_apis`。  
3. 补 edit_recipes / notes。  
4. 单测：允许调用 / 禁止幻想。  
5. 可选：sandbox 示例路径写入 genre_context。

### 6.2 触屏

- **过渡**：品类 `*_touch_overlay.gd` + `edu_workspace` 注入。  
- **目标**：桥 `ensure_touch_action(action_id, label)` 统一创建 overlay 只做布局。  
- 新操作未挂触屏 → **不得 done**（how_to_play 门禁 + runtime.touch 检查）。

### 6.3 Edu 注入

改 `_edu` 或 `edu_workspace.py` 后：必须 **新会话** 才生效；旧 workspace 不自动补丁。文档与 UI 提示「请重新制作一局」。

---

## 7. 门禁施工规范

实现位置：`agent_contracts.py` · `game_agent.py`

| 检查 | 失败行为 |
|------|----------|
| 无写入 | 拒 done |
| GDScript 坏 / 幻想 API | 拒写入或拒 done |
| 声称 ⊈ 磁盘 | 拒 done |
| how_to_play 无重开 / 无触屏 | 拒 done |
| catalog「启用了 X」但无 X | 拒 done |
| runtime 检查点（目标） | 拒 done |

进度：`emit_progress` 阶段名与 kiosk `PHASES` 对齐。

---

## 8. Kiosk 施工规范

- 等待：中文阶段 + 可轮询 progress。  
- 成功：展示 summary / how_to_play / 徽章；**禁止自动 onReplay**。  
- 提供「▶ 现在重开游戏」。  
- stub / agent 徽章诚实。

---

## 9. 窗口施工规范

- Godot 侧：`window_chrome_overlay` 启动铺满 + always_on_top。  
- 后端：Win32 `HWND_TOPMOST`，去边框后 `SWP_FRAMECHANGED`，启动后二次置位。  
- 勿用会丢掉置顶的 exclusive fullscreen 作为唯一方案。

---

## 10. 测试与验收

### 10.1 单测必过

- 契约七品类加载  
- 幻想 API 拦截  
- 虚假声称拦截  
- 触屏 how_to_play 门禁  
- 进度写入  

### 10.2 Live 抽测矩阵（最少）

| 品类 | 示例话术 | 期望可感知 |
|------|----------|------------|
| shmup | 技能少 + 彩色子弹 | 触屏技能 + 着色 |
| platformer | 二段跳 / 金币 buff | 跳跃或 buff |
| 再抽 1～2 品类 | 开 catalog 技能 | 触屏可点 |

### 10.3 回归红线

- `templates/{genre}/core` 无业务 diff  
- 不把 `.env` 提交进 git  

---

## 11. Learned Skill

- 仅高质量 / gate 通过优先入库  
- 含幻想 API → rejected  
- 「没生效」→ fail_count 强降权  
- 晋升只导出提案 JSON  

---

## 12. 提交与沟通

- 默认不 commit；用户要求时再按仓库规范提交。  
- 回复用户：先结论，再改动面；指向本手册章节即可。  

---

## 修订

| 日期 | 说明 |
|------|------|
| 2026-07-18 | v1：对齐需求 v1.2 通用工作流 |
