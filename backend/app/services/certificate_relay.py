"""证书扫码下载 · 临时公网图床中继。

展厅常见情况：API 仅局域网可达，游客手机扫码打不开 127.0.0.1。
本模块在服务端把 PNG 上传到可匿名访问的临时图床，返回公网直链；
前端继续用本地 qrcodejs 把该 URL 编成二维码。

失败则回落本地 token 路径，不阻断证书上传。
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

RELAY_META_FILENAME: str = ".certificate_relay.json"
_USER_AGENT: str = "GameForgeK12/1.0 (+certificate-relay)"
# 单个图床短超时：网络不稳时尽快回落，避免整次扫码卡死
_TIMEOUT_SEC: float = 8.0

_LITTERBOX_URL: str = "https://litterbox.catbox.moe/resources/internals/api.php"
_SMMS_URL: str = "https://smms.app/api/v2/upload"


@dataclass(frozen=True)
class RelayResult:
    provider: str
    url: str
    ttl_sec: int
    delete_url: str | None = None


def _multipart(fields: list[tuple[str, str | tuple[str, bytes, str]]]) -> tuple[bytes, str]:
    boundary = "----GameForgeCertRelay7MA4"
    chunks: list[bytes] = []
    for name, value in fields:
        if isinstance(value, tuple):
            filename, data, ctype = value
            chunks.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                    f"Content-Type: {ctype}\r\n\r\n"
                ).encode("utf-8")
            )
            chunks.append(data)
            chunks.append(b"\r\n")
        else:
            chunks.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def _post_multipart(
    url: str,
    fields: list[tuple[str, str | tuple[str, bytes, str]]],
) -> tuple[int, bytes]:
    body, boundary = _multipart(fields)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("User-Agent", _USER_AGENT)
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
        return int(resp.status), resp.read()


def _upload_litterbox(png: bytes, filename: str) -> RelayResult:
    status, raw = _post_multipart(
        _LITTERBOX_URL,
        [
            ("reqtype", "fileupload"),
            ("time", "1h"),
            ("fileToUpload", (filename, png, "image/png")),
        ],
    )
    text: str = raw.decode("utf-8", errors="replace").strip()
    if status >= 400 or not text.startswith("http"):
        raise RuntimeError(f"litterbox unexpected response ({status}): {text[:160]}")
    return RelayResult(provider="litterbox", url=text, ttl_sec=3600, delete_url=None)


def _upload_smms(png: bytes, filename: str) -> RelayResult:
    status, raw = _post_multipart(
        _SMMS_URL,
        [("smfile", (filename, png, "image/png"))],
    )
    payload: dict[str, Any] = json.loads(raw.decode("utf-8", errors="replace"))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    url = str(data.get("url") or payload.get("images") or "").strip()
    if not url.startswith("http"):
        raise RuntimeError(f"smms upload failed ({status}): {payload.get('message')}")
    delete_url = str(data.get("delete") or "").strip() or None
    return RelayResult(provider="smms", url=url, ttl_sec=86400, delete_url=delete_url)


def upload_certificate_relay(png: bytes, filename: str = "certificate.png") -> RelayResult:
    """依次尝试 Litterbox → SM.MS，全部失败则抛出。"""
    safe_name: str = re.sub(r"[^\w.\-]+", "_", filename, flags=re.UNICODE)[:48] or "certificate.png"
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"

    errors: list[str] = []
    for uploader in (_upload_litterbox, _upload_smms):
        try:
            result = uploader(png, safe_name)
            logger.info("certificate relay ok via %s", result.provider)
            return result
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{uploader.__name__}: {exc}")
            logger.warning("certificate relay provider failed: %s", exc)

    raise RuntimeError("; ".join(errors) if errors else "relay unavailable")


def is_publicly_reachable_url(url: str) -> bool:
    """本机/局域网地址，游客手机通常扫不开。"""
    text = (url or "").strip().lower()
    if not text.startswith("http://") and not text.startswith("https://"):
        return False
    try:
        host = (urlparse(text).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        return False
    if host.startswith("192.168.") or host.startswith("10."):
        return False
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return False
    return True


def relay_meta_path(workspace_root: Path) -> Path:
    return workspace_root / RELAY_META_FILENAME


def save_relay_meta(workspace_root: Path, result: RelayResult) -> None:
    path = relay_meta_path(workspace_root)
    path.write_text(
        json.dumps(
            {
                "provider": result.provider,
                "url": result.url,
                "ttl_sec": result.ttl_sec,
                "delete_url": result.delete_url,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def cleanup_relay_meta(workspace_root: Path) -> bool:
    """会话结束：有 delete_url 则请求删除；否则依赖图床 TTL。"""
    path = relay_meta_path(workspace_root)
    if not path.is_file():
        return False
    try:
        meta: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    delete_url = str(meta.get("delete_url") or "").strip()
    if delete_url.startswith("http"):
        try:
            req = urllib.request.Request(delete_url, method="GET")
            req.add_header("User-Agent", _USER_AGENT)
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
                _ = resp.read()
            logger.info("certificate relay deleted via %s", meta.get("provider"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("certificate relay delete failed: %s", exc)

    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return True
