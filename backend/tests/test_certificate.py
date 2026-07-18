from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

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


def test_certificate_upload_and_download(client: TestClient) -> None:
    created = client.post("/sessions")
    assert created.status_code == 201
    session_id: str = created.json()["session_id"]

    # 单测不打外网：中继失败时应回落本地 token 路径
    with patch(
        "app.routers.sessions.upload_certificate_relay",
        side_effect=RuntimeError("relay disabled in unit test"),
    ):
        upload = client.put(
            f"/sessions/{session_id}/certificate",
            content=_PNG_HEADER,
            headers={"Content-Type": "image/png"},
        )
    assert upload.status_code == 200
    body = upload.json()
    assert body["ok"] is True
    assert body["download_token"]
    assert body["download_path"].startswith("/public/certificates/")
    assert body["download_url"].startswith("/public/certificates/")
    assert body["expires_in_sec"] > 0

    token: str = body["download_token"]
    download = client.get(f"/public/certificates/{token}")
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"
    assert download.content == _PNG_HEADER

    legacy = client.get(f"/sessions/{session_id}/certificate/download")
    assert legacy.status_code == 200
    assert legacy.content == _PNG_HEADER


def test_certificate_rejects_non_png(client: TestClient) -> None:
    session_id: str = client.post("/sessions").json()["session_id"]

    bad = client.put(
        f"/sessions/{session_id}/certificate",
        content=b"not-a-png",
        headers={"Content-Type": "image/png"},
    )
    assert bad.status_code == 400


def test_certificate_download_404_before_upload(client: TestClient) -> None:
    session_id: str = client.post("/sessions").json()["session_id"]

    missing = client.get(f"/sessions/{session_id}/certificate/download")
    assert missing.status_code == 404

    missing_token = client.get("/public/certificates/not-a-real-token")
    assert missing_token.status_code == 404
