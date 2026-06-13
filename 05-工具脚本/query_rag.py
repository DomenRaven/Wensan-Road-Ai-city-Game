# -*- coding: utf-8 -*-
"""查询本地 RAG 知识库。"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "03-背景与调研" / "rag" / "index" / "gameforge_rag.db"


def search(query: str, top_k: int = 8, source_type: str | None = None) -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"索引不存在，请先运行 build_rag_index.py · {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # FTS5 查询：空格转 OR，中文整句加引号
    fts_q = query.replace('"', "")
    if " " in fts_q:
        terms = [t for t in fts_q.split() if t]
        match = " OR ".join(f'"{t}"' if len(t) > 2 else t for t in terms)
    else:
        match = f'"{fts_q}"'

    sql = """
        SELECT d.source_type, d.source_name, d.title, d.url, d.topic, d.score, d.content,
               bm25(documents_fts) AS rank
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
    """
    params: list = [match]
    if source_type:
        sql += " AND d.source_type = ?"
        params.append(source_type)
    sql += " ORDER BY rank LIMIT ?"
    params.append(top_k)

    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        # 降级：LIKE
        like = f"%{query}%"
        sql2 = """
            SELECT source_type, source_name, title, url, topic, score, content, 0 AS rank
            FROM documents
            WHERE content LIKE ? OR title LIKE ?
        """
        params2 = [like, like]
        if source_type:
            sql2 += " AND source_type = ?"
            params2.append(source_type)
        sql2 += " ORDER BY score DESC LIMIT ?"
        params2.append(top_k)
        rows = [dict(r) for r in conn.execute(sql2, params2).fetchall()]
    conn.close()
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="GameForge K12 本地 RAG 检索")
    p.add_argument("query", help="检索问题")
    p.add_argument("-k", "--top", type=int, default=8)
    p.add_argument("--source", choices=["crawl", "dev", "survey"], default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    results = search(args.query, top_k=args.top, source_type=args.source)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"查询: {args.query} · 命中 {len(results)} 条\n")
    for i, r in enumerate(results, 1):
        print(f"--- [{i}] {r['source_type']}/{r['source_name']} · score={r['score']:.0f} ---")
        print(r["title"])
        if r.get("url"):
            print(r["url"])
        if r.get("topic"):
            print(f"主题: {r['topic']}")
        preview = (r["content"] or "")[:400].replace("\n", " ")
        print(preview)
        print()


if __name__ == "__main__":
    main()
