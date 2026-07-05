from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import CONFIG_DIR
from app.models.session import SessionCreateResponse, SessionListResponse, SessionPhase, SessionRecord
from app.services.certificate_tokens import build_public_download_url, issue_token, revoke_tokens_for_session
from app.services.godot_launcher import get_launcher
from app.services.workspace import workspace_config_path
from app.services.workspace_guard import (
    WorkspaceGuardError,
    assert_under_workspace,
    remove_workspace,
    validate_session_id,
    workspace_root_for_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class WorkspaceGameConfigResponse(BaseModel):
    ok: bool
    genre: str
    content: str
    path: str


class WorkspaceFileResponse(BaseModel):
    ok: bool
    content: str
    path: str


class SessionPatchRequest(BaseModel):
    creator_name: str | None = None
    display_name: str | None = None


class CertificateUploadResponse(BaseModel):
    ok: bool
    download_token: str
    download_path: str
    download_url: str
    expires_in_sec: int


_CERTIFICATE_MAX_BYTES = 5 * 1024 * 1024
_CERTIFICATE_REL_PATH = "certificate.png"


_CREATOR_NAME_MAX = 8
_CREATOR_NAME_PATTERN = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9·]+$")


def _validate_creator_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(status_code=400, detail="creator_name is required")
    if len(name) > _CREATOR_NAME_MAX:
        raise HTTPException(status_code=400, detail=f"creator_name must be at most {_CREATOR_NAME_MAX} characters")
    if not _CREATOR_NAME_PATTERN.match(name):
        raise HTTPException(status_code=400, detail="creator_name contains invalid characters")
    return name


_WORKSPACE_FILE_PREFIXES: tuple[str, ...] = ("config/", "core/")


def _resolve_workspace_relative_file(
    workspace_root: Path,
    workspace_dir: Path,
    rel_path: str,
) -> Path:
    rel: str = rel_path.strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise WorkspaceGuardError(f"非法 workspace 相对路径: {rel_path!r}")
    if not rel.startswith(_WORKSPACE_FILE_PREFIXES):
        raise WorkspaceGuardError(f"仅允许读取 config/ 或 core/ 下文件: {rel_path!r}")
    target: Path = workspace_root / rel
    resolved: Path = assert_under_workspace(target, workspace_dir.resolve())
    if not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"workspace 中未找到文件: {rel}",
        )
    return resolved


@router.post("", response_model=SessionCreateResponse, status_code=201)
def create_session(request: Request) -> SessionCreateResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.create()
    if record is None:
        raise HTTPException(
            status_code=429,
            detail=f"Session pool full (max {settings.max_sessions})",
        )
    return SessionCreateResponse(
        session_id=record.session_id,
        phase=record.phase,
        wizard_step=record.wizard_step,
        queue_position=0,
    )


@router.get("", response_model=SessionListResponse)
def list_sessions(request: Request) -> SessionListResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    sessions: list[SessionRecord] = store.list_active()
    return SessionListResponse(
        active_count=len(sessions),
        max_sessions=settings.max_sessions,
        sessions=sessions,
    )


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(session_id: str, request: Request) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


@router.patch("/{session_id}", response_model=SessionRecord)
def patch_session(
    session_id: str,
    body: SessionPatchRequest,
    request: Request,
) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    payload: dict[str, Any] = dict(record.payload)
    meta: dict[str, Any] = dict(payload.get("meta", {}))

    if body.creator_name is not None:
        record.creator_name = _validate_creator_name(body.creator_name)
        meta["creator_name"] = record.creator_name

    if body.display_name is not None:
        name = body.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="display_name is required")
        record.display_name = name[:32]
        meta["display_name"] = record.display_name

    payload["meta"] = meta
    record.payload = payload
    store.save(record)
    return record


@router.delete("/{session_id}")
def reset_session(session_id: str, request: Request) -> dict[str, bool]:
    store = request.app.state.session_store
    settings = request.app.state.settings
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    revoke_tokens_for_session(settings.workspace_dir, session_id)
    get_launcher(settings).clear_session(session_id)
    workspace_removed: bool = remove_workspace(settings.workspace_dir, session_id)
    return {"deleted": True, "workspace_removed": workspace_removed}


@router.post("/{session_id}/release")
def release_session(session_id: str, request: Request) -> dict[str, bool]:
    """页面关闭/意外退出时释放会话：删 session 记录 + 清理 workspace 副本。"""
    return reset_session(session_id, request)


