from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.models.session import SessionRecord
from app.services.creative.analyzer import analyze_preset_only
from app.services.creative.code_map import build_code_map_preview
from app.services.creative.loader import get_name_suggestions, load_creative_template

router = APIRouter(tags=["creative"])


class NameSuggestionResponse(BaseModel):
    genre: str
    suggestions: list[str]


class CreativeAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class CreativeAnswersResponse(BaseModel):
    ok: bool
    session_id: str
    genre: str
    creative_answers: dict[str, Any]


class AnalyzeRequirementsResponse(BaseModel):
    resolutions: list[dict[str, Any]]
    llm_patch_required: bool
    code_map_preview: dict[str, Any]


def _load_template_or_404(genre: str) -> dict[str, Any]:
    try:
        return load_creative_template(genre)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _session_or_404(request: Request, session_id: str) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


def _validate_answers(template: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    question_map: dict[str, dict[str, Any]] = {
        str(q.get("id")): q for q in template.get("questions", []) if q.get("id")
    }
    normalized: dict[str, Any] = {}
    for qid, answer in answers.items():
        question: dict[str, Any] | None = question_map.get(str(qid))
        if question is None:
            raise HTTPException(status_code=400, detail=f"非法 question_id: {qid}")
        widget: str = str(question.get("widget", "single_choice"))
        if widget == "skill_pick":
            skill_ids: set[str] = {str(v) for v in question.get("skill_ids", [])}
            raw_values: list[str] = [str(answer)] if not isinstance(answer, list) else [str(v) for v in answer]
            for skill in raw_values:
                if skill and skill not in skill_ids:
                    raise HTTPException(status_code=400, detail=f"非法 skill_id: {skill}")
            normalized[str(qid)] = [skill for skill in raw_values if skill]
            continue

        option_ids: set[str] = {str(opt.get("id")) for opt in question.get("options", [])}
        option_id: str = str(answer).strip()
        if option_id not in option_ids:
            raise HTTPException(status_code=400, detail=f"非法 option_id: {qid}.{option_id}")
        normalized[str(qid)] = option_id
    return normalized


@router.get("/creative/templates/{genre}")
def get_creative_template(genre: str) -> dict[str, Any]:
    template: dict[str, Any] = _load_template_or_404(genre)
    return template


@router.get("/creative/name-suggestions", response_model=NameSuggestionResponse)
def get_creative_name_suggestions(genre: str = Query(...)) -> NameSuggestionResponse:
    _load_template_or_404(genre)
    return NameSuggestionResponse(genre=genre, suggestions=get_name_suggestions(genre))


@router.post("/sessions/{session_id}/creative/answers", response_model=CreativeAnswersResponse)
def submit_creative_answers(
    session_id: str,
    body: CreativeAnswersRequest,
    request: Request,
) -> CreativeAnswersResponse:
    record: SessionRecord = _session_or_404(request, session_id)
    genre: str = record.genre or str(record.payload.get("meta", {}).get("genre", "")).strip()
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成品类匹配")

    template: dict[str, Any] = _load_template_or_404(genre)
    normalized: dict[str, Any] = _validate_answers(template, body.answers)

    payload: dict[str, Any] = dict(record.payload)
    payload["creative_answers"] = normalized
    payload["edu_phase"] = "B5"
    record.payload = payload
    request.app.state.session_store.save(record)

    return CreativeAnswersResponse(
        ok=True,
        session_id=session_id,
        genre=genre,
        creative_answers=normalized,
    )


@router.post(
    "/sessions/{session_id}/analyze-requirements",
    response_model=AnalyzeRequirementsResponse,
)
def analyze_requirements(session_id: str, request: Request) -> AnalyzeRequirementsResponse:
    record: SessionRecord = _session_or_404(request, session_id)
    settings = request.app.state.settings
    genre: str = record.genre or str(record.payload.get("meta", {}).get("genre", "")).strip()
    if not genre:
        raise HTTPException(status_code=400, detail="请先完成品类匹配")
    answers: dict[str, Any] = dict(record.payload.get("creative_answers", {}))
    if not answers:
        raise HTTPException(status_code=400, detail="请先提交 creative_answers")

    try:
        result: dict[str, Any] = analyze_preset_only(genre, answers, settings.templates_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preview: dict[str, Any] = build_code_map_preview(genre, list(result.get("resolutions", [])))
    payload: dict[str, Any] = dict(record.payload)
    payload["analyze_result"] = result
    payload["code_map"] = preview
    payload["edu_phase"] = "B5"
    record.payload = payload
    request.app.state.session_store.save(record)

    return AnalyzeRequirementsResponse(
        resolutions=list(result.get("resolutions", [])),
        llm_patch_required=False,
        code_map_preview=preview,
    )
