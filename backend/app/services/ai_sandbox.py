"""AI 沙箱：只允许在 workspace/core/ai_sandbox/ 新建或覆写会话文件。

红线：
- 禁止写入 templates/**
- 禁止改写 templates/{genre} 已有相对路径对应的 workspace 源拷贝
  （即不得覆盖从模板复制来的 core/*.gd 等）
- 仅允许 core/ai_sandbox/** 下的新建文件（会话内可反复覆写沙箱文件）
- 回主页 / release → remove_workspace 整棵销毁，无需额外清理 API
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.services.workspace_guard import (
    WorkspaceGuardError,
    assert_not_under_templates,
    assert_under_workspace,
)

AI_SANDBOX_REL: str = "core/ai_sandbox"
AI_SANDBOX_BRIDGE_FILENAME: str = "ai_sandbox_bridge.gd"
OVERRIDES_FILENAME: str = "overrides.json"
MANIFEST_FILENAME: str = "manifest.json"

_SAFE_GD_NAME = re.compile(r"^[a-z][a-z0-9_]{0,40}\.gd$")
_SAFE_GD_REL = re.compile(
    r"^(?:[a-z][a-z0-9_]{0,24}/){0,3}[a-z][a-z0-9_]{0,40}\.gd$"
)
_SAFE_ICON_REL = re.compile(r"^icons/[a-z][a-z0-9_]{0,40}\.(svg|png)$")
_FORBIDDEN_GD_SNIPPETS: tuple[str, ...] = (
    "OS.execute",
    "OS.create_process",
    "OS.shell_open",
    "JavaScriptBridge",
    "ClassDB.instance",
    "load(\"user://",
    "FileAccess.open(\"res://core/",
    "FileAccess.open('res://core/",
    "DirAccess.remove",
    "DirAccess.make_dir",
)


class AiSandboxError(ValueError):
    """沙箱写入被拒绝。"""


def sandbox_dir(workspace_root: Path) -> Path:
    return workspace_root / AI_SANDBOX_REL


def ensure_sandbox_dir(workspace_root: Path, workspace_dir: Path, templates_dir: Path) -> Path:
    root = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())
    assert_not_under_templates(root, templates_dir.resolve())
    target = root / AI_SANDBOX_REL
    target.mkdir(parents=True, exist_ok=True)
    keep = target / ".keep"
    if not keep.is_file():
        keep.write_text("# AI session sandbox — destroyed with workspace\n", encoding="utf-8")
    return target


def _rel_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def template_has_relative(templates_dir: Path, genre: str, rel_posix: str) -> bool:
    """模板里是否已有该相对路径（沙箱外一律禁止覆盖这类文件）。"""
    candidate = (templates_dir / genre / rel_posix).resolve()
    templates = templates_dir.resolve()
    if templates not in candidate.parents and candidate != templates:
        return False
    return candidate.is_file() or candidate.is_dir()


def assert_sandbox_write_allowed(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    genre: str,
    rel_posix: str,
) -> Path:
    """校验相对路径可写：必须落在 core/ai_sandbox/ 下。"""
    rel = rel_posix.strip().replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if (
        not rel
        or "\x00" in rel
        or ".." in parts
        or "." in parts
        or "" in parts
    ):
        raise AiSandboxError(f"非法沙箱路径: {rel_posix!r}")
    if not rel.startswith(f"{AI_SANDBOX_REL}/"):
        raise AiSandboxError(
            f"LLM 只能新建 {AI_SANDBOX_REL}/ 下的文件，拒绝: {rel}"
        )
    # 必须是沙箱内的具体文件，禁止把目录本身当写入目标
    if rel.rstrip("/") == AI_SANDBOX_REL or rel.endswith("/"):
        raise AiSandboxError(f"必须指定沙箱内文件名，拒绝: {rel}")
    # 模板侧不应存在同名路径（防止误覆盖模板）
    if template_has_relative(templates_dir, genre, rel):
        raise AiSandboxError(f"拒绝覆盖模板已有路径: {rel}")

    root = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())
    assert_not_under_templates(root, templates_dir.resolve())
    target = (root / rel).resolve()
    assert_under_workspace(target, workspace_dir.resolve())
    assert_not_under_templates(target, templates_dir.resolve())
    # 目标父目录必须仍在 sandbox 内
    sand = (root / AI_SANDBOX_REL).resolve()
    if target != sand and sand not in target.parents:
        raise AiSandboxError(f"路径越出沙箱: {rel}")
    return target


def validate_gdscript_content(filename: str, content: str) -> str:
    name = filename.replace("\\", "/").lstrip("/")
    if not (_SAFE_GD_NAME.match(name) or _SAFE_GD_REL.match(name)):
        raise AiSandboxError(f"非法脚本名: {filename}")
    text = content.replace("\r\n", "\n")
    if len(text.encode("utf-8")) > 48_000:
        raise AiSandboxError("脚本过大")
    if "extends " not in text:
        raise AiSandboxError("脚本必须有 extends")
    lowered = text
    for snip in _FORBIDDEN_GD_SNIPPETS:
        if snip in lowered:
            raise AiSandboxError(f"脚本含禁止调用: {snip}")
    # 禁止改写冻结 core：不得 open 写 templates 语义路径
    if re.search(r'FileAccess\.open\([^)]*WRITE', text):
        raise AiSandboxError("沙箱脚本禁止 FileAccess WRITE")
    return text


def validate_svg_content(content: str) -> str:
    text = content.replace("\r\n", "\n").strip()
    if len(text.encode("utf-8")) > 16_000:
        raise AiSandboxError("图标过大")
    if not text.lstrip().lower().startswith("<svg"):
        raise AiSandboxError("须为 SVG 图标")
    lowered = text.lower()
    for bad in ("<script", "javascript:", "onclick", "onerror", "onload", "<foreignobject"):
        if bad in lowered:
            raise AiSandboxError("SVG 含禁止内容")
    return text


def decode_png_bytes(content: str | bytes) -> bytes:
    if isinstance(content, bytes):
        raw = content
    else:
        text = content.strip()
        if text.startswith("data:image/png;base64,"):
            text = text.split(",", 1)[1]
        try:
            import base64

            raw = base64.b64decode(text, validate=False)
        except Exception as exc:  # noqa: BLE001
            raise AiSandboxError("PNG base64 无效") from exc
    if len(raw) > 64_000:
        raise AiSandboxError("图标过大")
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise AiSandboxError("不是合法 PNG")
    return raw


def write_sandbox_asset(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    genre: str,
    rel_under_sandbox: str,
    content: str | bytes,
) -> str:
    """写入沙箱图标等资产。rel 形如 icons/double_jump.svg（相对 ai_sandbox）。"""
    rel_local = rel_under_sandbox.strip().replace("\\", "/").lstrip("/")
    if rel_local == "icons/manifest.json":
        if isinstance(content, bytes):
            text = content.decode("utf-8")
        else:
            text = str(content)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AiSandboxError("manifest.json 须为 JSON") from exc
        if not isinstance(parsed, dict):
            raise AiSandboxError("manifest.json 须为对象")
        payload: str | bytes = json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"
    elif _SAFE_ICON_REL.match(rel_local):
        if rel_local.endswith(".svg"):
            if isinstance(content, bytes):
                payload = validate_svg_content(content.decode("utf-8"))
            else:
                payload = validate_svg_content(content)
        else:
            payload = decode_png_bytes(content)
    else:
        raise AiSandboxError(f"非法沙箱资产路径: {rel_under_sandbox!r}")

    rel = f"{AI_SANDBOX_REL}/{rel_local}"
    written = write_sandbox_file(
        workspace_root, workspace_dir, templates_dir, genre, rel, payload
    )
    _update_manifest(workspace_root, written, "icon")
    return written


def write_sandbox_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    genre: str,
    rel_posix: str,
    content: str | bytes,
    *,
    encoding: str = "utf-8",
) -> str:
    """写入沙箱文件，返回相对路径。"""
    target = assert_sandbox_write_allowed(
        workspace_root, workspace_dir, templates_dir, genre, rel_posix
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding=encoding)
    return _rel_posix(target, workspace_root.resolve())


def write_overrides_json(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    genre: str,
    patch: dict[str, Any],
) -> str:
    """写入 / 合并 overrides.json（会话沙箱内，可反复覆写）。"""
    ensure_sandbox_dir(workspace_root, workspace_dir, templates_dir)
    rel = f"{AI_SANDBOX_REL}/{OVERRIDES_FILENAME}"
    target = assert_sandbox_write_allowed(
        workspace_root, workspace_dir, templates_dir, genre, rel
    )
    existing: dict[str, Any] = {}
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except json.JSONDecodeError:
            existing = {}
    merged = _deep_merge(existing, patch)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _update_manifest(workspace_root, rel, "overrides")
    return rel


def write_modifier_gdscript(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    genre: str,
    filename: str,
    content: str,
) -> str:
    safe = validate_gdscript_content(filename, content)
    rel = f"{AI_SANDBOX_REL}/{filename}"
    write_sandbox_file(
        workspace_root, workspace_dir, templates_dir, genre, rel, safe
    )
    _update_manifest(workspace_root, rel, "gdscript")
    return rel


def destroy_ai_sandbox(workspace_root: Path) -> bool:
    """显式销毁沙箱目录（release 前可调用；整棵 workspace 删除时也会带走）。"""
    target = sandbox_dir(workspace_root)
    if not target.is_dir():
        return False
    shutil.rmtree(target, ignore_errors=True)
    return True


def list_sandbox_files(workspace_root: Path) -> list[str]:
    root = sandbox_dir(workspace_root)
    if not root.is_dir():
        return []
    out: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != ".keep":
            out.append(_rel_posix(path, workspace_root.resolve()))
    return out


def _update_manifest(workspace_root: Path, rel: str, kind: str) -> None:
    man = sandbox_dir(workspace_root) / MANIFEST_FILENAME
    data: dict[str, Any] = {"files": []}
    if man.is_file():
        try:
            loaded = json.loads(man.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            pass
    files = data.get("files")
    if not isinstance(files, list):
        files = []
    files = [f for f in files if not (isinstance(f, dict) and f.get("path") == rel)]
    files.append({"path": rel, "kind": kind})
    data["files"] = files
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = json.loads(json.dumps(base))
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def changes_to_overrides_patch(changes: list[dict[str, Any]]) -> dict[str, Any]:
    """把 [{path, after}] 转成嵌套 dict，供 overrides.json。"""
    from app.services.config_builder import set_path

    patch: dict[str, Any] = {}
    for change in changes:
        path = str(change.get("path", "")).strip()
        if not path:
            continue
        set_path(patch, path, change.get("after"))
    return patch
