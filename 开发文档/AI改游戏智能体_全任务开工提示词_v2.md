# AI 改游戏智能体 · 全任务开工提示词 v2（归档）

> **状态**：已被 [`AI改游戏智能体_全任务开工提示词_v3.md`](./AI改游戏智能体_全任务开工提示词_v3.md) 取代。  
> **请改用 v3**（对齐需求 **v1.2** 通用落地工作流）。本文仅保留闭环门禁阶段历史。  
> 需求：[`AI改游戏智能体需求_v1.md`](./AI改游戏智能体需求_v1.md)（现为 **v1.2**）  
> 根因：[`AI改游戏智能体_根因分析与闭环改造_v1.md`](./AI改游戏智能体_根因分析与闭环改造_v1.md)

---

## 启动命令（整段粘贴）

```text
@开发文档/AI改游戏智能体需求_v1.md
@开发文档/AI改游戏智能体_根因分析与闭环改造_v1.md
@.cursor/rules/godot-mini-game.mdc

【全任务开工 · 智能体闭环 v1.1】按需求规格 v1.1 + 根因分析文档，一次性落地「可自行实现用户需求」的 Agent 闭环。本仓库 GameForge K12。

═══ 背景（勿再做成「只写文件口头 done」）═══
根因：当前是开环「猜代码→write→done」；缺 Contract、写后验收、品类挂钩、声称对齐磁盘。
样例：shmup「护盾+彩色子弹」声称成功但无效脚本/无护盾配置。目标不是修那一局，而是让日后 Agent 自己做对。

═══ 已拍板 ═══
1. 短对话弹层 B6/B7；可等待数分钟，必须美观打印/展示进度（阶段名中文）
2. 可改会话 core/config/scenes；现场可写技能；templates 只读
3. release 先 harvest（验证质量优先）再销毁；Learned Skill 长期库
4. done 门禁：声称⊆磁盘；无幻想 API；校验不过禁止成功返回
5. 宁扩真桥 API，勿让模型发明 add_method
6. Godot 试玩：全屏 + Always on Top
7. LLM 失败才 stub，UI 诚实

═══ 交付（按序，用 todo）═══
P0-闭环
- config/agent_contracts/ 七品类契约（bridge_apis / catalog / edit_recipes / hooks / notes）
- 重写 genre_context：删「禁止改会话 core」；shmup 等对齐 platformer 深度
- game_agent：注入契约；validate_gdscript；assert_apis_in_contract；assert_claims；进度 emit
- done 硬挡 + 多轮再改（允许数分钟）
- kiosk：美观多阶段进度（升级 wait UI）；agent/stub 徽章；没生效续聊

P0-桥
- AiSandboxBridge 补 shmup 等真 API（如子弹着色、临时护盾），并写进契约与示例路由

P0-窗
- godot_launcher / window_layout：全屏 + HWND_TOPMOST / ALWAYS_ON_TOP（去掉阻碍置顶的 SWP_NOZORDER）

P1
- dry_run/headless；Skill 验证加权与「没生效」强降权；坏片段拒绝入库

P2
- 晋升提案/导入导出（已有可加固，不改 templates 自动写入）

═══ 现状入口（演进，勿另起炉灶）═══
backend/app/services/creative/game_agent.py
backend/app/services/agent_workspace.py
backend/app/services/creative/genre_context.py
backend/app/services/creative/learned_skills.py
backend/app/services/creative/llm_patch.py
templates/_edu/ai_sandbox_bridge.gd
backend/app/services/godot_launcher.py
backend/app/services/godot_window_layout.py
kiosk/edu/nl-patch-dialog.js
kiosk/edu/llm-create-wait.js

═══ 验收 ═══
1. 单测：门禁拦住幻想 API / 虚假声称；契约加载；进度事件
2. 用真实 LLM 回归：「飞机技能太少，多加有趣的技能，子弹要五颜六色」→ 重开后可感知（着色或诚实说明上限）；不得再口头护盾却无落地
3. 七品类 stub+抽测 live；templates 未改
4. Godot：全屏置顶；run_project 无 ERROR
5. 对照需求 §7 逐条打勾

═══ 红线 ═══
禁止改 templates/** 玩法源（_edu 桥可改并注入）
不 commit/推远程除非我要求
不把 .env 入库
不做「修单局 workspace 糊弄验收」

按 P0-闭环 → P0-桥 → P0-窗 → P1 → P2 实施。开始干活。
```

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-18 | v2：对齐需求 v1.1 闭环 / 进度 / 置顶；替换旧「只堆 P0 harvest」开工词 |
