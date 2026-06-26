# -*- coding: utf-8 -*-
"""构建本地 RAG 索引（SQLite FTS5），供 Cursor / 脚本检索。"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = ROOT / "03-背景与调研" / "rag"
DB_PATH = RAG_DIR / "index" / "gameforge_rag.db"
DATA_DIR = ROOT / "03-背景与调研" / "data" / "游戏设计与AI创作调研"
INTEGRATED = ROOT / "03-背景与调研" / "游戏设计与AI创作-调研整合.md"
USER_SURVEY = ROOT / "03-背景与调研" / "K12用户向调研整合.md"
USER_DATA_DIR = ROOT / "03-背景与调研" / "data" / "K12用户向调研"
GENRE_RESEARCH = ROOT / "03-背景与调研" / "品类调研"
DOCS = ROOT / "开发文档"

NOISE_PATTERNS = [
    "china-dictatorship", "dictatroship", "dictattorshrip", "gege-circle",
    "OpenPacketFix", "PCL2", "torrent", "wenku.csdn.net/doc",
    "ops_request_misc", "[检索异常]", "[b站检索失败]",
]

DOC_SOURCES = [
    ("dev", "十天上线路线", DOCS / "AI生成小游戏_十天上线路线_v1.2.md"),
    ("dev", "前期准备待办", DOCS / "AI生成小游戏_前期准备与待办_v1.2.md"),
    ("dev", "项目自检对齐", DOCS / "AI生成小游戏_项目自检对齐报告_v1.0.md"),
    ("dev", "会话交接手册", DOCS / "AI生成小游戏_会话交接手册_v1.0.md"),
    ("dev", "历史工作足迹", DOCS / "AI生成小游戏_历史工作足迹_v1.0.md"),
    ("dev", "Godot可行性评估", DOCS / "AI生成小游戏_Godot联调与可行性评估_v1.0.md"),
    ("dev", "AI创作引导流程", DOCS / "模板引擎" / "AI创作引导流程_v1.0.md"),
    ("dev", "技术选型", DOCS / "AI生成小游戏_技术选型与开发计划_v1.0.md"),
    ("dev", "功能点明细", DOCS / "AI生成小游戏_功能点明细与开发计划_v1.0.md"),
    ("dev", "开发执行规范", DOCS / "AI生成小游戏_开发执行规范_v1.0.md"),
    ("dev", "自动化执行控制", DOCS / "AI生成小游戏_自动化执行控制文档_v1.0.md"),
    ("dev", "项目使用说明", DOCS / "AI生成小游戏_项目使用说明手册_v1.0.md"),
    ("dev", "技术方案独立评审", DOCS / "AI生成小游戏_技术方案独立评审_v1.0.md"),
    ("dev", "任务总结审核报告", DOCS / "AI生成小游戏_任务总结审核报告_v1.0.md"),
    ("dev", "品类参数", DOCS / "模板引擎" / "品类核心参数规格_v1.0.md"),
    ("dev", "架构", DOCS / "架构" / "系统架构说明_v1.0.md"),
    ("dev", "业务流程", DOCS / "架构" / "系统业务流程说明_v1.0.md"),
    ("survey", "调研整合", INTEGRATED),
    ("survey", "用户向调研", USER_SURVEY),
]

# 品类调研：每个 slug 下的 markdown
for genre_md in sorted(GENRE_RESEARCH.glob("*/*.md")):
    slug = genre_md.parent.name
    label = f"品类调研-{slug}"
    DOC_SOURCES.append(("genre", label, genre_md))


def _is_noise(title: str, url: str) -> bool:
    blob = f"{title} {url}".lower()
    return any(n in blob for n in NOISE_PATTERNS)


def _chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _latest_report(data_dir: Path) -> Path:
    reports = sorted(data_dir.glob("report_*.json"), reverse=True)
    if not reports:
        raise FileNotFoundError(f"未找到 crawler 报告: {data_dir}")
    return reports[0]


def _ingest_crawl_report(
    report_path: Path, rows: list[tuple], now: str, id_prefix: str
) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    web_count = 0
    for item in report.get("items", []):
        title = item.get("title", "")
        url = item.get("url", "")
        if _is_noise(title, url):
            continue
        score = item.get("scores", {}).get("total", 0)
        if score < 22:
            continue
        topic = item.get("topic_name", "")
        body = "\n".join(
            filter(
                None,
                [
                    item.get("summary", ""),
                    item.get("content_preview", ""),
                    f"分类: {item.get('category', '')}",
                    f"检索词: {item.get('query', '')}",
                    f"来源: {item.get('source', '')}",
                ],
            )
        )
        for i, chunk in enumerate(_chunk_text(body, 900)):
            rows.append(
                (
                    "crawl",
                    f"{id_prefix}_{web_count}",
                    f"{title} [{i+1}]" if i else title[:200],
                    url,
                    topic,
                    float(score),
                    chunk,
                    now,
                )
            )
        web_count += 1
    return web_count


def build_index() -> dict:
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    (RAG_DIR / "index").mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            source_type TEXT,
            source_name TEXT,
            title TEXT,
            url TEXT,
            topic TEXT,
            score REAL,
            content TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE documents_fts USING fts5(
            title, content, topic, source_name,
            content='documents', content_rowid='id'
        )
        """
    )

    rows: list[tuple] = []
    now = datetime.now().isoformat(timespec="seconds")

    # 1) crawler 条目（技术向 + 用户向）
    web_count = _ingest_crawl_report(_latest_report(DATA_DIR), rows, now, "web")
    user_crawl = 0
    user_reports = sorted(USER_DATA_DIR.glob("report_*.json"), reverse=True)
    if user_reports:
        user_crawl = _ingest_crawl_report(user_reports[0], rows, now, "user")
    web_count += user_crawl

    # 2) 项目文档
    for src_type, name, path in DOC_SOURCES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunk_text(text, 1500)):
            rows.append(
                (src_type, name, f"{name} §{i+1}", "", name, 100.0, chunk, now)
            )

    conn.executemany(
        "INSERT INTO documents (source_type, source_name, title, url, topic, score, content, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.execute("INSERT INTO documents_fts(rowid, title, content, topic, source_name) "
                 "SELECT id, title, content, topic, source_name FROM documents")
    conn.commit()

    stats = {
        "built_at": now,
        "db_path": str(DB_PATH),
        "total_chunks": len(rows),
        "crawl_items": web_count,
        "report": _latest_report(DATA_DIR).name,
        "user_report": user_reports[0].name if user_reports else None,
        "user_crawl_items": user_crawl,
    }
    (RAG_DIR / "index" / "manifest.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    conn.close()
    return stats


def main() -> None:
    stats = build_index()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
