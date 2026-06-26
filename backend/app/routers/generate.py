from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.models.session import SessionPhase, SessionRecord
from app.services.config_builder import build_game_config
from app.services.creative.analyzer import apply_resolutions_to_config
from app.services.creative.code_map import build_code_map_for_workspace
from app.services.edu_workspace import apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace
from app.services.workspace_guard import (
    WorkspaceGuardError,
    assert_not_under_templates,
    assert_under_workspace,
    validate_session_id,
)

router = APIRouter(tags=["generate"])


class GenerateResponseV1(BaseModel):
    ok: bool
    workspace_path: str
    config_path: str
    genre: str
    message: str | None = None


def _validate_recap_confirmed(record: SessionRecord) -> None:
    if not record.payload.get("recap_confirmed"):
        raise HTTPException(
            status_code=400,
            detail="请先完成 ★R 配方确认 (POST /sessions/{id}/wizard/R)",
        )


def _validate_genre(record: SessionRecord) -> str:
    genre: str = record.genre or str(record.payload.get("meta", {}).get("genre", "")).strip()
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成 S1 选择品类")
    return genre


class GenerateResponseV2(BaseModel):
    ok: bool
    workspace_path: str
    config_path: str
    code_map: dict[str, Any]
    genre: str


def _workspace_config_path(workspace_root: Path) -> Path:
    return workspace_root / "config" / "game_config.json"


@router.post("/sessions/{session_id}/generate", response_model=GenerateResponseV1)
def generate_session_workspace(session_id: str, request: Request) -> GenerateResponseV1:
    """B1: copy templates/{genre}/ → workspace/{session_id}/ and merge game_config (B2+B3)."""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _validate_recap_confirmed(record)
    genre: str = _validate_genre(record)

    try:
        workspace_root = copy_template_to_workspace(
            settings.templates_dir,
            settings.workspace_dir,
            genre,
            session_id,
        )
        config_path = build_game_config(
            session_id,
            record.payload,
            genre,
            workspace_root,
            settings.templates_dir,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"workspace 复制失败: {exc}") from exc

    record.phase = SessionPhase.PLAY
    record.wizard_step = "S8"
    payload: dict[str, Any] = dict(record.payload)
    payload["generate_completed"] = True
    payload["workspace_path"] = str(workspace_root)
    record.payload = payload
    store.save(record)

    return GenerateResponseV1(
        ok=True,
        workspace_path=str(workspace_root),
        config_path=str(config_path),
        genre=genre,
        message="workspace 已生成，可试玩",
    )


@router.post("/sessions/{session_id}/generate/v2", response_model=GenerateResponseV2)
def generate_session_workspace_v2(session_id: str, request: Request) -> GenerateResponseV2:
    """B 链教育版 P0: creative_answers + analyze_result 驱动的 preset-only 生成。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    genre: str = _validate_genre(record)
    answers: dict[str, Any] = dict(record.payload.get("creative_answers", {}))
    if not answers:
        raise HTTPException(status_code=400, detail="请先提交 creative_answers")

    analyze_result: dict[str, Any] = dict(record.payload.get("analyze_result", {}))
    resolutions: list[dict[str, Any]] = list(analyze_result.get("resolutions", []))
    if not resolutions:
        raise HTTPException(status_code=400, detail="请先完成 analyze-requirements")

    try:
        workspace_root = copy_template_to_workspace(
            settings.templates_dir,
            settings.workspace_dir,
            genre,
            session_id,
        )
        config_path: Path = _workspace_config_path(workspace_root)
        base_config_path: Path = settings.templates_dir / genre / "config" / "game_config.json"
        base_config: dict[str, Any] = json.loads(base_config_path.read_text(encoding="utf-8"))
        workspace_config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        merged: dict[str, Any] = apply_resolutions_to_config(workspace_config, base_config, resolutions)
        merged.setdefault("meta", {})
        merged["meta"]["session_id"] = session_id
        merged["meta"]["genre"] = genre
        if record.display_name:
            merged["meta"]["display_name"] = record.display_name[:32]
            merged.setdefault("theme", {})
            merged["theme"]["title"] = record.display_name[:32]

        resolved_workspace = assert_under_workspace(config_path, settings.workspace_dir.resolve())
        assert_not_under_templates(resolved_workspace, settings.templates_dir.resolve())
        resolved_workspace.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        code_map: dict[str, Any] = build_code_map_for_workspace(workspace_root, genre, resolutions)
        edu_applied: bool = apply_edu_workspace_patch(
            workspace_root,
            genre,
            settings.templates_dir,
            settings.workspace_dir,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"workspace 生成失败: {exc}") from exc

    payload: dict[str, Any] = dict(record.payload)
    payload["generate_completed"] = True
    payload["workspace_path"] = str(workspace_root)
    payload["code_map"] = code_map
    payload["edu_bridge_applied"] = edu_applied
    payload["edu_phase"] = "B6"
    record.payload = payload
    record.phase = SessionPhase.PLAY
    record.wizard_step = "S8"
    store.save(record)

    return GenerateResponseV2(
        ok=True,
        workspace_path=str(workspace_root),
        config_path=str(config_path.resolve()),
        code_map=code_map,
        genre=genre,
    )
