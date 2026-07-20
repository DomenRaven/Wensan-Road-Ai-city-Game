from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel

from app.config import Settings
from app.models.session import SessionPhase, SessionRecord
from app.services.edu_workspace import (
    append_edu_action,
    apply_edu_workspace_patch,
    read_edu_actions,
)
from app.services.godot_launcher import LaunchResult, get_launcher
from app.services.godot_window_layout import WindowRect, get_monitor_fullscreen_rect
from app.services.workspace_guard import (
    WorkspaceGuardError,
    validate_session_id,
    workspace_root_for_session,
)

router = APIRouter(tags=["play"])


class ClientViewportRect(BaseModel):
    x: int
    y: int
    w: int
    h: int


class ClientViewport(BaseModel):
    screen_x: int = 0
    screen_y: int = 0
    screen_w: int = 0
    screen_h: int = 0
    monitor_x: int = 0
    monitor_y: int = 0
    devicePixelRatio: float = 1.0
    kiosk_rect: ClientViewportRect | None = None
    godot_zone_rect: ClientViewportRect | None = None


class LaunchPlayRequest(BaseModel):
    orientation: Literal["landscape", "portrait"] | None = None
    client_viewport: ClientViewport | None = None


class PlacementRectResponse(BaseModel):
    x: int
    y: int
    w: int
    h: int


class PlayLaunchResponse(BaseModel):
    ok: bool
    session_id: str
    genre: str
    pid: int | None
    project_path: str
    godot_path: str
    message: str
    already_running: bool = False
    window_placed: bool = False
    placement_rect: PlacementRectResponse | None = None
    # W7 · S2-路B：server=现网 API 机起窗；local_share=仅返回本机路径，不起服务器 Godot
    launch_mode: Literal["server", "local_share"] = "server"
    ready_for_local_godot: bool = False


class PlayActionRequest(BaseModel):
    action_id: str


class PlayActionResponse(BaseModel):
    ok: bool
    action_id: str
    t_ms: int


def _display_anchor(client_viewport: ClientViewport) -> tuple[int, int]:
    """浏览器/展台所在显示器上的一个点，用于 Win32 定位目标显示器。"""
    kiosk = client_viewport.kiosk_rect
    if kiosk is not None and kiosk.w > 0 and kiosk.h > 0:
        return kiosk.x + kiosk.w // 2, kiosk.y + kiosk.h // 2
    if client_viewport.screen_w > 0 and client_viewport.screen_h > 0:
        return (
            client_viewport.monitor_x + client_viewport.screen_w // 2,
            client_viewport.monitor_y + client_viewport.screen_h // 2,
        )
    return client_viewport.screen_x, client_viewport.screen_y


def resolve_placement_rect(
    orientation: Literal["landscape", "portrait"] | None,
    client_viewport: ClientViewport | None,
) -> WindowRect | None:
    """S-A1 / N-1 · Godot 按真实显示器全屏铺满（禁止默认小窗 / 停靠半屏）。

    几何来自「游戏所在那块屏」的当前宽高与方向：优先 Win32 枚举真实显示器边界
    （多屏 + 横/竖屏自适应），失败时回退浏览器上报的整屏尺寸。orientation 仅用于
    锚点选择与降级，不再决定窗口大小——显示器自身的 w/h 决定横竖。
    """
    if client_viewport is None:
        return None

    anchor_x, anchor_y = _display_anchor(client_viewport)
    monitor_rect: WindowRect | None = get_monitor_fullscreen_rect(anchor_x, anchor_y)
    if monitor_rect is not None:
        return monitor_rect

    sw: int = client_viewport.screen_w
    sh: int = client_viewport.screen_h
    if sw > 0 and sh > 0:
        return {
            "x": client_viewport.monitor_x,
            "y": client_viewport.monitor_y,
            "w": sw,
            "h": sh,
        }
    return None


def _placement_response(rect: WindowRect | None) -> PlacementRectResponse | None:
    if rect is None:
        return None
    return PlacementRectResponse(x=rect["x"], y=rect["y"], w=rect["w"], h=rect["h"])


def _normalize_play_launch_mode(raw: str) -> Literal["server", "local_share"]:
    mode: str = (raw or "server").strip().lower()
    if mode == "local_share":
        return "local_share"
    return "server"


