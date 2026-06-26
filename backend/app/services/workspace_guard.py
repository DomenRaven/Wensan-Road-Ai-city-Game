from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR

SESSION_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class WorkspaceGuardError(ValueError):
    """B 链 workspace 隔离或路径校验失败。"""


def validate_session_id(session_id: str) -> str:
    sid: str = session_id.strip()
    if not SESSION_ID_PATTERN.fullmatch(sid):
        raise WorkspaceGuardError(f"非法 session_id: {session_id!r}")
    try:
        uuid.UUID(sid)
    except ValueError as exc:
        raise WorkspaceGuardError(f"非法 session_id: {session_id!r}") from exc
    return sid


def workspace_root_for_session(workspace_dir: Path, session_id: str) -> Path:
    sid: str = validate_session_id(session_id)
    root: Path = workspace_dir.resolve()
    target: Path = (root / sid).resolve()
    if target != root and root not in target.parents:
        raise WorkspaceGuardError(f"workspace 路径越界: {target}")
    return target


def ensure_workspace_root(workspace_dir: Path) -> Path:
    root: Path = workspace_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    readme: Path = root / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# GameForge workspace\n\n"
            "B 链个性化副本目录。每个 session 独占子目录，**禁止**直接修改 `templates/`。\n",
            encoding="utf-8",
        )
    return root


def assert_under_workspace(path: Path, workspace_root: Path) -> Path:
    resolved: Path = path.resolve()
    root: Path = workspace_root.resolve()
    if resolved == root or root in resolved.parents:
        return resolved
    raise WorkspaceGuardError(f"拒绝写入 workspace 外路径: {resolved}")


def assert_not_under_templates(path: Path, templates_dir: Path) -> None:
    resolved: Path = path.resolve()
    templates: Path = templates_dir.resolve()
    if resolved == templates or templates in resolved.parents:
        raise WorkspaceGuardError(f"拒绝写入模板目录: {resolved}")


def validate_template_genre(templates_dir: Path, genre: str) -> dict[str, str]:
    slug: str = genre.strip()
    if not slug or "/" in slug or "\\" in slug or ".." in slug:
        raise WorkspaceGuardError(f"非法品类 slug: {genre!r}")
    source: Path = (templates_dir / slug).resolve()
    templates: Path = templates_dir.resolve()
    if templates not in source.parents and source != templates:
        raise WorkspaceGuardError(f"模板路径越界: {source}")
    project_file: Path = source / "project.godot"
    config_file: Path = source / "config" / "game_config.json"
    missing: list[str] = []
    if not project_file.is_file():
        missing.append("project.godot")
    if not config_file.is_file():
        missing.append("config/game_config.json")
    if missing:
        raise FileNotFoundError(f"模板不完整 templates/{slug}/: {', '.join(missing)}")
    return {
        "slug": slug,
        "template_path": str(source),
        "project_godot": str(project_file),
        "game_config": str(config_file),
    }


def load_featured_genre_slugs() -> list[str]:
    spec_path: Path = CONFIG_DIR / "kiosk_ui_spec.json"
    if spec_path.is_file():
        data: dict[str, Any] = json.loads(spec_path.read_text(encoding="utf-8"))
        featured: dict[str, Any] = data.get("featured_genres", {})
        slugs: list[str] = [str(s) for s in featured.get("slugs", []) if s]
        if slugs:
            return slugs
    registry_path: Path = CONFIG_DIR / "genre_registry.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return [str(g["slug"]) for g in data.get("genres", [])]


def validate_featured_templates(templates_dir: Path, slugs: list[str] | None = None) -> dict[str, Any]:
    genre_slugs: list[str] = slugs or load_featured_genre_slugs()
    ok: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for slug in genre_slugs:
        try:
            ok.append(validate_template_genre(templates_dir, slug))
        except (FileNotFoundError, WorkspaceGuardError) as exc:
            errors.append({"slug": slug, "error": str(exc)})
    return {
        "featured_count": len(genre_slugs),
        "ok_count": len(ok),
        "error_count": len(errors),
        "ok": ok,
        "errors": errors,
        "ready": len(errors) == 0 and len(ok) > 0,
    }


def list_workspace_session_ids(workspace_dir: Path) -> list[str]:
    root: Path = ensure_workspace_root(workspace_dir)
    ids: list[str] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name: str = child.name
        if name.startswith("."):
            continue
        if SESSION_ID_PATTERN.fullmatch(name):
            ids.append(name)
    return ids


def remove_workspace(workspace_dir: Path, session_id: str) -> bool:
    target: Path = workspace_root_for_session(workspace_dir, session_id)
    if not target.exists():
        return False
    try:
        shutil.rmtree(target)
    except PermissionError:
        return False
    return True


def cleanup_orphan_workspaces(workspace_dir: Path, active_session_ids: set[str]) -> list[str]:
    removed: list[str] = []
    for sid in list_workspace_session_ids(workspace_dir):
        if sid in active_session_ids:
            continue
        if remove_workspace(workspace_dir, sid):
            removed.append(sid)
    return removed


def copy_template_to_workspace(
    templates_dir: Path,
    workspace_dir: Path,
    genre: str,
    session_id: str,
) -> Path:
    """Copy templates/{genre}/ → workspace/{session_id}/ (B1) · 仅写 workspace。"""
    validate_template_genre(templates_dir, genre)
    source: Path = (templates_dir / genre).resolve()
    root: Path = ensure_workspace_root(workspace_dir)
    target: Path = workspace_root_for_session(root, session_id)
    assert_not_under_templates(target, templates_dir)

    tmp: Path = root / f".{validate_session_id(session_id)}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    if target.exists():
        shutil.rmtree(target)

    try:
        shutil.copytree(source, tmp)
        tmp.rename(target)
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        raise

    return target.resolve()
