# -*- coding: utf-8 -*-
"""将 research_crawler 报告整合为《游戏设计与AI创作-调研整合.md》。"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "03-背景与调研" / "data" / "游戏设计与AI创作调研"
OUT_MD = ROOT / "03-背景与调研" / "游戏设计与AI创作-调研整合.md"

TOPIC_ORDER = [
    "AI辅助游戏创作与智能体",
    "Godot游戏设计与GDScript",
    "游戏手感与核心机制设计",
    "模板化与参数化游戏生成",
    "K12教育游戏与展陈",
    "分品类设计参考",
    "学术与行业理论",
]

PROJECT_TAKEAWAYS = {
    "AI辅助游戏创作与智能体": [
        "LLM Agent 适合承担「改配置/写脚本补丁」而非从零设计核心手感",
        "godot-mcp / GamingAgent 类工具证明：运行-读日志-修复闭环是 AI 做游戏的关键",
        "展陈场景应限制 Agent scope：模板 + tuning + theme，与品类核心参数规格一致",
    ],
    "Godot游戏设计与GDScript": [
        "Godot 4 2D 俯视角射击、塔防、平台跳跃均有成熟开源教程与 template",
        "GDScript 强类型 + 全文本项目最适合 Cursor 批量编辑",
        "官方与 GDQuest 教程可作为 core 层预制参考实现",
    ],
    "游戏手感与核心机制设计": [
        "Game Feel / Juice 理论支持：射击反馈、平台 coyote time、塔防数值公式应写入 core",
        "MDA 框架：Mechanics 预制锁定，Dynamics 靠 tuning 微调，Aesthetics 靠 theme",
        "10 分钟交付依赖「手感预制好」，而非现场调参",
    ],
    "模板化与参数化游戏生成": [
        "Data-driven design（JSON/Resource 驱动）是快速个性化的行业共识",
        "Game Jam 10 分钟原型实践：预制场景 + 换数值 + 换皮",
        "与本项目 `config/game_config.json` 三层模型完全同构",
    ],
    "K12教育游戏与展陈": [
        "教育游戏/Serious Games 强调低暴力、短时长、可带走成果",
        "研学场景需要讲解员复位、双工位队列、成果上墙",
        "与文三路馆「AI 教育区 K12」定位一致：创造感 > 竞技感",
    ],
    "分品类设计参考": [
        "射击：顶视角移动 + 波次；塔防：路径 + 经济 + 波次表",
        "闯关：移速/跳跃/关卡块；休闲：单核心循环 + 计分",
        "直接映射到 TPL-01~07 模板 core 预制清单",
    ],
    "学术与行业理论": [
        "PCG（程序化内容生成）综述支持参数化关卡而非生成新引擎",
        "LLM 代码生成论文指出：闭环执行与类型约束降低失败率",
        "期刊材料用于方案汇报背书，落地仍以 Godot 模板为准",
    ],
}


def _latest_report() -> Path:
    reports = sorted(DATA_DIR.glob("report_*.json"), reverse=True)
    if not reports:
        raise FileNotFoundError(f"未找到报告，请先运行 run_game_research_crawler.py · {DATA_DIR}")
    return reports[0]


def _clean_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title or "").strip()
    return t[:120] + ("…" if len(t) > 120 else "")


def _item_field(item: dict, key: str, default: str = "") -> str:
    if key in item:
        return item.get(key) or default
    return (item.get("result") or {}).get(key) or default


def _is_noise(item: dict) -> bool:
    title = _item_field(item, "title").lower()
    url = _item_field(item, "url").lower()
    noise = ["torrent", "ops_request_misc", "wenku.csdn.net/doc", "[检索异常]", "[b站检索失败]"]
    return any(n in title or n in url for n in noise)


def build_report() -> str:
    report_path = _latest_report()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    items = [i for i in data.get("items", []) if not _is_noise(i)]
    meta = data.get("meta", {})

    by_topic: dict[str, list] = defaultdict(list)
    for it in items:
        topic = it.get("topic_name") or "其他"
        by_topic[topic].append(it)

    for topic in by_topic:
        by_topic[topic].sort(key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)

    lines: list[str] = []
    lines.append("# 游戏设计与 AI 创作 · 调研整合报告")
    lines.append("")
    lines.append("> **文档类型**：全网检索归纳 · 服务 AI 小游戏创作工坊")
    lines.append("> **版本**：Survey-01")
    lines.append(f"> **日期**：{datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"> **检索报告**：`data/游戏设计与AI创作调研/{report_path.name}`")
    lines.append("> **检索方式**：`research_crawler` + `game_crawler_patch` · 虚拟环境 `py310_torch251_cu121`")
    lines.append("> **数据源**：web · bilibili · csdn · github · zhihu · juejin")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、调研摘要（给方案与模板预制用）")
    lines.append("")
    lines.append(
        "本次检索覆盖 **AI 辅助游戏创作、Godot 2D 实践、游戏手感理论、参数化模板、"
        "K12 教育游戏展陈、分品类机制设计、学术综述** 七条主线。"
        f"有效条目 **{len(items)}** 条（已过滤噪声）。"
    )
    lines.append("")
    lines.append("**对本项目的直接结论：**")
    lines.append("")
    lines.append("1. **你的「core 预制 + tuning 小改」思路与行业最佳实践一致**——Data-driven / Game Jam 模板路线是 10 分钟交付的唯一可行解。")
    lines.append("2. **Godot + Cursor + MCP** 已有大量社区案例（俯视角射击教程、塔防 case study、godot-mcp）。")
    lines.append("3. **AI 做游戏的价值在闭环**——GamingAgent 等研究证明：能运行、能读报错、能迭代才有意义。")
    lines.append("4. **K12 展陈**需低暴力、短循环、可视化创作过程，与教育游戏/Serious Games 文献方向一致。")
    lines.append("5. **分品类**应分别预制：射击（移动+命中）、塔防（数值公式+波次）、闯关（跳跃手感）。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、分主题要点与项目映射")
    lines.append("")

    for topic in TOPIC_ORDER:
        bucket = by_topic.get(topic, [])[:12]
        if not bucket:
            continue
        lines.append(f"### 2.{TOPIC_ORDER.index(topic)+1} {topic}")
        lines.append("")
        takeaways = PROJECT_TAKEAWAYS.get(topic, [])
        for t in takeaways:
            lines.append(f"- {t}")
        lines.append("")
        lines.append("| # | 分数 | 来源 | 标题 | 链接 |")
        lines.append("|---|------|------|------|------|")
        for idx, it in enumerate(bucket[:8], 1):
            score = it.get("scores", {}).get("total", 0)
            title = _clean_title(_item_field(it, "title")).replace("|", "/")
            url = _item_field(it, "url")
            src = _item_field(it, "source")
            lines.append(f"| {idx} | {score:.0f} | {src} | {title} | {url} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 三、高价值资源精选（跨主题 Top 15）")
    lines.append("")
    top = sorted(items, key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)[:15]
    for idx, it in enumerate(top, 1):
        score = it.get("scores", {}).get("total", 0)
        topic = it.get("topic_name", "")
        lines.append(f"### {idx}. {_clean_title(_item_field(it, 'title'))}")
        lines.append("")
        lines.append(f"- **综合分**：{score:.1f} · **来源**：{_item_field(it, 'source')} · **主题**：{topic}")
        lines.append(f"- **链接**：{_item_field(it, 'url')}")
        snip = (it.get("summary") or _item_field(it, "snippet") or "")[:280].replace("\n", " ")
        if snip:
            lines.append(f"- **摘要**：{snip}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 四、对模板预制的行动清单")
    lines.append("")
    lines.append("| 品类 | core 层应预制的理论依据 | 推荐参考类型 |")
    lines.append("|------|-------------------------|--------------|")
    rows = [
        ("射击 TPL-01", "八向移动平滑 + AABB 命中 + 波次", "Godot Top-down Shooter 教程 / GDQuest"),
        ("塔防 TPL-02", "网格放置 + 伤害公式 + 波次调度", "tower-defense-case-study 多引擎对照"),
        ("闯关 TPL-04", "coyote time + 可变高度跳 + 摩擦", "Game Feel / Godot platformer 教程"),
        ("竞速 TPL-03", "自动跑 + 跳跃缓冲 + 距离刷障碍", "跑酷核心循环文献"),
        ("休闲 TPL-07", "单轴操作 + 计分公式", "Arcade 设计模式"),
        ("AI 编排", "运行-日志-修复闭环", "godot-mcp · GamingAgent · Cursor Agent"),
    ]
    for a, b, c in rows:
        lines.append(f"| {a} | {b} | {c} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 五、检索元数据")
    lines.append("")
    lines.append(f"| 项 | 值 |")
    lines.append(f"|----|-----|")
    lines.append(f"| 报告文件 | `{report_path.name}` |")
    lines.append(f"| 生成时间 | {meta.get('generated_at', '')} |")
    lines.append(f"| 主题 | {meta.get('topic_summary', '')} |")
    lines.append(f"| 数据源 | {', '.join(meta.get('sources', []))} |")
    lines.append(f"| 有效条目 | {len(items)} |")
    lines.append(f"| 是否跑完 | {'是' if meta.get('all_tasks_done') else '否（可续跑）'} |")
    lines.append("")
    lines.append("### 续跑命令")
    lines.append("")
    lines.append("```powershell")
    lines.append('cd "E:\\文三路AI馆\\2.ai生成游戏\\05-工具脚本"')
    lines.append("C:\\Users\\MAC\\.conda\\envs\\py310_torch251_cu121\\python.exe run_game_research_crawler.py")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*游戏设计与 AI 创作 · 调研整合 Survey-01*")

    return "\n".join(lines)


def main() -> None:
    text = build_report()
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"已写入: {OUT_MD}")
    print(f"字数约: {len(text)}")


if __name__ == "__main__":
    main()
