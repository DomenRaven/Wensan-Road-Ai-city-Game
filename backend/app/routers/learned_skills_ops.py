"""讲解员运维：Learned Skill 长期库（清空 / 检索 / 导出导入提案）。

本机接口；不自动改 templates/** 或官方 optional_skills.json。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services.creative.learned_skills import (
    LearnedSkillsError,
    clear_learned_skills,
    ensure_store,
    export_experience_pack,
    import_experience_pack,
    promote_learned_skill_to_proposal,
    search_learned_skills,
)

router = APIRouter(prefix="/ops/learned-skills", tags=["learned-skills-ops"])


class ClearRequest(BaseModel):
    keep_experiences: bool = False
    confirm: str = Field(default="", description="必须为 CLEAR 才执行清空")


class ImportRequest(BaseModel):
    zip_path: str = Field(description="本机绝对或相对路径的经验包 zip")


class PromoteRequest(BaseModel):
    skill_id: str
    out_path: str = ""


class SearchResponse(BaseModel):
    ok: bool = True
    hits: list[dict[str, Any]]


@router.get("", response_model=dict)
def list_store(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    root: Path = ensure_store(settings.learned_skills_dir)
    index: Path = root / "index.jsonl"
    skills: list[dict[str, Any]] = []
    if index.is_file():
        for line in index.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                skills.append(obj)
    return {
        "ok": True,
        "store_dir": str(root),
        "skill_count": len(skills),
        "skills": skills[:200],
    }


@router.get("/search", response_model=SearchResponse)
def search_store(
    request: Request,
    q: str = Query(default=""),
    genre: str = Query(default="platformer"),
    k: int = Query(default=5, ge=1, le=20),
) -> SearchResponse:
    settings = request.app.state.settings
    hits = search_learned_skills(settings.learned_skills_dir, q, genre, k=k)
    return SearchResponse(ok=True, hits=hits)


@router.post("/clear")
def clear_store(body: ClearRequest, request: Request) -> dict[str, Any]:
    if body.confirm.strip() != "CLEAR":
        raise HTTPException(
            status_code=400,
            detail="请传 confirm=CLEAR 以确认清空经验库",
        )
    settings = request.app.state.settings
    return clear_learned_skills(
        settings.learned_skills_dir, keep_experiences=body.keep_experiences
    )


@router.post("/export")
def export_pack(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    out: Path = settings.learned_skills_dir / "exports" / "learned_skills_pack.zip"
    path = export_experience_pack(settings.learned_skills_dir, out)
    return {"ok": True, "zip_path": str(path)}


@router.post("/import")
def import_pack(body: ImportRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    zip_path: Path = Path(body.zip_path)
    if not zip_path.is_absolute():
        zip_path = (Path.cwd() / zip_path).resolve()
    try:
        return import_experience_pack(settings.learned_skills_dir, zip_path)
    except LearnedSkillsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/promote")
def promote_skill(body: PromoteRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    out: Path
    if body.out_path.strip():
        out = Path(body.out_path)
        if not out.is_absolute():
            out = (Path.cwd() / out).resolve()
    else:
        out = (
            settings.learned_skills_dir
            / "proposals"
            / f"{body.skill_id}_optional_skills_proposal.json"
        )
    try:
        path = promote_learned_skill_to_proposal(
            settings.learned_skills_dir, body.skill_id, out
        )
    except LearnedSkillsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "proposal_path": str(path),
        "note": "请人工审核后手工合并到 config/optional_skills.json；不会自动改 templates",
    }
