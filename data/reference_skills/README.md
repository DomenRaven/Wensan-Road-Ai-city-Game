# Reference Skills · 策展参考包（非 Learned）

> **地位**：总纲 G9 · 只读参考材料，**不是** catalog express，**不是** harvest 自动入库结果。  
> **权威总纲**：[`开发文档/7.19_AI改游戏智能体_总体设计需求_v1.0.md`](../../开发文档/7.19_AI改游戏智能体_总体设计需求_v1.0.md)  
> **来源**：[`SOURCES.md`](./SOURCES.md)

## 用法（Agent / 人工）

1. 先 `diagnose` / `read_file` 会话磁盘，再对照本目录对应品类 `SKILL.md`。  
2. 社区通识（强类型、信号解耦、稳妥取节点）以 `_common/` 为准；**品类路径以本仓库为准**。  
3. 未经验证试玩的机制，写成提案即可，有效 Learned Skill 需通过试玩验证。

## 目录

| 路径 | 内容 |
|------|------|
| `_common/agent_loop.md` | 多工具循环 · 读盘优先 · 最小编辑 |
| `_common/godot4_gdscript.md` | Godot 4 / GDScript 通识（已裁到本产品） |
| `{genre}/SKILL.md` | 七品类：真实节点/脚本/常见需求落点 |
| `index.json` | 机读索引（genre → 文件） |

## 与 `data/learned_skills/` 区别

| | Reference | Learned |
|--|-----------|---------|
| 来源 | 策展 + 对照 templates | 有效会话 harvest |
| 删除 | 随版本维护 | 回主页不删库；清库走运维 API |
| 失败局 | 不写入 | 否定态不入库有效 Skill |
