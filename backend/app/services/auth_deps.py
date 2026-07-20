"""FastAPI 鉴权依赖 · 游客会话放行，登录会话校验归属。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Request

from app.models.session import SessionRecord
from app.services.auth_service import user_from_token
from app.services.auth_store import AuthUser


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts: list[str] = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser | None:
    token: str = _extract_bearer(authorization)
    if not token:
        return None
    return user_from_token(token)


def get_required_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    user: AuthUser | None = get_optional_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def assert_session_access(
    record: SessionRecord,
    user: AuthUser | None,
) -> None:
    """登录会话必须由本人 Token 访问；游客会话保持现网（持 session_id 即可）。"""
    if not record.user_id:
        return
    if user is None or user.id != record.user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")


def require_session(
    request: Request,
    session_id: str,
    user: AuthUser | None,
) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)
    return record
