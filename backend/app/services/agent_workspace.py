"""会话工作区智能体写权限：可改「本局副本」，严禁碰 templates。

与旧 ai_sandbox 红线的关系：
- 默认/降级路径仍只写 core/ai_sandbox/**
- 智能体路径可改会话内 core/**、config/game_config.json、scenes/**
- 回主页 / release 仍整棵销毁 workspace
"""

from __future__ import annotations

import re
from pathlib import Path

from app.services.workspace_guard import (
    assert_not_under_templates,
    assert_under_workspace,
)

# 危险 GDScript 片段（K12 / 展厅安全）
FORBIDDEN_GD_SNIPPETS: tuple[str, ...] = (
    "OS.execute",
    "OS.create_process",
    "OS.shell_open",
    "JavaScriptBridge",
    "ClassDB.instance",
    "DirAccess.remove",
    "IP.resolve_hostname",
    "HTTPRequest",
    "PacketPeer",
    "TCPServer",
    "UDPServer",
    "WebSocket",
)

_ALLOWED_SUFFIXES: frozenset[str] = frozenset(
    {".gd", ".tscn", ".json", ".svg", ".png", ".md", ".txt", ".tres", ".import"}
)

# 禁止智能体改动的相对路径前缀/文件（会话内）
_BLOCKED_EXACT: frozenset[str] = frozenset(
    {
        "project.godot",  # autoload 由 edu 注入，避免打坏启动
        ".env",
        "export_presets.cfg",
    }
)
_BLOCKED_PREFIXES: tuple[str, ...] = (
    ".git/",
    "addons/",
    ".godot/",
)


class AgentWorkspaceError(ValueError):
    """智能体读写被拒绝。"""


def normalize_rel(rel_posix: str) -> str:
    rel = rel_posix.strip().replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if (
        not rel
        or "\x00" in rel
        or ".." in parts
        or "" in parts
    ):
        raise AgentWorkspaceError(f"非法路径: {rel_posix!r}")
    return rel


def assert_agent_path(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    *,
    for_write: bool,
) -> Path:
    """校验相对路径落在会话 workspace，且不在 templates。"""
    rel = normalize_rel(rel_posix)
    if rel in _BLOCKED_EXACT or any(rel.startswith(p) for p in _BLOCKED_PREFIXES):
        raise AgentWorkspaceError(f"禁止访问: {rel}")

    if for_write:
        suffix = Path(rel).suffix.lower()
        if suffix and suffix not in _ALLOWED_SUFFIXES:
            raise AgentWorkspaceError(f"禁止写入此类型: {rel}")
        # 写范围：core/**、config/**、scenes/**、assets 下新建说明类
        if not (
            rel.startswith("core/")
            or rel.startswith("config/")
            or rel.startswith("scenes/")
            or rel.startswith("assets/")
        ):
            raise AgentWorkspaceError(
                f"智能体只能写会话 core/config/scenes/assets，拒绝: {rel}"
            )

    root = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())
    assert_not_under_templates(root, templates_dir.resolve())
    target = (root / rel).resolve()
    assert_under_workspace(target, workspace_dir.resolve())
    assert_not_under_templates(target, templates_dir.resolve())
    return target


def validate_gdscript_safe(content: str) -> None:
    for snip in FORBIDDEN_GD_SNIPPETS:
        if snip in content:
            raise AgentWorkspaceError(f"脚本含禁止 API: {snip}")


def list_workspace_tree(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_dir: str = "",
    max_entries: int = 80,
) -> list[str]:
    """列出目录（相对路径），供 LLM 观察项目结构。"""
    rel = normalize_rel(rel_dir) if rel_dir.strip() else ""
    if rel:
        base = assert_agent_path(
            workspace_root, workspace_dir, templates_dir, rel, for_write=False
        )
        if not base.is_dir():
            raise AgentWorkspaceError(f"不是目录: {rel}")
    else:
        base = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())

    out: list[str] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        try:
            rp = p.resolve().relative_to(workspace_root.resolve()).as_posix()
        except ValueError:
            continue
        if any(rp.startswith(b) for b in _BLOCKED_PREFIXES):
            continue
        if rp in _BLOCKED_EXACT:
            continue
        out.append(rp)
        if len(out) >= max_entries:
            break
    return out


def read_workspace_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    max_chars: int = 12000,
) -> str:
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel_posix, for_write=False
    )
    if not target.is_file():
        raise AgentWorkspaceError(f"文件不存在: {rel_posix}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n…(截断，共 {len(text)} 字符)"
    return text


def write_workspace_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    content: str,
) -> str:
    """写入会话文件；返回相对路径。绝不写 templates。"""
    rel = normalize_rel(rel_posix)
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel, for_write=True
    )
    if rel.endswith(".gd"):
        validate_gdscript_safe(content)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return rel
