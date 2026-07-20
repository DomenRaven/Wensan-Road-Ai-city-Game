from __future__ import annotations

import asyncio
import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import CONFIG_DIR
from app.models.session import SessionCreateResponse, SessionListResponse, SessionPhase, SessionRecord
from app.services.ai_sandbox import destroy_ai_sandbox
from app.services.auth_deps import assert_session_access, get_optional_user
from app.services.auth_store import AuthUser
from app.services.creative.learned_skills import harvest_session_experience
from app.services.learning_analytics import get_learning_store
from app.services.certificate_relay import (
    cleanup_relay_meta,
    is_publicly_reachable_url,
    save_relay_meta,
    upload_certificate_relay,
)
from app.services.certificate_tokens import build_public_download_url, issue_token, revoke_tokens_for_session
from app.services.godot_launcher import get_launcher
from app.services.workspace import workspace_config_path
from app.services.workspace_guard import (
    WorkspaceGuardError,
    assert_under_workspace,
    remove_workspace,
    validate_session_id,
    workspace_root_for_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class WorkspaceGameConfigResponse(BaseModel):
    ok: bool
    genre: str
    content: str
    path: str


class WorkspaceFileResponse(BaseModel):
    ok: bool
    content: str
    path: str
    truncated: bool = False
    annotation: str = ""


class WorkspaceTreeResponse(BaseModel):
    ok: bool
    session_id: str
    tree: list[dict[str, Any]]


class SessionPatchRequest(BaseModel):
    creator_name: str | None = None
    display_name: str | None = None


class SessionCreateRequest(BaseModel):
    auth_mode: Literal["guest", "login"] = "guest"


class CertificateUploadResponse(BaseModel):
    ok: bool
    download_token: str
    download_path: str
    download_url: str
    expires_in_sec: int
    relay_provider: str | None = None
    public_reachable: bool = False


_CERTIFICATE_MAX_BYTES = 5 * 1024 * 1024
_CERTIFICATE_REL_PATH = "certificate.png"


_CREATOR_NAME_MAX = 8
_CREATOR_NAME_PATTERN = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9·]+$")


def _validate_creator_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(status_code=400, detail="creator_name is required")
    if len(name) > _CREATOR_NAME_MAX:
        raise HTTPException(status_code=400, detail=f"creator_name must be at most {_CREATOR_NAME_MAX} characters")
    if not _CREATOR_NAME_PATTERN.match(name):
        raise HTTPException(status_code=400, detail="creator_name contains invalid characters")
    return name


_WORKSPACE_FILE_PREFIXES: tuple[str, ...] = ("config/", "core/", "scenes/")
_WORKSPACE_TREE_PREFIXES: tuple[str, ...] = (
    "config/",
    "core/",
    "scenes/",
    "assets/",
    "ai_sandbox/",
)
_WORKSPACE_HIDDEN_NAMES: frozenset[str] = frozenset(
    {
        ".agent_progress.json",
        ".session_ai_log.jsonl",
        "certificate.png",
        ".cert_tokens",
    }
)
_WORKSPACE_TEXT_SUFFIXES: tuple[str, ...] = (
    ".gd",
    ".tscn",
    ".json",
    ".md",
    ".txt",
    ".cfg",
    ".tres",
    ".godot",
)
_WORKSPACE_FILE_MAX_CHARS = 200_000


def _workspace_root(settings: Any, record: SessionRecord) -> Path:
    return workspace_root_for_session(
        settings.workspace_dir,
        record.session_id,
        user_id=record.user_id,
    )


def _normalize_rel_path(rel_path: str) -> str:
    rel: str = rel_path.strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise WorkspaceGuardError(f"非法 workspace 相对路径: {rel_path!r}")
    return rel


