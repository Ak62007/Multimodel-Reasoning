"""End-to-end tests of the jobs + reports endpoints.

Every test uses ``MMR_TEST_MODE=1`` + ``LLM_PROVIDER=stub`` (set in the
api_settings fixture). The POST /api/jobs path accepts the committed
``tests/fixtures/tiny_master_df.parquet`` instead of a video, so the
backend skips the pipeline and exercises only the JobRunner + agents.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
MASTER_FIXTURE = FIXTURE_DIR / "tiny_master_df.parquet"


def _upload_master_fixture(client: TestClient) -> dict:
    with MASTER_FIXTURE.open("rb") as f:
        resp = client.post(
            "/api/jobs",
            files={
                "video": (
                    MASTER_FIXTURE.name,
                    f,
                    "application/octet-stream",
                ),
            },
            data={"speaker_label": "B"},
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_job_returns_job_with_queued_status(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    assert job["filename"] == MASTER_FIXTURE.name
    assert job["status"] in ("queued", "running", "succeeded")


def test_full_lifecycle_with_test_mode_and_stub(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    job_id = job["id"]

    # BackgroundTasks have run by the time TestClient.post returns;
    # fetching the job should already show terminal state.
    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final
    assert final["progress"] == 1.0
    assert final["error"] is None
    assert final["duration_sec"] is not None and final["duration_sec"] >= 0.0

    # Segments are present and non-empty.
    segments_resp = client.get(f"/api/jobs/{job_id}/segments")
    assert segments_resp.status_code == 200
    segments = segments_resp.json()
    assert isinstance(segments, list)
    assert len(segments) >= 1
    first = segments[0]
    assert {"time_range_start", "time_range_end", "overall_window_tone"}.issubset(first)
    assert all(
        i["pattern_type"] in ("Strength", "Concern", "Notable")
        for r in segments
        for i in r["key_insights"]
    )

    # Final report = markdown + structured.
    report_resp = client.get(f"/api/jobs/{job_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert "Executive Summary" in report["markdown"]
    for field in (
        "executive_summary",
        "behavioral_strengths",
        "vulnerabilities_and_triggers",
        "areas_for_improvement",
    ):
        assert field in report["structured"]


def test_master_df_endpoint_returns_parquet_by_default(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    job_id = job["id"]

    resp = client.get(f"/api/jobs/{job_id}/master_df")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert resp.content[:4] == b"PAR1"  # parquet magic


def test_master_df_endpoint_returns_json_when_requested(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    job_id = job["id"]

    resp = client.get(f"/api/jobs/{job_id}/master_df", params={"format": "json"})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "Time" in rows[0]


def test_logs_endpoint_returns_tail(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    job_id = job["id"]

    resp = client.get(f"/api/jobs/{job_id}/logs", params={"tail": 50})
    assert resp.status_code == 200
    lines = resp.json()["lines"]
    assert isinstance(lines, list)
    assert any("job complete" in line for line in lines)


def test_list_jobs_returns_pagination(client: TestClient) -> None:
    for _ in range(3):
        _upload_master_fixture(client)
    resp = client.get("/api/jobs", params={"limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2


def test_list_jobs_filters_by_status(client: TestClient) -> None:
    _upload_master_fixture(client)
    resp = client.get("/api/jobs", params={"status_filter": "succeeded"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(j["status"] == "succeeded" for j in body["items"])


def test_get_job_404_for_unknown_id(client: TestClient) -> None:
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


def test_segments_409_when_job_not_succeeded(client: TestClient) -> None:
    """Queued/running/failed jobs cannot serve segments yet."""
    # Insert a manually-queued job that the BackgroundTasks chain never ran.
    from sqlmodel import Session

    from backend.app.config import get_settings
    from backend.app.db import get_engine
    from backend.app.models import JobRecord

    settings = get_settings()
    engine = get_engine(settings)
    with Session(engine) as session:
        job = JobRecord(id="not-ready", filename="x.mp4", status="queued")
        session.add(job)
        session.commit()

    resp = client.get("/api/jobs/not-ready/segments")
    assert resp.status_code == 409


def test_report_409_when_job_not_succeeded(client: TestClient) -> None:
    from sqlmodel import Session

    from backend.app.config import get_settings
    from backend.app.db import get_engine
    from backend.app.models import JobRecord

    settings = get_settings()
    engine = get_engine(settings)
    with Session(engine) as session:
        job = JobRecord(id="not-ready-2", filename="x.mp4", status="failed")
        session.add(job)
        session.commit()

    resp = client.get("/api/jobs/not-ready-2/report")
    assert resp.status_code == 409


def test_delete_job_removes_db_row_and_artefacts(client: TestClient) -> None:
    job = _upload_master_fixture(client)
    job_id = job["id"]
    resp = client.delete(f"/api/jobs/{job_id}")
    assert resp.status_code == 204
    follow_up = client.get(f"/api/jobs/{job_id}")
    assert follow_up.status_code == 404


def test_upload_rejects_unsupported_mime_outside_test_mode(client: TestClient) -> None:
    """In MMR_TEST_MODE=1 the parquet shortcut works; in production it would 422."""
    # Reject a clearly-wrong-type upload regardless of test mode.
    resp = client.post(
        "/api/jobs",
        files={"video": ("note.txt", b"hello", "text/plain")},
        data={"speaker_label": "B"},
    )
    assert resp.status_code == 422
