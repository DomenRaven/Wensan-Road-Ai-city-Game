---
name: gameforge-agent-oracle-gates
description: >-
  GameForge K12 agent acceptance oracles: HF-14 evidence wiring, HF-15 L1/L2
  presentation predicates, HF-15.1 hollow-done / same-error early stop. Use when
  editing agent_contracts/game_agent gates, diagnosing Live虚空 done / false-green
  UI, writing HF docs, or running the hf14/hf15/hf15_1 pytest cluster.
---

# GameForge · Agent 预言机门禁（HF-14 / 15 / 15.1）

## 何时用本 Skill

- 改 `backend/app/services/creative/agent_contracts.py` 或 `game_agent.py` 的 done / self_check / 反馈门禁  
- Live 出现：缺符号仍宣称已实现、反复 rollback 烧轮、门禁绿但玩家看不见  
- 写/对齐 `开发文档/7.20_*证据验收*` · `*预言机分层*` · `*HF-15.1*`  
- 需要复验验收簇  

教学长文：`开发文档/7.20_教学案例_Agent预言机与虚空Done闭环_工作历程与经验_2026-07-20.md`  
（含 §10 走偏实录、§11 未竟清单——诊断时先排除「tip-only / 放宽门禁 / 专修场景」类偏航）

## 产品口径（勿偏航）

- 创作自由交给 LLM；**是否完工交给机器预言机**  
- 探针暴露通用短板；**禁止**为单场景堆 Intent if / catalog express  
- **禁止**第二模型 Judge 当 P0 过关  
- 禁止改 `templates/*/core/**`  

## 三层预言机

| 层 | 代号 | 判定什么 |
|----|------|----------|
| L1 接线 | HF-14 + HF-15 加固 | `evidence[]` 符号存在且被 caller/间接调用；拒非法形状 |
| L2 表现 | HF-15 P0 | 进度驱动 / 图标可见等 `assert_presentation_predicates` |
| 早停 | HF-15.1 | 非法 evidence；新符号须本轮写入；同错≥3 → partial；`symbols_added` |

## HF-15.1 红线（虚空 Done）

1. `.tscn` / `.tres` 路径不可当 GDScript `symbol`  
2. `wired_by` 禁止散文箭头 `->`  
3. 相对回合初 **新出现** 的符号必须在本轮 `written_paths`  
4. 同一归一化 gate 错连续 ≥3 → `_salvage` partial，停止空转  
5. 失败的同轮 `self_check` 后 `done` 不得假绿  

## 复验命令

```powershell
Set-Location "<repo>/backend"
python -m pytest tests/test_hf15_1_hollow_done.py tests/test_hf15_oracle_layers.py tests/test_hf14_evidence.py -q
```

预期：**28 passed**（以本机为准）。

Live：`python 05-工具脚本/watch_agent_live.py` —— **必须跟当前 session**，勿挂旧 sid。

## 文档入口

- 锁定：`开发文档/工作方向锁定_AI改游戏智能体_v1.md`  
- 快照：`开发文档/AI改游戏智能体_工作进度与快照_2026-07-20.md`  
- HF-15.1 施工：`开发文档/7.20_AI改游戏智能体_HF-15.1_虚空Done早停_施工规范_v1.0.md`  

## 运维红线（清理时）

- `data/learning_analytics/learning.db` **同时存认证与分析** —— 勿当「可再生缓存」直接删；否则鉴权炸，前端像「连不上后端」  
- 可清：`reports/*`、analytics `blobs/`；保留 `.gitkeep`  

## 工作方式（测→诊→方案→改→复测）

与教学案例 §4 对齐：

1. **测**：先对齐 session / 复现现象；合成簇与 Live 分层  
2. **诊**：只读 trace + 磁盘；给人根因标签；**此阶段默认不改代码**  
3. **方案**：列修通用 Agent 的选项；等人确认开修 / 红线  
4. **改**：按施工切片；不动 `templates/*/core`  
5. **复测**：约定 pytest 簇 →（可选）同题 Live → 文档状态回写  

先读施工规范进度表 → 最小改 contracts/agent → 补单测 → 跑验收簇 → 回写文档状态（立项/开修/落地）。不自动 commit，除非用户要求。
