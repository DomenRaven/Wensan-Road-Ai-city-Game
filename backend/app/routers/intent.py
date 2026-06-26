from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.models.session import SessionRecord
from app.services.creative.loader import load_intent_lexicon
from app.services.workspace_guard import load_featured_genre_slugs

router = APIRouter(prefix="/intent", tags=["intent"])


class IntentMatchRequest(BaseModel):
    text: str
    session_id: str


class IntentMatchResponse(BaseModel):
    matched_genre: str
    confidence: float
    reply_text: str
    candidates: list[str]


def _token_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for token in keywords if token and token in text)


def _default_reply(genre: str) -> str:
    fallback: dict[str, str] = {
        "platformer": "听起来你想玩横版闯关！",
        "shmup": "听起来你想玩飞机射击！",
        "survivor": "听起来你想玩割草打怪！",
        "pingpong": "听起来你想玩乒乓球！",
        "fighting": "听起来你想玩横版格斗！",
        "parkour": "听起来你想玩跑酷！",
        "racing": "听起来你想玩欢乐赛车！",
    }
    return fallback.get(genre, "听起来很有趣，我们来做这个游戏吧！")


@router.post("/match-genre", response_model=IntentMatchResponse)
def match_genre(body: IntentMatchRequest, request: Request) -> IntentMatchResponse:
    text: str = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    if len(text) > 80:
        raise HTTPException(status_code=400, detail="text 长度不能超过 80")

    store = request.app.state.session_store
    record: SessionRecord | None = store.get(body.session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        lexicon: dict[str, Any] = load_intent_lexicon()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="intent lexicon 未配置") from exc

    featured: list[str] = load_featured_genre_slugs()
    genre_doc: dict[str, Any] = lexicon.get("genres", {})
    tie_break: list[str] = [str(v) for v in lexicon.get("tie_break", featured)]
    tie_rank: dict[str, int] = {slug: idx for idx, slug in enumerate(tie_break)}

    score_map: dict[str, float] = {slug: 0.0 for slug in featured}
    for slug in featured:
        spec: Any = genre_doc.get(slug, {})
        if not isinstance(spec, dict):
            continue
        keywords: list[str] = [str(v) for v in spec.get("keywords", [])]
        weight: float = float(spec.get("weight", 1.0))
        score_map[slug] += float(_token_hits(text, keywords)) * weight

    ranked: list[str] = sorted(
        featured,
        key=lambda slug: (-score_map.get(slug, 0.0), tie_rank.get(slug, 999)),
    )
    best: str = ranked[0] if ranked else "platformer"
    best_score: float = score_map.get(best, 0.0)
    total_score: float = sum(score_map.values())
    confidence: float = 0.0 if total_score <= 0 else best_score / (total_score + 1e-6)
    confidence = max(0.0, min(1.0, confidence))

    best_spec: Any = genre_doc.get(best, {})
    if isinstance(best_spec, dict):
        reply_text = str(
            best_spec.get("reply_text")
            or best_spec.get("reply_template")
            or _default_reply(best)
        )
    else:
        reply_text = _default_reply(best)
    if confidence < 0.6:
        reply_text = f"{reply_text} 我们也可以换别的哦。"

    payload: dict[str, Any] = dict(record.payload)
    payload["intent_raw"] = text
    payload["edu_phase"] = "B2"
    payload["intent_match"] = {"matched_genre": best, "confidence": confidence}
    payload["meta"] = payload.get("meta", {})
    payload["meta"]["genre"] = best
    record.genre = best
    record.payload = payload
    store.save(record)

    return IntentMatchResponse(
        matched_genre=best,
        confidence=round(confidence, 4),
        reply_text=reply_text,
        candidates=[],
    )