def _resolve_workspace_relative_file(
    workspace_root: Path,
    workspace_dir: Path,
    rel_path: str,
) -> Path:
    rel: str = _normalize_rel_path(rel_path)
    if rel in _WORKSPACE_HIDDEN_NAMES or any(
        part.startswith(".") for part in rel.split("/")
    ):
        raise WorkspaceGuardError(f"拒绝读取内部文件: {rel_path!r}")
    if rel.startswith("assets/"):
        raise WorkspaceGuardError("assets/ 文件仅可在目录树中列出，不支持预览正文")
    if not rel.startswith(_WORKSPACE_FILE_PREFIXES):
        raise WorkspaceGuardError(
            f"仅允许读取 config/、core/ 或 scenes/ 下文件: {rel_path!r}"
        )
    target: Path = workspace_root / rel
    resolved: Path = assert_under_workspace(target, workspace_dir.resolve())
    if not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"workspace 中未找到文件: {rel}",
        )
    return resolved


def _lookup_code_annotation(genre: str, rel_path: str) -> str:
    """文件级导读：品类表 → _default → 空（前端显示暂无说明）。"""
    candidates: list[Path] = []
    slug = (genre or "").strip()
    if slug:
        candidates.append(CONFIG_DIR / "code_annotations" / f"{slug}.json")
    candidates.append(CONFIG_DIR / "code_annotations" / "_default.json")
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and rel_path in data:
            return str(data[rel_path] or "").strip()
        files = data.get("files") if isinstance(data, dict) else None
        if isinstance(files, dict) and rel_path in files:
            return str(files[rel_path] or "").strip()
    return ""


def _build_workspace_tree(workspace_root: Path) -> list[dict[str, Any]]:
    """返回嵌套目录树（教学浏览用）；assets 可列不可预览。"""
    root = workspace_root.resolve()

    def walk(dir_path: Path, prefix: str) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        try:
            children = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return nodes
        for child in children:
            name = child.name
            if name in _WORKSPACE_HIDDEN_NAMES or name.startswith("."):
                continue
            rel = f"{prefix}{name}" if not prefix else f"{prefix.rstrip('/')}/{name}"
            if child.is_dir():
                # 仅展开白名单顶层及其子树
                if prefix == "" and f"{name}/" not in _WORKSPACE_TREE_PREFIXES:
                    continue
                nodes.append(
                    {
                        "name": name,
                        "path": rel,
                        "type": "dir",
                        "children": walk(child, rel + "/"),
                    }
                )
            elif child.is_file():
                if prefix == "" and name != "project.godot":
                    continue
                previewable = (
                    any(name.lower().endswith(suf) for suf in _WORKSPACE_TEXT_SUFFIXES)
                    and not rel.startswith("assets/")
                    and rel.startswith(_WORKSPACE_FILE_PREFIXES)
                )
                nodes.append(
                    {
                        "name": name,
                        "path": rel,
                        "type": "file",
                        "previewable": previewable,
                    }
                )
        return nodes

    tree: list[dict[str, Any]] = []
    # 顶层：project.godot + 白名单目录
    godot = root / "project.godot"
    if godot.is_file():
        tree.append(
            {
                "name": "project.godot",
                "path": "project.godot",
                "type": "file",
                "previewable": False,
            }
        )
    for prefix in _WORKSPACE_TREE_PREFIXES:
        folder = root / prefix.rstrip("/")
        if folder.is_dir():
            tree.append(
                {
                    "name": prefix.rstrip("/"),
                    "path": prefix.rstrip("/"),
                    "type": "dir",
                    "children": walk(folder, prefix),
                }
            )
    return tree


