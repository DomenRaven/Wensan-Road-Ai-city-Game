# parkour L0 评审记录

- **日期**：2026-06-20
- **评审轮次**：R1（Agent + 主线程 MCP 复验 + R2 贴图 fallback 修复）
- **MCP errors**：无（R2 后）
- **总分**：**85 / 100**

## 硬门槛 H1–H6

| # | 项 | 结果 |
|---|-----|------|
| H1 | MCP run_project 无 ERROR | PASS（R2 修复 `.import` 无 PNG 时 load 报错） |
| H2 | 仅 templates/parkour/ | PASS |
| H3 | core 锁定 + config 驱动 | PASS |
| H4 | K12 · ≤3 键 | PASS |
| H5 | Kenney 素材 | PASS（Image.load_from_file + 色块 fallback） |
| H6 | 节点/深度 | PASS |

## R2 修复

- 新增 `core/theme_sprite.gd`：`FileAccess.file_exists` + `Image.load_from_file`，避免 `ResourceLoader.exists` + `load()` 在仅有 `.import` 无 PNG 时输出 ERROR

## 待完善（不阻塞 D5）

- 三车道换道
- long/branch/trick prefab
- 视差背景层
- Jumper Pack P0 素材
- 清理 junction 下无效 `.import` 缓存（可选）

## 结论

**通过**（≥80 · 硬门槛全过）
