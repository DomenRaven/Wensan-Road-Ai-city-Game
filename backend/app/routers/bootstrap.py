from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.services.bootstrap import run_startup_bootstrap

router = APIRouter(tags=["bootstrap"])


@router.get("/bootstrap")
def get_bootstrap_status(request: Request) -> dict[str, Any]:
    """Kiosk 启动校验（只读）。

    SW-1：不再每次 GET 都清孤儿 workspace。优先返回启动时缓存的报告，
    仅刷新 active_sessions；若尚无缓存则跑一次「不清理」的校验。
    """
    settings = request.app.state.settings
    store = request.app.state.session_store
    cached = getattr(request.app.state, "bootstrap_report", None)
    if cached is not None:
        cached.active_sessions = store.count_active()
        return cached.to_dict()
    report = run_startup_bootstrap(settings, store, cleanup_orphans=False)
    request.app.state.bootstrap_report = report
    return report.to_dict()


@router.post("/bootstrap/refresh")
def refresh_bootstrap(request: Request) -> dict[str, Any]:
    """重新校验模板并（安全策略下）清理孤立 workspace（展厅每日开馆前可调用）。"""
    settings = request.app.state.settings
    store = request.app.state.session_store
    report = run_startup_bootstrap(settings, store, cleanup_orphans=True)
    request.app.state.bootstrap_report = report
    return report.to_dict()
