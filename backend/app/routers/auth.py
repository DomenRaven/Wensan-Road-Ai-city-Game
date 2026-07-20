"""教学入口 · 开放注册 / 登录 / 登出 / me。"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.services.auth_deps import get_required_user
from app.services.auth_service import AuthError, login_user, logout_token, register_user
from app.services.auth_store import AuthUser

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str
    class_label: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    nickname: str
    role: Literal["student", "admin"]
    class_label: str = ""


class AuthTokenResponse(BaseModel):
    ok: bool = True
    token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    ok: bool = True
    user: UserPublic


def _public_user(user: AuthUser) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        role=user.role,  # type: ignore[arg-type]
        class_label=user.class_label,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=201)
def register(body: RegisterRequest) -> AuthTokenResponse:
    try:
        user = register_user(
            username=body.username,
            password=body.password,
            nickname=body.nickname,
            class_label=body.class_label,
        )
        logged_in, token = login_user(username=body.username, password=body.password)
    except AuthError as exc:
        detail: str = str(exc)
        status: int = 409 if "占用" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return AuthTokenResponse(token=token, user=_public_user(logged_in))


@router.post("/login", response_model=AuthTokenResponse)
def login(body: LoginRequest) -> AuthTokenResponse:
    try:
        user, token = login_user(username=body.username, password=body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthTokenResponse(token=token, user=_public_user(user))


@router.post("/logout")
def logout(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            logout_token(parts[1].strip())
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: Annotated[AuthUser, Depends(get_required_user)]) -> MeResponse:
    return MeResponse(user=_public_user(user))
