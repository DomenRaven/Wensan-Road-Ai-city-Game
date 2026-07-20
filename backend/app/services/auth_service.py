"""教学认证：密码哈希、字段校验、命名助手。"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from functools import lru_cache
from pathlib import Path

from app.config import Settings, get_settings
from app.services.auth_store import AuthStore, AuthUser, UserRole

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
_NICKNAME_RE = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9·]+$")
_NICKNAME_MAX = 8
_PASSWORD_MIN = 6
_PASSWORD_MAX = 64
_PBKDF2_ROUNDS = 120_000


class AuthError(ValueError):
    """认证业务错误（映射 400/401/409）。"""


def hash_password(password: str) -> str:
    salt: bytes = secrets.token_bytes(16)
    digest: bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ROUNDS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, rounds_s, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    try:
        rounds: int = int(rounds_s)
        salt: bytes = bytes.fromhex(salt_hex)
        expected: bytes = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual: bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        rounds,
    )
    return hmac.compare_digest(actual, expected)


def validate_username(username: str) -> str:
    value: str = username.strip()
    if not _USERNAME_RE.fullmatch(value):
        raise AuthError("用户名须为 3～32 位，仅字母、数字与下划线")
    return value


def validate_nickname(nickname: str) -> str:
    value: str = nickname.strip()
    if not value:
        raise AuthError("昵称不能为空")
    if len(value) > _NICKNAME_MAX:
        raise AuthError(f"昵称最多 {_NICKNAME_MAX} 个字")
    if not _NICKNAME_RE.fullmatch(value):
        raise AuthError("昵称仅支持中文、字母、数字与间隔号·")
    return value


def validate_password(password: str) -> str:
    if len(password) < _PASSWORD_MIN or len(password) > _PASSWORD_MAX:
        raise AuthError(f"密码长度须为 {_PASSWORD_MIN}～{_PASSWORD_MAX} 位")
    return password


def default_work_display_name(nickname: str, username: str, genre_display_name: str) -> str:
    """F4-N3：{nickname}（{username}）的{品类中文名}游戏"""
    genre: str = genre_display_name.strip() or "小"
    return f"{nickname}（{username}）的{genre}游戏"


@lru_cache
def get_auth_store() -> AuthStore:
    settings: Settings = get_settings()
    store: AuthStore = AuthStore(Path(settings.learning_analytics_dir) / "learning.db")
    admin_user: str = settings.bootstrap_admin_username.strip()
    admin_pass: str = settings.bootstrap_admin_password
    if admin_user and admin_pass:
        store.ensure_admin(
            username=admin_user,
            password_hash=hash_password(admin_pass),
            nickname=settings.bootstrap_admin_nickname.strip() or "管理员",
        )
    return store


def clear_auth_store_cache() -> None:
    get_auth_store.cache_clear()


def register_user(
    *,
    username: str,
    password: str,
    nickname: str,
    class_label: str = "",
    role: UserRole = "student",
) -> AuthUser:
    store: AuthStore = get_auth_store()
    uname: str = validate_username(username)
    nick: str = validate_nickname(nickname)
    pwd: str = validate_password(password)
    if role == "admin":
        raise AuthError("开放注册不可创建管理员账号")
    if store.get_by_username(uname) is not None:
        raise AuthError("用户名已被占用")
    return store.create_user(
        username=uname,
        password_hash=hash_password(pwd),
        nickname=nick,
        role=role,
        class_label=class_label.strip()[:32],
    )


def login_user(*, username: str, password: str) -> tuple[AuthUser, str]:
    store: AuthStore = get_auth_store()
    settings: Settings = get_settings()
    uname: str = username.strip()
    if not uname or not password:
        raise AuthError("用户名或密码错误")
    encoded: str | None = store.get_password_hash(uname)
    if encoded is None or not verify_password(password, encoded):
        raise AuthError("用户名或密码错误")
    user: AuthUser | None = store.get_by_username(uname)
    if user is None:
        raise AuthError("用户名或密码错误")
    token: str = store.issue_token(user.id, settings.auth_token_ttl_sec)
    return user, token


def logout_token(token: str) -> None:
    get_auth_store().revoke_token(token)


def user_from_token(token: str) -> AuthUser | None:
    return get_auth_store().resolve_token(token)
