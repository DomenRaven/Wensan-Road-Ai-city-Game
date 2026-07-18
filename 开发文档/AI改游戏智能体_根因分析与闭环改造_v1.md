# AI 改游戏智能体 · 根因分析与闭环改造方向 v1.0

> **日期**：2026-07-18  
> **触发**：shmup 会话「飞机技能太少 / 五颜六色子弹 / 护盾」——对话声称成功，重开后未实装  
> **会话样例**：`workspace/4d4af5ed-b12c-4a92-892d-804a28bfc501`（当时未回首页，文件仍在）  
> **结论归属**：智能体架构缺口，而非单局手修、亦非「换更大模型即可」  
> **关联需求**：[`AI改游戏智能体需求_v1.md`](./AI改游戏智能体需求_v1.md)（**已升至 v1.2**）  
> **后续落地**：施工 [`…_施工规范手册_v1.md`](./AI改游戏智能体_施工规范手册_v1.md) · 映射 [`…_文件映射表_v1.md`](./AI改游戏智能体_文件映射表_v1.md) · 开工 [`…_全任务开工提示词_v3.md`](./AI改游戏智能体_全任务开工提示词_v3.md) · 主线 [`工作方向锁定_AI改游戏智能体_v1.md`](./工作方向锁定_AI改游戏智能体_v1.md)

---

## 1. 现象与磁盘事实（样例）

| 用户 / Agent 声称 | 磁盘事实 |
|-------------------|----------|
| 新增「护盾」技能 | `enabled_skills` 仅 `bomb` + `laser_beam`；无 shield 脚本/图标 |
| 子弹五颜六色 | 仅有 `colored_bullet_modifier.gd`，且为无效 GDScript |
| 三技能：左炸弹 / 右护盾 / 彩色自动 | catalog 最多 2 个预制；护盾在机体内是**捡道具**，非对话 skill |
| 重开后生效 | 无可运行正确改动 → **不生效是预期** |

无效脚本特征：`bridge.add_method`（不存在）、`Color.red`（Godot 4 应为 `Color.RED`）、`bullet.set_color`（`bullet.gd` 无此方法）、未挂入 `bullet_pool` / `activate` 生成链。

**旁路结论（窗口）**：启动有「铺满显示器 + 去边框」；**无** `ALWAYS_ON_TOP` / `HWND_TOPMOST`（`SWP_NOZORDER`），故非「永远最上层」。属产品缺口，与本次「未实装」并列记录。

---

## 2. 一句话根因

当前 Agent 是 **「写文件 + 口头 done」** 开环；缺少秒哒式 **「契约能力面 → 按挂钩施工 → 写后验证 → 声称对齐磁盘 → 失败再改」** 闭环。  
LLM 不笨，是 **可执行约束与验收缺失**。

---

## 3. 因果链（七条）

### 3.1 无「可调用能力契约」→ 幻想 API

- Bridge 真实 API：`watch_coins` / `grant_invincibility` / `boost_move_speed` / `show_countdown` / `flash_player_fx` / `set_tuning_number` 等。  
- 工具层只拦危险片段（OS.execute 等），**不拦「调用了不存在的方法」**。  
- 落盘成功 ≠ 可运行。

### 3.2 品类接线知识极不均衡

- `genre_context`：platformer 有完整 playbook；**shmup 仅两三行**。  
- 未说明：子弹生成链、bomb/laser 输入、护盾是道具而非 catalog。  
- 模型只能用通用 GDScript 幻觉填空。

### 3.3 无写后验收即允许 `done`

现有工具：`list_dir` / `read_file` / `write_file` / `enable_catalog_skill` / `search_learned_skills` / `done`。  

缺失：

| 工具/门禁 | 作用 |
|-----------|------|
| `validate_gdscript` | 语法/能否被解析 |
| `assert_apis_exist` | 脚本调用 ⊆ 已公布 bridge/节点 API |
| `assert_hooks` | 是否接到生成链/输入链 |
| `dry_run` / headless | 启动无 SCRIPT ERROR |
| `assert_claims` | summary 声称 ⊆ 磁盘/config 事实 |

### 3.4 「可改会话 core」与提示「优先只写沙箱」未路由

- 产品已允许改会话 `core/*.gd`。  
- System 仍强调优先 `ai_sandbox` + `apply(bridge)`。  
- 对「改子弹颜色」类需求，正确路径是改会话 `bullet.gd`/`bullet_pool` 或**扩展真实桥 API**；实际路径却是假钩子。

### 3.5 轮次激励偏向「快 done」

- 「尽量 1～3 轮内 done」→ 少读、少验、早结束。  
- 展厅可接受 **等待数分钟**，应用进度 UI 换取可靠闭环，而非压缩正确性。

### 3.6 Learned Skill 会放大错误经验

- 入库偏「写过什么」，缺「游戏里验证过」。  
- 「没生效」降权不够强时，坏片段会被再次检索推荐 → **错误复利**。

### 3.7 提示自相矛盾

- `genre_context` 仍写「禁止改已有 core」；需求已允许会话副本改 core。  
- 模型更不敢改真挂钩文件。

---

## 4. 对照：秒哒 / WorkBuddy vs 当前

| 维度 | 秒哒类 | 当前 GameForge Agent |
|------|--------|----------------------|
| 工程感知 | 符号/调用/报错 | 文件名列表 + 薄 playbook |
| 工具 | 编辑 + lint + 跑测 | 几乎只有读写 |
| 完成判据 | 测试/运行通过 | LLM 自说 done |
| 失败恢复 | 看日志再改 | 靠用户说「没生效」 |
| API 面 | 受限工具 | 开放写码、无执行白名单 |

---

## 5. 改造方向（已认可 · 写入需求 v1.1）

按优先级：

1. **Capability Contract（每品类）**  
   `bridge_apis` · `catalog_skills` · `edit_recipes`（需求类型→改哪些文件/字段）· `forbidden_invented_apis`。

2. **`done` 门禁（硬挡）**  
   声称必须对齐磁盘；新 `.gd` 必须解析通过且 API ∈ 契约；不过则禁止 done、强制再改。

3. **扩桥 / 标准挂钩（宁扩真 API，勿让模型发明钩子）**  
   例 shmup：`tint_enemy_bullets` / `grant_temp_shield` 等做成真实 `AiSandboxBridge` 方法。

4. **七品类 playbook 对齐 platformer 深度**  
   并删除「禁止改会话 core」的过时表述（templates 仍只读）。

5. **运行/反馈进经验库**  
   仅验证通过或用户未报「没生效」的片段高权重；「没生效」强降权。

6. **需求路由器**  
   目录技能 → `enable_catalog_skill`；生成链/外观 → 会话 core 或专用 bridge；禁止假 `add_method`。

7. **进度可视化**  
   允许 Agent 工作 **数分钟**；kiosk / 后端日志 **美观打印阶段进度**（读契约→检索→读写→校验→done）。

8. **窗口（并行产品项）**  
   启动全屏 + **Always on Top**（Win32 TOPMOST / Godot flag）。

---

## 6. 非目标（重申）

- 不为「修某一局会话」当主交付。  
- 不 fine-tune 云端基座；能力增长 = 契约 + 验证过的 Skill Store。  
- 不自动改 `templates/**` / 官方 `optional_skills.json`（晋升仍人工）。

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-18 | v1.0：基于 shmup 未实装案例的系统根因与闭环方向；方向已获产品认可 |
