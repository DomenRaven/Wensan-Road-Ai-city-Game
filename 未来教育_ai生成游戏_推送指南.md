# 未来教育 · AI 生成小游戏 · Gitea 推送指南 v1.0

> **仓库**：`http://10.70.160.61:3002/3240103625/zwm.git` · **GitHub**：https://github.com/DomenRaven/Wensan-Road-Ai-city-Game  
> **工作目录**：`e:\文三路AI馆\2.ai生成游戏`  
> **专用分支**：`gameforge-k12`  
> **main 归属**：`e:\文三路AI馆\1未来隧道部分`（未来隧道部分，与本项目隔离）  
> **并列分支**：`lobby-mechanical-screen` → `3.前厅机械屏视频`

---

## 1. 分支与目录

| 分支 | 项目 | 本地目录 | 合并至 main |
|------|------|----------|-------------|
| `main` | 未来隧道部分 | `e:\文三路AI馆\1未来隧道部分` | — |
| `lobby-mechanical-screen` | 前厅机械屏视频 | `e:\文三路AI馆\3.前厅机械屏视频` | 否 |
| **`gameforge-k12`** | **AI 小游戏创作工坊** | **`e:\文三路AI馆\2.ai生成游戏`** | **否** |

```text
zwm
├── main                      → 1未来隧道部分
├── lobby-mechanical-screen   → 3.前厅机械屏视频（orphan 独立线）
└── gameforge-k12             → 2.ai生成游戏（orphan 独立线）
```

| 规则 | |
|------|--|
| Git 根目录 | `2.ai生成游戏` |
| pull / push 目标 | 仅 `gameforge-k12` |
| 禁止 | 在 `main` 提交本项目；复制至 `1未来隧道部分` 再提交；PR 合并至 `main`；`git pull origin main` |

---

## 2. 仓库参数

| 项 | 值 |
|----|-----|
| Gitea | http://10.70.160.61:3002 |
| 远程 | `http://10.70.160.61:3002/3240103625/zwm.git` |
| 参考指南 | `3.前厅机械屏视频/前厅机械屏视频_推送指南.md` |
| 未来隧道参考 | `1未来隧道部分/开发文档/AI出行体验舱_Gitea推送指南_v1.0.md` |

---

## 3. 首次推送

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
Set-Location "e:\文三路AI馆\2.ai生成游戏"

git init
git remote add origin http://10.70.160.61:3002/3240103625/zwm.git
git checkout --orphan gameforge-k12
git add .
git commit -m "docs: AI小游戏创作工坊项目初始入库（v1.1 文档体系）"
git push -u origin gameforge-k12
```

远程已存在 `origin` 时：

```powershell
git remote set-url origin http://10.70.160.61:3002/3240103625/zwm.git
```

验证：http://10.70.160.61:3002/3240103625/zwm · 分支 `gameforge-k12` · 根目录含 `文档目录说明.md`、`开发文档/`、`03-背景与调研/`

---

## 4. 日常推送

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
Set-Location "e:\文三路AI馆\2.ai生成游戏"

git checkout gameforge-k12
git pull origin gameforge-k12
git add .
git commit -m "docs: 简要说明本次变更"
git push origin gameforge-k12
```

---

## 5. 提交前检查

| 项 | 要求 |
|----|------|
| 分支 | `gameforge-k12` |
| 目录 | `2.ai生成游戏` |
| 敏感文件 | 不含 `.env`、密钥、Token、LLM API Key |
| 大文件 | `checkpoint.json`、`.exe`、`exports/` 由 `.gitignore` 排除 |
| RAG 库 | `gameforge_rag.db` 可入库（约 1.5MB）；变更后建议重建并提交 |
| 临时文件 | 不含 `Untitled`、`workspace/` 运行实例 |
| force push | 禁止（`main` 与 `gameforge-k12` 均禁止） |

```powershell
git status
git diff --stat
git log -3 --oneline
git branch --show-current   # 应输出 gameforge-k12
```

---

## 6. 阶段子分支

```powershell
git checkout gameforge-k12
git pull origin gameforge-k12
git checkout -b gameforge-k12/w1-platformer
git push -u origin gameforge-k12/w1-platformer
```

合回专用主线：

```powershell
git checkout gameforge-k12
git merge gameforge-k12/w1-platformer
git push origin gameforge-k12
```

---

## 7. 冲突与异常

**推送被拒（fetch first）**

```powershell
git pull origin gameforge-k12
git push origin gameforge-k12
```

**误在 main 暂存本项目文件**

```powershell
Set-Location "e:\文三路AI馆\1未来隧道部分"
git checkout main
git restore --staged . ; git restore .
```

