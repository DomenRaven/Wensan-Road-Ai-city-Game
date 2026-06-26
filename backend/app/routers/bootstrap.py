from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.services.bootstrap import run_startup_bootstrap

router = APIRouter(tags=["bootstrap"])


@router.get("/bootstrap")
def get_bootstrap_status(request: Request) -> dict[str, Any]:
    """Kiosk 启动校验：模板完整性 + 清理无活跃 session 的孤儿 workspace。"""
    settings = request.app.state.settings
    store = request.app.state.session_store
    report = run_startup_bootstrap(settings, store)
    request.app.state.bootstrap_report = report
    return report.to_dict()


@router.post("/bootstrap/refresh")
def refresh_bootstrap(request: Request) -> dict[str, Any]:
    """重新校验模板并清理孤立 workspace（展厅每日开馆前可调用）。"""
    settings = request.app.state.settings
    store = request.app.state.session_store
    report = run_startup_bootstrap(settings, store)
    request.app.state.bootstrap_report = report
    return report.to_dict()
