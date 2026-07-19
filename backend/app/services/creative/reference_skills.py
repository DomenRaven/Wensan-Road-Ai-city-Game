"""策展 Reference Skills：只读注入 Agent（与 learned_skills 分离）。"""

from __future__ import annotations

import json
from pathlib import Path


def ensure_reference_dir(store_dir: Path) -> Path:
    root: Path = store_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_text(path: Path, limit: int = 6000) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def format_reference_summary_for_prompt(store_dir: Path, genre: str) -> str:
    """启动时只注入索引；详细正文由 read_reference_skill 按需读取。"""
    root: Path = ensure_reference_dir(store_dir)
    genre_path: Path = root / genre / "SKILL.md"
    common_path: Path = root / "_common" / "agent_loop.md"
    available: list[str] = []
    if genre_path.is_file():
        available.append(f"genre:{genre}")
    if common_path.is_file():
        available.extend(["agent_loop", "gdscript"])
    if not available:
        return ""
    return (
        "【Reference Skills 索引】可用："
        + "、".join(available)
        + "；需要时调用 read_reference_skill。施工仍以会话磁盘为准。"
    )


def read_reference_skill(
    store_dir: Path,
    genre: str,
    *,
    which: str = "genre",
) -> dict[str, str | bool]:
    """供工具 read_reference_skill：which=genre|common|agent_loop|gdscript|sources。"""
    root: Path = ensure_reference_dir(store_dir)
    key: str = (which or "genre").strip().lower()
    mapping: dict[str, Path] = {
        "genre": root / genre / "SKILL.md",
        "common": root / "_common" / "godot4_gdscript.md",
        "gdscript": root / "_common" / "godot4_gdscript.md",
        "agent_loop": root / "_common" / "agent_loop.md",
        "sources": root / "SOURCES.md",
        "readme": root / "README.md",
    }
    path: Path = mapping.get(key, mapping["genre"])
    text: str = _read_text(path, 8000)
    return {
        "ok": bool(text),
        "which": key,
        "path": path.as_posix() if path else "",
        "content": text or f"（未找到 reference：{key}）",
    }


def list_reference_index(store_dir: Path) -> dict[str, object]:
    root: Path = ensure_reference_dir(store_dir)
    index_path: Path = root / "index.json"
    if not index_path.is_file():
        return {"ok": False, "genres": []}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "genres": []}
    if isinstance(data, dict):
        return {"ok": True, **data}
    return {"ok": False, "genres": []}
