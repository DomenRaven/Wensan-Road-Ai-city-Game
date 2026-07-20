"""S-A2 / S-A4 · 自然语言改参（nl-patch）+ webgame 配方下发（可选轨）。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.models.session import SessionRecord
from app.services.agent_queue import AgentQueueError, get_agent_queue
from app.services.auth_deps import assert_session_access, get_optional_user
from app.services.auth_store import AuthUser
from app.services.creative.llm_patch import NlPatchError, apply_nl_patch
from app.services.creative.agent_contracts import read_progress
from app.services.learning_analytics import RATING_LABELS, compose_agent_reply_full, get_learning_store
from app.services.turn_diff import compute_turn_diff, snapshot_workspace_texts
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
    attempted_paths: list[str] = Field(
        default_factory=list,
        description="门禁未过时曾尝试写入的路径（已回滚则仅作说明）",
    )
    how_to_play: list[str] = Field(default_factory=list)
    applied_capabilities: list[str] = Field(default_factory=list)
    needs_relaunch: bool = False
    verify_gaps: list[str] = Field(default_factory=list)
    repaired: bool = False
    llm_error: str = ""
    learned_skills: list[str] = Field(default_factory=list)
    demoted_skills: list[str] = Field(default_factory=list)
    gate_passed: bool = False
    partial: bool = False
    rolled_back: bool = False
    express: bool = False
    agent_rounds: int | None = None
    understanding: str = ""
    goals: list[str] = Field(default_factory=list)
    turn_id: str = ""
    has_diff: bool = False
    diff_file_count: int = 0


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


class TurnRatingRequest(BaseModel):
    score: int = Field(ge=1, le=5, description="1～5 星")
    comment: str = Field(default="", max_length=200)


class TurnRatingResponse(BaseModel):
    ok: bool = True
    turn_id: str
    score: int
    label: str
    comment: str = ""
    revision: int = 1


class TurnDiffFile(BaseModel):
    path: str
    change_type: str
    diff_text: str = ""
    after_text: str = ""
    note: str = ""


class TurnDiffResponse(BaseModel):
    ok: bool = True
    turn_id: str
    rolled_back: bool = False
    file_count: int = 0
    overview_note: str = ""
    files: list[TurnDiffFile] = Field(default_factory=list)


def _session_or_404(request: Request, session_id: str) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


def _assert_turn_readable(
    request: Request,
    session_id: str,
    turn: dict[str, Any],
    user: AuthUser | None,
    *,
    deny_detail: str = "无权访问该回合",
) -> None:
    """回合可读性：同 session_id；或登录用户读取本人旧回合（会话重建后 path sid 可能已变）。"""
    turn_sid: str = str(turn.get("session_id") or "")
    owner = turn.get("user_id")
    live: SessionRecord | None = request.app.state.session_store.get(session_id)

    if turn_sid == session_id:
        if live is not None:
            assert_session_access(live, user)
        elif owner and (user is None or user.id != str(owner)):
            raise HTTPException(status_code=403, detail=deny_detail)
        return

    if not owner or user is None or user.id != str(owner):
        raise HTTPException(status_code=404, detail="turn not found")
    if live is not None:
        assert_session_access(live, user)


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
        else workspace_root_for_session(
            settings.workspace_dir, session_id, user_id=record.user_id
        )
    )
    if not workspace_root.is_dir():
        raise HTTPException(status_code=400, detail="workspace 尚未生成，请先完成制作")

    history_payload: list[dict[str, str]] = [
        {"role": t.role, "content": t.content} for t in body.history
    ]
    prev_rating: dict[str, Any] | None = None
    try:
        prev_rating = get_learning_store().get_previous_turn_user_rating(session_id)
    except Exception:  # noqa: BLE001
        prev_rating = None

    try:
        with get_agent_queue().acquire(
            session_id,
            user_id=record.user_id,
            max_concurrent=int(settings.max_concurrent_agents),
            wait_sec=float(settings.agent_queue_wait_sec),
        ):
            before_snap: dict[str, str] = snapshot_workspace_texts(workspace_root)
            try:
                result: dict[str, Any] = apply_nl_patch(
                    settings,
                    workspace_root,
                    settings.templates_dir,
                    genre,
                    body.text,
                    history=history_payload,
                    feedback=body.feedback,
                    previous_turn_user_rating=prev_rating,
                )
            except NlPatchError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except WorkspaceGuardError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            after_snap: dict[str, str] = snapshot_workspace_texts(workspace_root)
    except AgentQueueError as exc:
        status = 503 if exc.code == "agent_queue_full" else 429
        raise HTTPException(
            status_code=status,
            detail={
                "code": exc.code,
                "message": exc.message,
                "queue_size": exc.queue_size,
            },
        ) from exc

    rounds_raw = result.get("agent_rounds")
    try:
        rounds_n: int | None = int(rounds_raw) if rounds_raw is not None else None
    except (TypeError, ValueError):
        rounds_n = None

    summary_text: str = str(result.get("summary", ""))
    message_text: str = str(result.get("message", ""))
    how_to_play_list: list[str] = [str(x) for x in result.get("how_to_play", [])]
    turn_id: str = ""
    has_diff: bool = False
    diff_file_count: int = 0
    try:
        learning = get_learning_store()
        turn = learning.record_agent_turn(
            session_id=session_id,
            user_id=record.user_id,
            auth_mode=record.auth_mode or "guest",
            user_text=body.text,
            message=message_text,
            summary=summary_text,
            how_to_play=how_to_play_list,
            provider=str(result.get("provider", "stub")),
            gate_passed=bool(result.get("gate_passed")),
            partial=bool(result.get("partial")),
            rolled_back=bool(result.get("rolled_back")),
            goals=[str(x) for x in (result.get("goals") or []) if str(x).strip()],
            sandbox_files=[str(p) for p in result.get("sandbox_files", [])],
            genre=genre,
            display_name=record.display_name or "",
            creator_name=record.creator_name or "",
            workspace_key=str(workspace_root),
        )
        turn_id = turn.turn_id
        overview = compose_agent_reply_full(message_text, summary_text, how_to_play_list)
        diff_payload = compute_turn_diff(
            before_snap,
            after_snap,
            rolled_back=bool(result.get("rolled_back")),
            overview_note=overview,
        )
        learning.save_turn_diff(turn_id, diff_payload)
        diff_file_count = int(diff_payload.get("file_count") or 0)
        has_diff = True
    except Exception:  # noqa: BLE001 — 学情/Diff 失败不阻断改游戏主路径
        # NB-02：禁止静默吞掉；turn_id 可能仍为空，须落日志便于排查
        logger.exception(
            "nl-patch 学情/Diff 落库失败 · session_id=%s turn_id=%r has_diff=%s",
            session_id,
            turn_id,
            has_diff,
        )

    return NlPatchResponse(
        ok=bool(result.get("ok")),
        provider=str(result.get("provider", "stub")),
        summary=summary_text,
        message=message_text,
        changes=[NlPatchChange(**c) for c in result.get("changes", [])],
        sandbox_files=[str(p) for p in result.get("sandbox_files", [])],
        attempted_paths=[str(p) for p in (result.get("attempted_paths") or [])],
        how_to_play=how_to_play_list,
        applied_capabilities=[str(x) for x in result.get("applied_capabilities", [])],
        needs_relaunch=bool(result.get("needs_relaunch")),
        verify_gaps=[str(x) for x in result.get("verify_gaps", [])],
        repaired=bool(result.get("repaired")),
        llm_error=str(result.get("llm_error", "") or ""),
        learned_skills=[str(x) for x in result.get("learned_skills", [])],
        demoted_skills=[str(x) for x in result.get("demoted_skills", [])],
        gate_passed=bool(result.get("gate_passed")),
        partial=bool(result.get("partial")),
        rolled_back=bool(result.get("rolled_back")),
        express=bool(result.get("express")),
        agent_rounds=rounds_n,
        understanding=str(result.get("understanding", "") or ""),
        goals=[str(x) for x in (result.get("goals") or []) if str(x).strip()],
        turn_id=turn_id,
        has_diff=has_diff,
        diff_file_count=diff_file_count,
    )


@router.get(
    "/sessions/{session_id}/turns/{turn_id}/diff",
    response_model=TurnDiffResponse,
)
def get_turn_diff(
    session_id: str,
    turn_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> TurnDiffResponse:
    """F2 · 本轮真实 Diff（学情库，release 后仍可回看）。"""
    store = get_learning_store()
    turn = store.get_turn(turn_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="turn not found")
    _assert_turn_readable(
        request,
        session_id,
        turn,
        user,
        deny_detail="无权访问该回合 Diff",
    )
    payload = store.get_turn_diff(turn_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="diff not found")
    files = [
        TurnDiffFile(
            path=str(f.get("path", "")),
            change_type=str(f.get("change_type", "modified")),
            diff_text=str(f.get("diff_text", "")),
            after_text=str(f.get("after_text", "")),
            note=str(f.get("note", "")),
        )
        for f in (payload.get("files") or [])
        if isinstance(f, dict) and f.get("path")
    ]
    return TurnDiffResponse(
        turn_id=turn_id,
        rolled_back=bool(payload.get("rolled_back")),
        file_count=int(payload.get("file_count") or len(files)),
        overview_note=str(payload.get("overview_note") or ""),
        files=files,
    )


@router.get(
    "/sessions/{session_id}/turns/{turn_id}/rating",
    response_model=TurnRatingResponse,
)
def get_turn_rating(
    session_id: str,
    turn_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> TurnRatingResponse:
    """UH-4 · 读取本轮已提交评价（关闭弹层再进可回填）。"""
    record: SessionRecord = _session_or_404(request, session_id)
    assert_session_access(record, user)
    store = get_learning_store()
    turn = store.get_turn(turn_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="turn not found")
    _assert_turn_readable(request, session_id, turn, user)
    saved = store.get_rating(turn_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="rating not found")
    return TurnRatingResponse(
        turn_id=str(saved["turn_id"]),
        score=int(saved["score"]),
        label=str(saved["label"]),
        comment=str(saved.get("comment") or ""),
        revision=int(saved.get("revision") or 1),
    )


@router.post(
    "/sessions/{session_id}/turns/{turn_id}/rating",
    response_model=TurnRatingResponse,
)
def post_turn_rating(
    session_id: str,
    turn_id: str,
    body: TurnRatingRequest,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> TurnRatingResponse:
    """F3 · 本轮 1～5 星评价；可改评并留 revision。"""
    record: SessionRecord = _session_or_404(request, session_id)
    assert_session_access(record, user)
    if body.score not in RATING_LABELS:
        raise HTTPException(status_code=400, detail="score must be 1..5")
    store = get_learning_store()
    turn = store.get_turn(turn_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="turn not found")
    _assert_turn_readable(request, session_id, turn, user)
    try:
        saved = store.upsert_turn_rating(
            turn_id=turn_id,
            score=body.score,
            comment=body.comment,
            user_id=record.user_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="turn not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TurnRatingResponse(
        turn_id=saved["turn_id"],
        score=int(saved["score"]),
        label=str(saved["label"]),
        comment=str(saved["comment"]),
        revision=int(saved["revision"]),
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
        uid = record.user_id if record is not None else None
        workspace_root = workspace_root_for_session(
            settings.workspace_dir, session_id, user_id=uid
        )
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

    workspace_root: Path = workspace_root_for_session(
        settings.workspace_dir, session_id, user_id=record.user_id
    )
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