@router.post("", response_model=SessionCreateResponse, status_code=201)
def create_session(
    request: Request,
    body: SessionCreateRequest = Body(default_factory=SessionCreateRequest),
    user: AuthUser | None = Depends(get_optional_user),
) -> SessionCreateResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    auth_mode: str = body.auth_mode
    taken_over: str | None = None

    creator_name: str = ""
    bind_user_id: str | None = None
    if auth_mode == "login":
        if user is None:
            raise HTTPException(status_code=401, detail="登录模式须先登录")
        bind_user_id = user.id
        creator_name = user.nickname
        existing: SessionRecord | None = store.find_by_user_id(user.id)
        if existing is not None:
            taken_over = existing.session_id
            _teardown_session(existing.session_id, request, harvest=False)
    else:
        # 游客：即使带 Token 也不绑定账号（两线并行）
        bind_user_id = None

    record: SessionRecord | None = store.create(
        user_id=bind_user_id,
        auth_mode="login" if bind_user_id else "guest",
        creator_name=creator_name,
    )
    if record is None:
        raise HTTPException(
            status_code=429,
            detail=f"Session pool full (max {settings.max_sessions})",
        )
    try:
        get_learning_store().ensure_play_session(
            session_id=record.session_id,
            user_id=record.user_id,
            auth_mode=record.auth_mode,
            creator_name=record.creator_name,
        )
    except Exception:  # noqa: BLE001
        pass
    return SessionCreateResponse(
        session_id=record.session_id,
        phase=record.phase,
        wizard_step=record.wizard_step,
        queue_position=0,
        auth_mode=record.auth_mode,
        user_id=record.user_id,
        creator_name=record.creator_name,
        taken_over_session_id=taken_over,
    )


@router.get("", response_model=SessionListResponse)
def list_sessions(request: Request) -> SessionListResponse:
    store = request.app.state.session_store
    settings = request.app.state.settings
    sessions: list[SessionRecord] = store.list_active()
    return SessionListResponse(
        active_count=len(sessions),
        max_sessions=settings.max_sessions,
        sessions=sessions,
    )


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(
    session_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)
    return record


@router.patch("/{session_id}", response_model=SessionRecord)
def patch_session(
    session_id: str,
    body: SessionPatchRequest,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)

    payload: dict[str, Any] = dict(record.payload)
    meta: dict[str, Any] = dict(payload.get("meta", {}))

    if body.creator_name is not None:
        # 登录模式锁定创作者名为注册昵称，禁止改成他人名
        if record.auth_mode == "login" and record.user_id:
            if user is None or body.creator_name.strip() != user.nickname:
                raise HTTPException(status_code=400, detail="登录模式创作者名已锁定为昵称")
            record.creator_name = user.nickname
        else:
            record.creator_name = _validate_creator_name(body.creator_name)
        meta["creator_name"] = record.creator_name

    if body.display_name is not None:
        name = body.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="display_name is required")
        record.display_name = name[:48]
        meta["display_name"] = record.display_name

    payload["meta"] = meta
    record.payload = payload
    store.save(record)
    return record


def _teardown_session(
    session_id: str,
    request: Request,
    *,
    harvest: bool,
) -> dict[str, Any]:
    """销毁会话与 workspace。

    harvest=True：讲解员主动回主页/结束 → 可入库有效 Learned Skill。
    harvest=False：刷新/关页/异常退出/陈旧会话清理 → 只清盘，禁止写 learned_skills。
    """
    store = request.app.state.session_store
    settings = request.app.state.settings
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    genre: str = (
        record.genre
        or str(record.payload.get("meta", {}).get("genre", "")).strip()
        or "unknown"
    )
    display_name: str = (record.display_name or "").strip()
    harvest_result: dict[str, Any] = {
        "ok": True,
        "skipped": True,
        "reason": "harvest_disabled" if not harvest else "no_workspace",
    }
    try:
        workspace_root: Path = _workspace_root(settings, record)
        if workspace_root.is_dir() and harvest:
            harvest_result = harvest_session_experience(
                settings.learned_skills_dir,
                session_id,
                workspace_root,
                genre,
                display_name=display_name,
            )
        elif workspace_root.is_dir() and not harvest:
            harvest_result = {
                "ok": True,
                "skipped": True,
                "reason": "abnormal_exit_no_harvest",
            }
    except Exception:  # noqa: BLE001 — harvest 失败不阻断销毁
        harvest_result = {"ok": False, "skipped": True, "reason": "harvest_error"}

    owner_user_id: str | None = record.user_id
    # 学情长期保留：仅标记 ended，禁止随 release 删库
    try:
        get_learning_store().mark_play_session_ended(session_id)
    except Exception:  # noqa: BLE001
        pass
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    revoke_tokens_for_session(settings.workspace_dir, session_id)
    get_launcher(settings).clear_session(session_id)
    try:
        workspace_root = workspace_root_for_session(
            settings.workspace_dir, session_id, user_id=owner_user_id
        )
        cleanup_relay_meta(workspace_root)
        destroy_ai_sandbox(workspace_root)
    except WorkspaceGuardError:
        pass
    workspace_removed: bool = remove_workspace(
        settings.workspace_dir, session_id, user_id=owner_user_id
    )
    return {
        "deleted": True,
        "workspace_removed": workspace_removed,
        "harvest": harvest_result,
        "harvest_requested": harvest,
    }


