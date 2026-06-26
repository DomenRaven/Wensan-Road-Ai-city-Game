from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import CONFIG_DIR
from app.models.session import SessionCreateResponse, SessionListResponse, SessionPhase, SessionRecord
from app.services.play_variants import list_variants_for_genre
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
