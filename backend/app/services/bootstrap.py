from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.workspace_guard import (
    cleanup_orphan_workspaces,
    ensure_workspace_root,
    load_featured_genre_slugs,
    validate_featured_templates,
)
from app.stores.session_store import SessionStore


@dataclass
class BootstrapReport:
    ready: bool
    workspace_dir: str
    templates_dir: str
    featured_slugs: list[str] = field(default_factory=list)
    template_validation: dict[str, Any] = field(default_factory=dict)
    orphan_workspaces_removed: list[str] = field(default_factory=list)
    active_sessions: int = 0
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "workspace_dir": self.workspace_dir,
            "templates_dir": self.templates_dir,
            "featured_slugs": self.featured_slugs,
            "template_validation": self.template_validation,
            "orphan_workspaces_removed": self.orphan_workspaces_removed,
            "active_sessions": self.active_sessions,
            "messages": self.messages,
            "b_chain": {
                "writes_to": "workspace/{session_id}/ only",
                "templates_readonly": True,
                "user_isolation": "per session_id workspace copy",
            },
        }


def run_startup_bootstrap(settings: Settings, store: SessionStore) -> BootstrapReport:
    workspace_dir: Path = ensure_workspace_root(settings.workspace_dir)
    templates_dir: Path = settings.templates_dir.resolve()
    featured_slugs: list[str] = load_featured_genre_slugs()

    messages: list[str] = []
    if not templates_dir.is_dir():
        messages.append(f"templates 目录不存在: {templates_dir}")

    template_validation: dict[str, Any] = validate_featured_templates(templates_dir, featured_slugs)
    if not template_validation.get("ready"):
        messages.append("部分精选模板未通过校验")

    active_ids: set[str] = {s.session_id for s in store.list_active()}
    removed: list[str] = cleanup_orphan_workspaces(workspace_dir, active_ids)
    if removed:
        messages.append(f"已清理孤立 workspace: {len(removed)} 个")

    ready: bool = bool(template_validation.get("ready")) and templates_dir.is_dir()
    return BootstrapReport(
        ready=ready,
        workspace_dir=str(workspace_dir),
        templates_dir=str(templates_dir),
        featured_slugs=featured_slugs,
        template_validation=template_validation,
        orphan_workspaces_removed=removed,
        active_sessions=store.count_active(),
        messages=messages,
    )