@router.get("/{session_id}/workspace/game-config", response_model=WorkspaceGameConfigResponse)
def get_workspace_game_config(session_id: str, request: Request) -> WorkspaceGameConfigResponse:
    """E-P0-17: 只读返回 workspace/{session_id}/config/game_config.json 全文。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path = workspace_root_for_session(settings.workspace_dir, session_id)
    config_path: Path = workspace_config_path(workspace_root)
    try:
        resolved: Path = assert_under_workspace(config_path, settings.workspace_dir.resolve())
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"workspace 中未找到 game_config.json: {resolved}",
        )

    content: str = resolved.read_text(encoding="utf-8")
    genre: str = record.genre or ""
    try:
        parsed: dict[str, Any] = json.loads(content)
        meta: dict[str, Any] = parsed.get("meta", {})
        if isinstance(meta, dict) and meta.get("genre"):
            genre = str(meta["genre"])
    except json.JSONDecodeError:
        pass
    if not genre:
        genre = str(record.payload.get("meta", {}).get("genre", "")).strip()

    rel_path: str = "config/game_config.json"
    return WorkspaceGameConfigResponse(
        ok=True,
        genre=genre,
        content=content,
        path=rel_path,
    )


@router.get("/{session_id}/workspace/file", response_model=WorkspaceFileResponse)
def get_workspace_file(
    session_id: str,
    request: Request,
    rel_path: str,
) -> WorkspaceFileResponse:
    """只读返回 workspace/{session_id}/ 下 config/ 或 core/ 内单个源文件。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path = workspace_root_for_session(settings.workspace_dir, session_id)
    try:
        resolved: Path = _resolve_workspace_relative_file(
            workspace_root,
            settings.workspace_dir.resolve(),
            rel_path,
        )
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content: str = resolved.read_text(encoding="utf-8")
    normalized: str = rel_path.strip().replace("\\", "/").lstrip("/")
    return WorkspaceFileResponse(ok=True, content=content, path=normalized)


def _certificate_path(session_id: str, workspace_dir: Path) -> Path:
    workspace_root: Path = workspace_root_for_session(workspace_dir, session_id)
    target: Path = workspace_root / _CERTIFICATE_REL_PATH
    return assert_under_workspace(target, workspace_dir.resolve())


@router.put("/{session_id}/certificate", response_model=CertificateUploadResponse)
async def upload_certificate(session_id: str, request: Request) -> CertificateUploadResponse:
    """展厅扫码下载：暂存 PNG 至 workspace/{session_id}/certificate.png。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    body: bytes = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty certificate body")
    if len(body) > _CERTIFICATE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="certificate too large")
    if not body.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="PNG required")

    cert_path: Path = _certificate_path(session_id, settings.workspace_dir)
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_bytes(body)

    display_name: str = (record.display_name or "证书").strip() or "证书"
    token, expires_at = issue_token(
        settings.workspace_dir,
        session_id,
        display_name,
        settings.certificate_download_ttl_sec,
    )

    expires_in_sec: int = max(0, int(expires_at - time.time()))
    public_base: str = settings.public_api_base.strip()
    download_path: str = f"/public/certificates/{token}"
    download_url: str = build_public_download_url(public_base, token)

    return CertificateUploadResponse(
        ok=True,
        download_token=token,
        download_path=download_path,
        download_url=download_url,
        expires_in_sec=expires_in_sec,
    )


@router.get("/{session_id}/certificate/download")
def download_certificate(session_id: str, request: Request) -> FileResponse:
    """手机扫码 GET 下载证书 PNG。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cert_path: Path = _certificate_path(session_id, settings.workspace_dir)
    if not cert_path.is_file():
        raise HTTPException(status_code=404, detail="certificate not found")

    display_name: str = (record.display_name or "证书").strip() or "证书"
    safe_name: str = re.sub(r'[\\/:*?"<>|]', "_", display_name)[:40]
    filename: str = f"{safe_name}_证书.png"

    return FileResponse(
        cert_path,
        media_type="image/png",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{session_id}/play", response_model=SessionRecord)
def mark_play(session_id: str, request: Request) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    record.phase = SessionPhase.PLAY
    record.wizard_step = "S9"
    store.save(record)
    return record