def _resolve_session_project_path(
    *,
    settings: Settings,
    session_id: str,
    user_id: str | None,
    workspace_path: str,
) -> Path:
    """优先会话 workspace；须已有 project.godot（local_share 不回退模板）。"""
    if workspace_path:
        root: Path = Path(workspace_path)
        if (root / "project.godot").is_file():
            return root.resolve()
    try:
        sid: str = validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    workspace: Path = workspace_root_for_session(
        settings.workspace_dir, sid, user_id=user_id
    )
    if (workspace / "project.godot").is_file():
        return workspace.resolve()
    raise HTTPException(
        status_code=400,
        detail="workspace 尚未生成，请先完成制作后再试玩",
    )


@router.post("/sessions/{session_id}/play/launch", response_model=PlayLaunchResponse)
def launch_play(
    session_id: str,
    request: Request,
    force: bool = Query(False, description="强制重新启动（Godot 已关闭时使用）"),
    body: LaunchPlayRequest | None = Body(default=None),
) -> PlayLaunchResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    genre: str = record.genre or ""
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成 S1 选择品类")
    workspace_path: str = str(record.payload.get("workspace_path", "")).strip()
    if workspace_path:
        workspace_root: Path = Path(workspace_path)
        if workspace_root.is_dir():
            apply_edu_workspace_patch(
                workspace_root,
                genre,
                settings.templates_dir,
                settings.workspace_dir,
            )
    launch_mode: Literal["server", "local_share"] = _normalize_play_launch_mode(
        str(getattr(settings, "play_launch_mode", "server"))
    )

    # S2-路B：服务器不替学生起 Godot，只回本机会话路径供映射盘/脚本启动
    if launch_mode == "local_share":
        project: Path = _resolve_session_project_path(
            settings=settings,
            session_id=session_id,
            user_id=record.user_id,
            workspace_path=workspace_path,
        )
        record.phase = SessionPhase.PLAY
        record.wizard_step = "S9"
        store.save(record)
        return PlayLaunchResponse(
            ok=True,
            session_id=session_id,
            genre=genre,
            pid=None,
            project_path=str(project),
            godot_path="",
            message=(
                "本机会话目录已就绪。请用学生机上的 Godot 4.6 打开该路径"
                "（服务器不会启动试玩窗口）"
            ),
            already_running=False,
            window_placed=False,
            placement_rect=None,
            launch_mode="local_share",
            ready_for_local_godot=True,
        )

    launch_body: LaunchPlayRequest = body or LaunchPlayRequest()
    layout_rect: WindowRect | None = resolve_placement_rect(
        launch_body.orientation,
        launch_body.client_viewport,
    )
    try:
        launcher = get_launcher(settings)
        result: LaunchResult = launcher.launch(
            session_id,
            genre,
            force=force,
            layout_rect=layout_rect,
            user_id=record.user_id,
        )
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
        window_placed=result.window_placed,
        placement_rect=_placement_response(result.placement_rect),
        launch_mode="server",
        ready_for_local_godot=False,
    )


@router.get("/sessions/{session_id}/play/status")
def play_status(session_id: str, request: Request) -> dict[str, Any]:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    settings = request.app.state.settings
    launch_mode: Literal["server", "local_share"] = _normalize_play_launch_mode(
        str(getattr(settings, "play_launch_mode", "server"))
    )
    if launch_mode == "local_share":
        workspace_path: str = str(record.payload.get("workspace_path", "")).strip()
        project_path: str = ""
        try:
            project_path = str(
                _resolve_session_project_path(
                    settings=settings,
                    session_id=session_id,
                    user_id=record.user_id,
                    workspace_path=workspace_path,
                )
            )
        except HTTPException:
            project_path = workspace_path
        return {
            "session_id": session_id,
            "pid": None,
            "running": False,
            "project_path": project_path,
            "phase": record.phase,
            "genre": record.genre,
            "launch_mode": "local_share",
            "ready_for_local_godot": bool(project_path),
            "server_godot": False,
        }
    launcher = get_launcher(settings)
    status: dict[str, object] = launcher.status(session_id)
    status["phase"] = record.phase
    status["genre"] = record.genre
    status["launch_mode"] = "server"
    status["server_godot"] = True
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
