from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    store = request.app.state.session_store
    store_ok: bool = store.ping()
    bootstrap = getattr(request.app.state, "bootstrap_report", None)
    return {
        "status": "ok" if store_ok and (bootstrap is None or bootstrap.ready) else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "session_backend": request.app.state.store_backend,
        "redis_url": settings.redis_url,
        "store_ok": store_ok,
        "active_sessions": store.count_active(),
        "max_sessions": settings.max_sessions,
        "bootstrap_ready": None if bootstrap is None else bootstrap.ready,
        "deployment": {
            "server_os": settings.deployment_server_os,
            "terminal_layout": settings.deployment_terminal_layout,
        },
    }