@router.delete("/{session_id}")
def reset_session(
    session_id: str,
    request: Request,
    harvest: bool = True,
) -> dict[str, Any]:
    """主动重置/结束：默认 harvest=True（有效经验可入库），再销毁 workspace。"""
    return _teardown_session(session_id, request, harvest=harvest)


@router.post("/{session_id}/release")
def release_session(
    session_id: str,
    request: Request,
    harvest: bool = False,
) -> dict[str, Any]:
    """释放会话。

    默认 harvest=False：pagehide/刷新/sendBeacon/陈旧清理 → 只删 workspace，不写 Skill。
    讲解员点「回主页/重新开始」应显式 `?harvest=true`。
    """
    return _teardown_session(session_id, request, harvest=harvest)


@router.get("/{session_id}/workspace/game-config", response_model=WorkspaceGameConfigResponse)
def get_workspace_game_config(
    session_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> WorkspaceGameConfigResponse:
    """E-P0-17: 只读返回 workspace/.../config/game_config.json 全文。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path = _workspace_root(settings, record)
    config_path: Path = workspace_config_path(workspace_root)
    try:
        resolved: Path = assert_under_workspace(config_path, settings.workspace_dir.resolve())
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"workspace 中未找到 game_config.json: {resolved}",
        )

    content: str = resolved.read_text(encoding="utf-8")
    genre: str = record.genre or ""
    try:
        parsed: dict[str, Any] = json.loads(content)
        meta: dict[str, Any] = parsed.get("meta", {})
        if isinstance(meta, dict) and meta.get("genre"):
            genre = str(meta["genre"])
    except json.JSONDecodeError:
        pass
    if not genre:
        genre = str(record.payload.get("meta", {}).get("genre", "")).strip()

    rel_path: str = "config/game_config.json"
    return WorkspaceGameConfigResponse(
        ok=True,
        genre=genre,
        content=content,
        path=rel_path,
    )


@router.get("/{session_id}/workspace/tree", response_model=WorkspaceTreeResponse)
def get_workspace_tree(
    session_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> WorkspaceTreeResponse:
    """F1 · 真实工作区目录树（含 scenes/；assets 可列不可预览）。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)
    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path = _workspace_root(settings, record)
    if not workspace_root.is_dir():
        raise HTTPException(status_code=404, detail="workspace 尚未生成")
    return WorkspaceTreeResponse(
        ok=True,
        session_id=session_id,
        tree=_build_workspace_tree(workspace_root),
    )


