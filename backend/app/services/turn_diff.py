"""F2 · 回合前后工作区 Diff（不另调 LLM）。"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ChangeType = Literal["added", "modified", "deleted"]

_DIFF_PREFIXES: tuple[str, ...] = ("config/", "core/", "scenes/", "ai_sandbox/")
_TEXT_SUFFIXES: tuple[str, ...] = (
    ".gd",
    ".tscn",
    ".json",
    ".md",
    ".txt",
    ".cfg",
    ".tres",
    ".godot",
)
_MAX_FILE_BYTES = 512 * 1024
_MAX_DIFF_CHARS = 120_000


@dataclass(frozen=True)
class FileDiff:
    path: str
    change_type: ChangeType
    diff_text: str
    after_text: str
    note: str


def _is_text_rel(rel: str) -> bool:
    lower = rel.lower()
    return any(lower.endswith(suf) for suf in _TEXT_SUFFIXES)


def _iter_text_files(workspace_root: Path) -> list[Path]:
    root = workspace_root.resolve()
    out: list[Path] = []
    for prefix in _DIFF_PREFIXES:
        base = root / prefix.rstrip("/")
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if ".." in rel.split("/"):
                continue
            if not _is_text_rel(rel):
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            out.append(path)
    return out


def snapshot_workspace_texts(workspace_root: Path) -> dict[str, str]:
    """回合开始前/结束后：可读文本树快照 path → utf-8 内容。"""
    root = workspace_root.resolve()
    snap: dict[str, str] = {}
    for path in _iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            snap[rel] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return snap


def _file_note(path: str, change_type: ChangeType) -> str:
    name = path.rsplit("/", 1)[-1]
    if change_type == "added":
        return f"本轮新增了 `{name}`，请重点看绿色「+」行。"
    if change_type == "deleted":
        return f"本轮删除了 `{name}`（红色「−」为原内容）。"
    if path.startswith("config/"):
        return f"本轮调整了配置 `{name}`，对照绿/红行看参数变化。"
    if path.startswith("scenes/"):
        return f"本轮改了场景 `{name}`，对照绿/红行看节点或属性变化。"
    return f"本轮修改了 `{name}`，绿色为新增/改后，红色删除为斜体对照。"


def _unified(path: str, before: str, after: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    text = "\n".join(diff_iter)
    if len(text) > _MAX_DIFF_CHARS:
        return text[:_MAX_DIFF_CHARS] + "\n…（Diff 过长已截断）"
    return text


def compute_turn_diff(
    before: dict[str, str],
    after: dict[str, str],
    *,
    rolled_back: bool = False,
    overview_note: str = "",
) -> dict[str, Any]:
    """对照 before/after，产出可持久化的 Diff 结构。"""
    files: list[dict[str, Any]] = []
    all_paths = sorted(set(before) | set(after))
    for path in all_paths:
        old = before.get(path)
        new = after.get(path)
        if old is None and new is not None:
            ctype: ChangeType = "added"
            diff_text = _unified(path, "", new)
            after_text = new
        elif old is not None and new is None:
            ctype = "deleted"
            diff_text = _unified(path, old, "")
            after_text = ""
        elif old != new:
            ctype = "modified"
            assert old is not None and new is not None
            diff_text = _unified(path, old, new)
            after_text = new
        else:
            continue
        if not diff_text.strip() and ctype == "modified":
            continue
        files.append(
            {
                "path": path,
                "change_type": ctype,
                "diff_text": diff_text,
                "after_text": after_text[:_MAX_DIFF_CHARS],
                "note": _file_note(path, ctype),
            }
        )

    overview = (overview_note or "").strip()
    if len(overview) > 800:
        overview = overview[:800] + "…"
    if not overview:
        if rolled_back:
            overview = "本轮改动未通过验收并已回滚；下列为回滚后相对开局前的对照（可能无净变更）。"
        elif not files:
            overview = "本轮工作区文本文件无净变更。"
        else:
            overview = f"本轮共变更 {len(files)} 个文件。请对照绿色新增与红色删除行。"

    return {
        "rolled_back": bool(rolled_back),
        "file_count": len(files),
        "overview_note": overview,
        "files": files,
    }
