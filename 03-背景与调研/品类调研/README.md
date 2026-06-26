# 品类调研资料库 · TPL v1.2

> **用途**：为 D3–D5 Godot 模板开发提供各品类的**设计规范、核心规则、参数区间与实现路径**  
> **对齐**：[`config/genre_registry.json`](../../config/genre_registry.json) · [`开发文档/模板引擎/品类核心参数规格_v1.0.md`](../../开发文档/模板引擎/品类核心参数规格_v1.0.md)  
> **更新**：2026-06-19 · 来源含 GDC、GameDev.net、知乎、机核、Shmups Wiki、RAG 1348+ chunks

---

## 目录结构

每个品类文件夹包含：

| 文件 | 内容 |
|------|------|
| `设计规范与实现路径.md` | 核心规则 · 参数规格 · Godot 实现 · K12 约束 |
| `参考来源.md` | 网页/社区/论文链接与摘要 |

```
品类调研/
├── README.md              ← 本索引
├── shooter/               TPL-01 射击（FPS/TPS）
├── fighting/              TPL-02 横版格斗
├── survivor/              TPL-03 割草肉鸽
├── tower_defense/         TPL-04 塔防
├── parkour/               TPL-05 跑酷
├── platformer/            TPL-06 横版闯关
├── life_sim/              TPL-07 生活模拟
├── sports_race/           TPL-08 体育竞速
├── pingpong/              TPL-09 乒乓球
├── racing/                TPL-10 赛车
└── shmup/                 TPL-11 雷霆战机
```

---

## 十一品类速查

| slug | 品类 | D10 档 | 操作键 | 单局时长 |
|------|------|--------|--------|----------|
| `shooter` | 射击 | L0+L1 | ≤3 | 2–3min |
| `fighting` | 横版格斗 | L0 | ≤3 | 1–2min/局 |
| `survivor` | 割草肉鸽 | L0+L1 | ≤2 | 3min |
| `tower_defense` | 塔防 | L0+L1 | ≤3 | 5min |
| `platformer` | 横版闯关 | L0+L1 | ≤3 | 2–4min |
| `parkour` | 跑酷 | L0 | ≤2 | 1–3min |
| `life_sim` | 生活模拟 | L0 | ≤2 | 2min |
| `sports_race` | 体育竞速 | L0 | ≤2 | 60–90s |
| `pingpong` | 乒乓球 | L0 | ≤2 | 2min |
| `racing` | 赛车 | L0 | ≤3 | 2min |
| `shmup` | 雷霆战机 | L0+L1 | ≤3 | 2–3min |

---

## 使用方式

1. **模板开发前**：阅读对应 slug 的 `设计规范与实现路径.md`
2. **Agent 生成前**：`python 05-工具脚本/query_rag.py "{品类+主题}" -k 5`
3. **参数填写**：tuning 须在规格文档 ±30% 范围内
4. **验收**：MCP `run_project` 无 ERROR + K12 内容安全

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-06-19 | 初建 11 品类调研文件夹与规范文档 |
