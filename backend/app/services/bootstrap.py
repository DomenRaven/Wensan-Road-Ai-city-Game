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
from app.stores.session_store import MemorySessionStore, SessionStore

# 孤儿清理最短存活：避免刚写入的教学副本在 memory 抖动/误判时被秒删
_ORPHAN_MIN_AGE_SEC: float = 6 * 3600


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
    certificate: dict[str, Any] = field(default_factory=dict)

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
            "certificate": self.certificate,
        }


def certificate_deploy_config(settings: Settings) -> dict[str, Any]:
    """展馆实装 · 证书扫码下载契约（供 Kiosk bootstrap 同步）。"""
    public_base: str = settings.public_api_base.strip().rstrip("/")
    ttl_sec: int = settings.certificate_download_ttl_sec
    relay_on: bool = bool(settings.certificate_relay_enabled)
    return {
        "public_download_base": public_base,
        "download_ttl_sec": ttl_sec,
        # 自有公网 或 临时图床中继，均可让游客手机扫码
        "ready_for_public_qr": bool(public_base) or relay_on,
        "relay_enabled": relay_on,
        "endpoints": {
            "upload": "PUT /sessions/{session_id}/certificate",
            "public_download": "GET /public/certificates/{token}",
            "legacy_session_download": "GET /sessions/{session_id}/certificate/download",
        },
    }


def run_startup_bootstrap(
    settings: Settings,
    store: SessionStore,
    *,
    cleanup_orphans: bool = True,
) -> BootstrapReport:
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
    removed: list[str] = []
    if cleanup_orphans:
        # memory 冷启动 active 为空时，全量清理会误删全部教学副本（SW-2）
        if isinstance(store, MemorySessionStore) and not active_ids:
            messages.append(
                "memory 会话冷启动且无活跃会话：跳过孤立 workspace 全量清理（防误删）"
            )
        else:
            removed = cleanup_orphan_workspaces(
                workspace_dir,
                active_ids,
                min_age_sec=_ORPHAN_MIN_AGE_SEC,
            )
            if removed:
                messages.append(f"已清理孤立 workspace: {len(removed)} 个")
    else:
        messages.append("本次 bootstrap 未执行孤立 workspace 清理")

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
        certificate=certificate_deploy_config(settings),
    )
