from __future__ import annotations

from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.models.session import SessionPhase, SessionRecord
from app.services.edu_workspace import append_edu_action, read_edu_actions
from app.services.godot_launcher import LaunchResult, get_launcher
from app.services.workspace_guard import WorkspaceGuardError, validate_session_id

router = APIRouter(tags=["play"])


class PlayLaunchResponse(BaseModel):
    ok: bool
    session_id: str
    genre: str
    pid: int | None
    project_path: str
    godot_path: str
    message: str
    already_running: bool = False


class PlayActionRequest(BaseModel):
    action_id: str


class PlayActionResponse(BaseModel):
    ok: bool
    action_id: str
    t_ms: int


@router.post("/sessions/{session_id}/play/launch", response_model=PlayLaunchResponse)
def launch_play(
    session_id: str,
    request: Request,
    force: bool = Query(False, description="强制重新启动（Godot 已关闭时使用）"),
) -> PlayLaunchResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    genre: str = record.genre or ""
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成 S1 选择品类")
    try:
        launcher = get_launcher(settings)
        result: LaunchResult = launcher.launch(session_id, genre, force=force)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record.phase = SessionPhase.PLAY
    record.wizard_step = "S9"
    store.save(record)
    return PlayLaunchResponse(
        ok=result.ok,
        session_id=session_id,
        genre=result.genre,
        pid=result.pid,
        project_path=result.project_path,
        godot_path=result.godot_path,
        message=result.message,
        already_running=result.already_running,
    )


@router.get("/sessions/{session_id}/play/status")
def play_status(session_id: str, request: Request) -> dict[str, Any]:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    settings = request.app.state.settings
    launcher = get_launcher(settings)
    status: dict[str, object] = launcher.status(session_id)
    status["phase"] = record.phase
    status["genre"] = record.genre
    return status


@router.post("/sessions/{session_id}/play/action", response_model=PlayActionResponse)
def post_play_action(
    session_id: str,
    body: PlayActionRequest,
    request: Request,
) -> PlayActionResponse:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    action_id: str = body.action_id.strip()
    if not action_id:
        raise HTTPException(status_code=400, detail="action_id must not be empty")

    workspace_path: str = str(record.payload.get("workspace_path", "")).strip()
    if not workspace_path:
        raise HTTPException(status_code=400, detail="workspace_path missing; complete generate first")
    workspace_root: Path = Path(workspace_path)
    if not workspace_root.is_dir():
        raise HTTPException(status_code=400, detail="workspace_path invalid")

    t_ms: int = append_edu_action(workspace_root, action_id)
    return PlayActionResponse(ok=True, action_id=action_id, t_ms=t_ms)


@router.get("/sessions/{session_id}/play/actions")
def list_play_actions(
    session_id: str,
    request: Request,
    since: int = Query(0, ge=0, description="仅返回 t_ms 大于 since 的事件"),
) -> dict[str, Any]:
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_path: str = str(record.payload.get("workspace_path", "")).strip()
    if not workspace_path:
        return {"actions": [], "since": since}

    events: list[dict[str, object]] = read_edu_actions(Path(workspace_path), since_ms=since)
    return {"actions": events, "since": since}
