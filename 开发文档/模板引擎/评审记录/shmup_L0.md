# shmup L0 评审记录

- **日期**：2026-06-20
- **评审轮次**：R2（并发 Agent + 主线程修复）
- **MCP errors**：无
- **总分**：**84 / 100**

## 硬门槛 H1–H6

| # | 项 | 结果 |
|---|-----|------|
| H1 | MCP run_project 无 ERROR | PASS |
| H2 | 仅 templates/shmup/ | PASS |
| H3 | core 锁定 + config 驱动 | PASS |
| H4 | K12 · ≤3 键 | PASS（移动+射击+炸弹技能可选） |
| H5 | Kenney 素材 | PASS |
| H6 | 节点/深度 | PASS |

## 分项得分

| 维度 | 得分 | 说明 |
|------|------|------|
| A 可运行 | 25/25 | |
| B 玩法闭环 | 18/20 | 波次+得分+胜负 |
| C 配置驱动 | 15/15 | |
| D 规格符合 | 13/15 | 子弹池+纵版 |
| E K12 安全 | 10/10 | UFO 卡通风 |
| F 工程约束 | 3/10 | 128 子弹池节点 |
| G 展陈观感 | 5/5 | |

## 结论

**通过**（≥80 · 硬门槛全过）

## R2 修复摘要

- 场景内嵌贴图 → 运行时 load(theme
- bullet deactivate 改 call_deferred
- scroll_background 背景色路径修正
