# GameForge K12 本地 RAG 知识库

> **用途**：将爬虫报告 + 项目文档索引为可检索知识库，供 Cursor Agent / 脚本调用。  
> **技术**：SQLite FTS5 + BM25（无 GPU、无外部 API）

---

## 构建索引

```powershell
cd "E:\文三路AI馆\2.ai生成游戏\05-工具脚本"
E:\文三路AI馆\1未来隧道部分\研究资料\AI出行体验舱_技术调研\crawler\.venv\Scripts\python.exe build_rag_index.py
```

产出：
- `rag/index/gameforge_rag.db`
- `rag/index/manifest.json`

## 检索

```powershell
python query_rag.py "Godot 塔防 数值平衡" -k 5
python query_rag.py "godot-mcp Cursor" --source crawl
python query_rag.py "core tuning theme" --source dev --json
```

## Cursor Agent 使用建议

在 Prompt 前追加：

```text
先执行: python 05-工具脚本/query_rag.py "{用户主题}" -k 5 --json
将命中片段作为依据，禁止编造未在 RAG 或项目文档出现的库名/版本。
```

## 索引范围

| source_type | 内容 |
|-------------|------|
| crawl | 最新 crawler 报告（已过滤噪声） |
| dev | 技术选型、功能点、品类参数、架构、业务流、**执行规范、自动化控制、独立评审、审核报告、使用手册** |
| survey | 调研整合报告 |

## 更新时机

- 爬虫续跑或整合报告更新后 → 重新 `build_rag_index.py`
- 开发文档 v1.x 变更后 → 重新构建