@router.get("/{session_id}/workspace/file", response_model=WorkspaceFileResponse)
def get_workspace_file(
    session_id: str,
    request: Request,
    rel_path: str,
    user: AuthUser | None = Depends(get_optional_user),
) -> WorkspaceFileResponse:
    """只读返回 workspace 下 config/、core/ 或 scenes/ 内单个源文件。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspace_root: Path = _workspace_root(settings, record)
    try:
        resolved: Path = _resolve_workspace_relative_file(
            workspace_root,
            settings.workspace_dir.resolve(),
            rel_path,
        )
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        content: str = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="该文件不是可读文本") from exc
    truncated = False
    if len(content) > _WORKSPACE_FILE_MAX_CHARS:
        content = content[:_WORKSPACE_FILE_MAX_CHARS]
        truncated = True
    normalized: str = _normalize_rel_path(rel_path)
    annotation = _lookup_code_annotation(record.genre or "", normalized)
    return WorkspaceFileResponse(
        ok=True,
        content=content,
        path=normalized,
        truncated=truncated,
        annotation=annotation,
    )


def _certificate_path(session_id: str, workspace_dir: Path, *, user_id: str | None = None) -> Path:
    workspace_root: Path = workspace_root_for_session(workspace_dir, session_id, user_id=user_id)
    target: Path = workspace_root / _CERTIFICATE_REL_PATH
    return assert_under_workspace(target, workspace_dir.resolve())


@router.put("/{session_id}/certificate", response_model=CertificateUploadResponse)
async def upload_certificate(
    session_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> CertificateUploadResponse:
    """展厅扫码下载：暂存 PNG 至会话 workspace/certificate.png。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    body: bytes = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty certificate body")
    if len(body) > _CERTIFICATE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="certificate too large")
    if not body.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="PNG required")

    cert_path: Path = _certificate_path(
        session_id, settings.workspace_dir, user_id=record.user_id
    )
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_bytes(body)

    # F1 门闩：证书 PNG 写入成功即视为保存成功
    payload_cert: dict[str, Any] = dict(record.payload)
    payload_cert["certificate_saved"] = True
    record.payload = payload_cert
    store.save(record)

    display_name: str = (record.display_name or "证书").strip() or "证书"
    token, expires_at = issue_token(
        settings.workspace_dir,
        session_id,
        display_name,
        settings.certificate_download_ttl_sec,
        user_id=record.user_id,
    )

    expires_in_sec: int = max(0, int(expires_at - time.time()))
    public_base: str = settings.public_api_base.strip()
    download_path: str = f"/public/certificates/{token}"
    download_url: str = build_public_download_url(public_base, token)
    relay_provider: str | None = None

    # 无自有公网时：中继到临时图床（线程池，避免堵住事件循环）
    if not public_base and settings.certificate_relay_enabled:
        try:
            relay = await asyncio.to_thread(
                upload_certificate_relay,
                body,
                f"{display_name}_证书.png",
            )
            download_url = relay.url
            expires_in_sec = (
                min(expires_in_sec, relay.ttl_sec) if expires_in_sec > 0 else relay.ttl_sec
            )
            relay_provider = relay.provider
            save_relay_meta(cert_path.parent, relay)
        except Exception:  # noqa: BLE001
            relay_provider = None

    public_reachable = bool(public_base) or is_publicly_reachable_url(download_url)

    return CertificateUploadResponse(
        ok=True,
        download_token=token,
        download_path=download_path,
        download_url=download_url,
        expires_in_sec=expires_in_sec,
        relay_provider=relay_provider,
        public_reachable=public_reachable,
    )


@router.get("/{session_id}/certificate/download")
def download_certificate(
    session_id: str,
    request: Request,
    user: AuthUser | None = Depends(get_optional_user),
) -> FileResponse:
    """手机扫码 GET 下载证书 PNG。"""
    store = request.app.state.session_store
    settings = request.app.state.settings
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_session_access(record, user)

    try:
        validate_session_id(session_id)
    except WorkspaceGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cert_path: Path = _certificate_path(
        session_id, settings.workspace_dir, user_id=record.user_id
    )
    if not cert_path.is_file():
        raise HTTPException(status_code=404, detail="certificate not found")

    display_name: str = (record.display_name or "证书").strip() or "证书"
    safe_name: str = re.sub(r'[\\/:*?"<>|]', "_", display_name)[:40]
    filename: str = f"{safe_name}_证书.png"

    return FileResponse(
        cert_path,
        media_type="image/png",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{session_id}/play", response_model=SessionRecord)
def mark_play(session_id: str, request: Request) -> SessionRecord:
    store = request.app.state.session_store
    record: SessionRecord | None = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    record.phase = SessionPhase.PLAY
    record.wizard_step = "S9"
    store.save(record)
    return record
