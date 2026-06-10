"""Tests for the /api/health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_status_and_version(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0-test"
