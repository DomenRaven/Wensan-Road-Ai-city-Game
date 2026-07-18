"""S-A2 / S-A4 · 自然语言改参（nl-patch）+ webgame 配方下发（可选轨）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.session import SessionRecord
from app.services.creative.llm_patch import NlPatchError, apply_nl_patch
from app.services.creative.agent_contracts import read_progress
from app.services.workspace import workspace_config_path
from app.services.workspace_guard import (
    WorkspaceGuardError,
    assert_under_workspace,
    validate_session_id,
    workspace_root_for_session,
)

router = APIRouter(tags=["nl-patch"])


class NlPatchHistoryTurn(BaseModel):
    role: str = Field(description="user | assistant")
    content: str = Field(default="")


class NlPatchRequest(BaseModel):
    text: str = Field(default="", description="小朋友的自然语言改参要求")
    history: list[NlPatchHistoryTurn] = Field(
        default_factory=list, description="多轮对话历史（可选）"
    )
    feedback: str = Field(
        default="", description="试玩反馈，如「没生效」「只有图标没有二段跳」"
    )


class NlPatchChange(BaseModel):
    path: str
    before: Any = None
    after: Any = None


class NlPatchResponse(BaseModel):
    ok: bool
    provider: str
    summary: str
    message: str
    changes: list[NlPatchChange]
    sandbox_files: list[str] = Field(default_factory=list)
    how_to_play: list[str] = Field(default_factory=list)
    applied_capabilities: list[str] = Field(default_factory=list)
    needs_relaunch: bool = False
    verify_gaps: list[str] = Field(default_factory=list)
    repaired: bool = False
    llm_error: str = ""
    learned_skills: list[str] = Field(default_factory=list)
    demoted_skills: list[str] = Field(default_factory=list)
    gate_passed: bool = False
    understanding: str = ""
    goals: list[str] = Field(default_factory=list)


class AgentProgressResponse(BaseModel):
    stage: str = ""
    title: str = ""
    detail: str = ""


class WebgameConfigResponse(BaseModel):
    ok: bool
    session_id: str
    genre: str
    tuning: dict[str, Any]
    theme: dict[str, Any]
    config: dict[str, Any]


def _session_or_404(request: Request, session_id: str) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


def _genre_of(record: SessionRecord) -> str:
    genre: str = record.genre or str(record.payload.get("meta", {}).get("genre", "")).strip()
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成品类匹配")
    return genre


@router.post("/sessions/{session_id}/nl-patch", response_model=NlPatchResponse)
def post_nl_patch(session_id: str, body: NlPatchRequest, request: Request) -> NlPatchResponse:
    record: SessionRecord = _session_or_404(request, session_id)
    settings = request.app.state.settings
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    genre: str = _genre_of(record)
    workspace_path: str = str(record.payload.get("workspace_path", "")).strip()
    workspace_root: Path = (
        Path(workspace_path)
        if workspace_path
        else workspace_root_for_session(settings.workspace_dir, session_id)
    )
    if not workspace_root.is_dir():
        raise HTTPException(status_code=400, detail="workspace 尚未生成，请先完成制作")

    history_payload: list[dict[str, str]] = [
        {"role": t.role, "content": t.content} for t in body.history
    ]
    try:
        result: dict[str, Any] = apply_nl_patch(
            settings,
            workspace_root,
            settings.templates_dir,
            genre,
            body.text,
            history=history_payload,
            feedback=body.feedback,
        )
    except NlPatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return NlPatchResponse(
        ok=bool(result.get("ok")),
        provider=str(result.get("provider", "stub")),
        summary=str(result.get("summary", "")),
        message=str(result.get("message", "")),
        changes=[NlPatchChange(**c) for c in result.get("changes", [])],
        sandbox_files=[str(p) for p in result.get("sandbox_files", [])],
        how_to_play=[str(x) for x in result.get("how_to_play", [])],
        applied_capabilities=[str(x) for x in result.get("applied_capabilities", [])],
        needs_relaunch=bool(result.get("needs_relaunch")),
        verify_gaps=[str(x) for x in result.get("verify_gaps", [])],
        repaired=bool(result.get("repaired")),
        llm_error=str(result.get("llm_error", "") or ""),
        learned_skills=[str(x) for x in result.get("learned_skills", [])],
        demoted_skills=[str(x) for x in result.get("demoted_skills", [])],
        gate_passed=bool(result.get("gate_passed")),
        understanding=str(result.get("understanding", "") or ""),
        goals=[str(x) for x in (result.get("goals") or []) if str(x).strip()],
    )


@router.get("/sessions/{session_id}/agent-progress", response_model=AgentProgressResponse)
def get_agent_progress(session_id: str, request: Request) -> AgentProgressResponse:
    """智能体多阶段进度（Kiosk 轮询 · 中文阶段名）。

    优先读会话记录里的 workspace_path；会话短暂丢失时仍尽量读盘，避免前端误判「无输出」。
    """
    settings = request.app.state.settings
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path | None = None
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is not None:
        wp = str(record.payload.get("workspace_path", "")).strip()
        if wp:
            workspace_root = Path(wp)
    if workspace_root is None:
        workspace_root = workspace_root_for_session(settings.workspace_dir, session_id)
    if not workspace_root.is_dir():
        return AgentProgressResponse()
    prog = read_progress(workspace_root)
    return AgentProgressResponse(
        stage=str(prog.get("stage") or ""),
        title=str(prog.get("title") or ""),
        detail=str(prog.get("detail") or ""),
    )


@router.get("/sessions/{session_id}/webgame-config", response_model=WebgameConfigResponse)
def get_webgame_config(session_id: str, request: Request) -> WebgameConfigResponse:
    """S-A4 · 可选轨：下发当前 workspace 配方（tuning/theme），供 Web 内嵌预留使用。

    默认「开始试玩」不走此接口；此为兼容/预留能力，读同一份 game_config.json。
    """
    record: SessionRecord = _session_or_404(request, session_id)
    settings = request.app.state.settings
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
        raise HTTPException(status_code=404, detail="workspace 尚未生成，请先完成制作")

    config: dict[str, Any] = json.loads(resolved.read_text(encoding="utf-8"))
    genre: str = _genre_of(record)
    meta: Any = config.get("meta", {})
    if isinstance(meta, dict) and meta.get("genre"):
        genre = str(meta["genre"])

    tuning: Any = config.get("tuning", {})
    theme: Any = config.get("theme", {})
    return WebgameConfigResponse(
        ok=True,
        session_id=session_id,
        genre=genre,
        tuning=tuning if isinstance(tuning, dict) else {},
        theme=theme if isinstance(theme, dict) else {},
        config=config,
    )
