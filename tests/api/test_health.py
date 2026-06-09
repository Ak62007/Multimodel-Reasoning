"""Health endpoint smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok_and_version(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]