在 `2.ai生成游戏` 目录重新提交。

**合并冲突**

编辑冲突文件 → 删除 `<<<<<<<` / `=======` / `>>>>>>>` → `git add .` → `git commit` → `git push origin gameforge-k12`

**RAG 索引过期**

文档更新后重建再提交：

```powershell
cd "e:\文三路AI馆\2.ai生成游戏\05-工具脚本"
E:\文三路AI馆\1未来隧道部分\研究资料\AI出行体验舱_技术调研\crawler\.venv\Scripts\python.exe build_rag_index.py
```

---

## 8. 禁止操作

| 操作 | 原因 |
|------|------|
| 在 `main` 提交本项目 | 与未来隧道混库 |
| `git merge main` | 引入无关历史 |
| PR 合并至 `main` | 混库 |
| `git push --force origin main` | 覆盖远程 main |
| `git push -f origin gameforge-k12` | 覆盖专用分支历史 |
| 提交 `.env`、密钥、`checkpoint.json` | 安全 / 体积 |
| 提交 `workspace/` 会话实例 | 临时运行数据 |

---

## 9. .gitignore

项目根目录 `.gitignore`（已创建）要点：

```gitignore
.env / credentials / *.pem
checkpoint.json          # 爬虫续跑检查点，体积大
workspace/ exports/      # 会话与导出产物
.godot/ *.import         # Godot 缓存
node_modules/ __pycache__/
```

---

## 10. 提交信息

格式：`<类型>: <目的>`

| 类型 | 示例 |
|------|------|
| `docs` | `docs: 技术选型 v1.1 与审核报告入库` |
| `feat` | `feat: platformer 模板 core 预制` |
| `chore` | `chore: 重建 RAG 索引（905 chunks）` |
| `fix` | `fix: 修正 game_config schema 字段名` |

---

## 11. 入库路径

| 路径 | 内容 |
|------|------|
| `文档目录说明.md` | 项目索引 |
| `未来教育_ai生成游戏_推送指南.md` | 本指南 |
| `开发文档/README.md` | 开发文档索引 |
| `开发文档/` | 技术选型、功能点、评审、架构、模板引擎 |
| `03-背景与调研/` | 调研整合、RAG、爬虫报告（不含 checkpoint） |
| `05-工具脚本/` | 爬虫、整合、RAG 构建与查询 |
| `templates/` | Godot 品类模板与 config 示例 |
| `6.3功能点与效果示意图/` | 效果示意图 |
| `.cursor/` | mcp.json、Rules（core_locked） |

**不入库**：`workspace/`、`exports/`、Godot 导出 `.exe`、爬虫 `checkpoint.json`

---

## 12. Agent 提示词

```text
目录：e:\文三路AI馆\2.ai生成游戏
远程：http://10.70.160.61:3002/3240103625/zwm.git
分支：gameforge-k12（禁止 main）

按 未来教育_ai生成游戏_推送指南.md §4 推送；回报 commit hash 与 Gitea 分支链接。
生成任务前先 query_rag.py；禁止修改 templates/*/core/。
```

---

## 13. GitHub 公开仓库（v1.0 起）

| 项 | 值 |
|----|-----|
| 仓库 | https://github.com/DomenRaven/Wensan-Road-Ai-city-Game |
| 远程名 | `github`（与场内 `origin` 并存，互不影响） |
| 默认推送分支 | `gameforge-k12` → GitHub `main` |
| 版本标签 | `v1.0`（回退锚点） |

**首次添加 GitHub 远程并推送：**

```powershell
Set-Location "e:\文三路AI馆\2.ai生成游戏"
git remote add github https://github.com/DomenRaven/Wensan-Road-Ai-city-Game.git
git push -u github gameforge-k12:main
git push github v1.0
```

**日常同步 GitHub（在场内 origin 推送之外）：**

```powershell
git checkout gameforge-k12
git push origin gameforge-k12          # 场内 Gitea
git push github gameforge-k12:main     # GitHub
```

**回退到 v1.0：**

```powershell
git fetch github --tags
git checkout v1.0                      # 只读查看
# 或在工作分支上：
git branch backup-$(Get-Date -Format yyyyMMdd)
git reset --hard v1.0
```

发新版时：更新 `VERSION`、`CHANGELOG.md`，提交后 `git tag -a v1.1 -m "..."` 并 `git push github v1.1`。

---

## 14. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.1 | 2026-06-24 | 增加 GitHub 远程、VERSION/CHANGELOG、v1.0 标签与回退说明 |
| v1.0 | 2026-06-13 | 初版；独立 orphan 分支 `gameforge-k12`；对齐前厅机械屏推送指南体例 |
