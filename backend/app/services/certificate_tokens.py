"""证书公网扫码下载 · 短期 token 映射（不暴露 session_id）。"""

from __future__ import annotations

import json
import re
import secrets
import time
from pathlib import Path
from typing import Any

from app.services.workspace_guard import WorkspaceGuardError, assert_under_workspace, ensure_workspace_root

_TOKEN_DIR_NAME = ".cert_tokens"
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


class CertificateTokenError(ValueError):
    """证书 token 读写或校验失败。"""


def _tokens_dir(workspace_dir: Path) -> Path:
    root: Path = ensure_workspace_root(workspace_dir)
    target: Path = root / _TOKEN_DIR_NAME
    resolved: Path = assert_under_workspace(target, root)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _token_path(workspace_dir: Path, token: str) -> Path:
    if not _TOKEN_PATTERN.fullmatch(token):
        raise CertificateTokenError(f"非法 certificate token: {token!r}")
    root: Path = ensure_workspace_root(workspace_dir)
    target: Path = _tokens_dir(workspace_dir) / f"{token}.json"
    return assert_under_workspace(target, root)


def _safe_filename(display_name: str) -> str:
    safe: str = re.sub(r'[\\/:*?"<>|]', "_", display_name.strip())[:40]
    return safe or "证书"


def issue_token(
    workspace_dir: Path,
    session_id: str,
    display_name: str,
    ttl_sec: int,
    *,
    user_id: str | None = None,
) -> tuple[str, float]:
    """签发 token 并写入映射文件。返回 (token, expires_at)。"""
    token: str = secrets.token_urlsafe(18)
    expires_at: float = time.time() + max(300, ttl_sec)
    payload: dict[str, Any] = {
        "session_id": session_id,
        "user_id": user_id,
        "filename": f"{_safe_filename(display_name)}_证书.png",
        "expires_at": expires_at,
        "created_at": time.time(),
    }
    path: Path = _token_path(workspace_dir, token)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return token, expires_at


def resolve_token(workspace_dir: Path, token: str) -> dict[str, Any]:
    """解析 token；过期则删除并抛错。"""
    path: Path = _token_path(workspace_dir, token)
    if not path.is_file():
        raise CertificateTokenError("certificate token not found")

    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CertificateTokenError("certificate token corrupt") from exc

    expires_at: float = float(data.get("expires_at", 0))
    if expires_at < time.time():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise CertificateTokenError("certificate download link expired")

    session_id: str = str(data.get("session_id", "")).strip()
    if not session_id:
        raise CertificateTokenError("certificate token missing session")

    return data


def build_public_download_url(public_api_base: str, token: str) -> str:
    base: str = public_api_base.strip().rstrip("/")
    if not base:
        return f"/public/certificates/{token}"
    return f"{base}/public/certificates/{token}"


def revoke_tokens_for_session(workspace_dir: Path, session_id: str) -> int:
    """会话释放时清理该 session 的全部证书 token。"""
    try:
        token_dir: Path = _tokens_dir(workspace_dir)
    except WorkspaceGuardError:
        return 0

    removed = 0
    for path in token_dir.glob("*.json"):
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if str(data.get("session_id", "")) == session_id:
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
    return removed
