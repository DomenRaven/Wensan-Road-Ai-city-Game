from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.certificate_relay import RelayResult, cleanup_relay_meta, save_relay_meta

_PNG_HEADER = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_certificate_upload_uses_relay_url_when_no_public_base(client: TestClient) -> None:
    created = client.post("/sessions")
    session_id: str = created.json()["session_id"]
    fake = RelayResult(
        provider="litterbox",
        url="https://litter.catbox.moe/demo.png",
        ttl_sec=3600,
        delete_url=None,
    )
    with patch(
        "app.routers.sessions.upload_certificate_relay",
        return_value=fake,
    ):
        upload = client.put(
            f"/sessions/{session_id}/certificate",
            content=_PNG_HEADER,
            headers={"Content-Type": "image/png"},
        )
    assert upload.status_code == 200
    body = upload.json()
    assert body["download_url"] == "https://litter.catbox.moe/demo.png"
    assert body["relay_provider"] == "litterbox"
    assert body["expires_in_sec"] <= 3600


def test_cleanup_relay_meta_calls_delete_url(tmp_path: Path) -> None:
    result = RelayResult(
        provider="smms",
        url="https://example.com/a.png",
        ttl_sec=86400,
        delete_url="https://example.com/delete/x",
    )
    save_relay_meta(tmp_path, result)
    with patch("app.services.certificate_relay.urllib.request.urlopen") as opener:
        opener.return_value.__enter__.return_value.read.return_value = b"ok"
        assert cleanup_relay_meta(tmp_path) is True
        assert opener.called
    assert not (tmp_path / ".certificate_relay.json").exists()
