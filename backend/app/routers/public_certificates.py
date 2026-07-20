from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.services.certificate_tokens import CertificateTokenError, resolve_token
from app.services.workspace_guard import WorkspaceGuardError, assert_under_workspace, validate_session_id, workspace_root_for_session

router = APIRouter(tags=["public"])

_CERTIFICATE_REL_PATH = "certificate.png"


@router.get("/public/certificates/{token}")
def download_certificate_by_token(token: str, request: Request) -> FileResponse:
    """公网扫码下载：短期 token · 不暴露 session_id · 游客手机有网即可访问。"""
    settings = request.app.state.settings
    workspace_dir: Path = settings.workspace_dir.resolve()

    try:
        meta = resolve_token(workspace_dir, token)
    except CertificateTokenError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_id: str = str(meta["session_id"])
    raw_uid = meta.get("user_id")
    user_id: str | None = str(raw_uid).strip() if raw_uid else None
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=404, detail="certificate unavailable") from exc

    workspace_root: Path = workspace_root_for_session(
        workspace_dir, session_id, user_id=user_id or None
    )
    cert_path: Path = workspace_root / _CERTIFICATE_REL_PATH
    try:
        resolved: Path = assert_under_workspace(cert_path, workspace_dir)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=404, detail="certificate unavailable") from exc

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="certificate file missing")

    filename: str = str(meta.get("filename") or "certificate.png")
    return FileResponse(
        resolved,
        media_type="image/png",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )
