# Reference · Agent 多工具循环（全开）

对齐总纲：有 Key 时从第 1 轮起全开工具，开放读盘，放宽轮次以完成 goals。

## 推荐回合节奏

1. **理解**：把用户原话拆成 `goals[]`（条件、数值、手感各一条）。  
2. **读盘**：`diagnose_workspace` → `list_dir` → `read_file` / `search_in_file`；优先本局近期改动路径与本品类 `SKILL.md`。  
3. **可选材料**：`search_learned_skills` / Reference；Catalog 在 goals 合适时再用。  
4. **施工**：已有大脚本/场景默认 `replace_text`；`write_file` 用于新文件、小配置或 goals 标明的完整重构；桥 API / 触屏按钮按需；带条件的需求用脚本实现条件本身。  
5. **自检**：`validate_gdscript` → `self_check` → 玩家健康 / dry-run。  
6. **收工**：`done.summary` 覆盖全部 goals；试玩说明含重开与触屏。

## 预算

- 首段最多 16 轮；有写盘进展可软续杯 +16  
- 墙钟 360s：超时诚实 partial，可继续下一轮对话  

## 定位技巧

- 反馈类：对照「状态是否成对开闭」（外观、特效、速度、充能等）  
- 找角色：`group=player` 或桥 `get_player_node()`（开局多在 GameRoot 下）  
- 改已有脚本：先 read，再改相关函数  
