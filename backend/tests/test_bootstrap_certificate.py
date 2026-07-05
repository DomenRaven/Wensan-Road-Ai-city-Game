"""Bootstrap / health · 展馆证书部署契约."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_bootstrap_includes_certificate_deploy() -> None:
    with TestClient(create_app()) as client:
        report = client.get("/bootstrap").json()

    cert = report.get("certificate", {})
    assert cert.get("endpoints", {}).get("upload") == "PUT /sessions/{session_id}/certificate"
    assert cert.get("endpoints", {}).get("public_download") == "GET /public/certificates/{token}"
    assert cert.get("download_ttl_sec", 0) > 0
    assert "ready_for_public_qr" in cert


def test_health_includes_certificate_block() -> None:
    with TestClient(create_app()) as client:
        body = client.get("/health").json()

    assert "certificate" in body
    assert body["certificate"].get("download_ttl_sec", 0) > 0
