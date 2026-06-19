"""Full job lifecycle tests using the test-mode parquet upload path.

`MMR_TEST_MODE=1` (set in the `settings` fixture) lets us upload the
committed `tiny_master_df.parquet` directly — the JobRunner skips stages
1–9 and only exercises stages 10–11 (agentic layer with stub provider).
That gives us a deterministic end-to-end run in <1s.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.config import Settings
from backend.app.db import session_scope
from backend.app.models import Job


def _upload(client: TestClient, parquet_path: Path) -> str:
    with parquet_path.open("rb") as f:
        r = client.post(
            "/api/jobs",
            files={"video": (parquet_path.name, f, "application/octet-stream")},
            data={"speaker_label": "B"},
        )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_upload_returns_queued_job(client: TestClient, tiny_parquet_path: Path) -> None:
    with tiny_parquet_path.open("rb") as f:
        r = client.post(
            "/api/jobs",
            files={"video": (tiny_parquet_path.name, f, "application/octet-stream")},
            data={"speaker_label": "B"},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] in ("queued", "running", "succeeded")
    assert body["filename"] == "tiny_master_df.parquet"
    assert body["progress"] == 0.0 or body["progress"] == 1.0


def test_upload_rejects_unsupported_extension(client: TestClient) -> None:
    r = client.post(
        "/api/jobs",
        files={"video": ("not_a_video.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"speaker_label": "B"},
    )
    assert r.status_code == 422


def test_full_lifecycle_upload_then_succeed(client: TestClient, tiny_parquet_path: Path) -> None:
    """Upload → BackgroundTasks runs the agent chain → status becomes succeeded
    → segments + report are served."""
    job_id = _upload(client, tiny_parquet_path)

    # TestClient runs BackgroundTasks synchronously after the response, so by
    # the time the next request lands the job is already finished.
    job_res = client.get(f"/api/jobs/{job_id}")
    assert job_res.status_code == 200
    job = job_res.json()
    assert job["status"] == "succeeded", job
    assert job["progress"] == 1.0
    assert job["error"] is None
    assert job["duration_sec"] is not None

    segments_res = client.get(f"/api/jobs/{job_id}/segments")
    assert segments_res.status_code == 200
    segments = segments_res.json()["items"]
    # Every selected window yields a WindowAnalysis field note (none dropped).
    assert segments, "expected at least the engineered anomaly windows"
    for seg in segments:
        assert "time_start" in seg
        assert "time_end" in seg
        assert "phase" in seg
        assert seg["narrative"], "every window note must have a narrative"
        assert "signals" in seg

    report_res = client.get(f"/api/jobs/{job_id}/report")
    assert report_res.status_code == 200
    body = report_res.json()
    assert body["markdown"].startswith("# ")
    structured = body["structured"]
    assert structured["headline"]
    assert structured["overview"]
    assert structured["behavioral_arc"]
    assert "highlights" in structured
    assert "threads" in structured


def test_list_jobs_pagination(client: TestClient, tiny_parquet_path: Path) -> None:
    for _ in range(3):
        _upload(client, tiny_parquet_path)

    r = client.get("/api/jobs", params={"limit": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_list_jobs_status_filter(client: TestClient, tiny_parquet_path: Path) -> None:
    _upload(client, tiny_parquet_path)
    r = client.get("/api/jobs", params={"status": "succeeded"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(j["status"] == "succeeded" for j in body["items"])


def test_get_unknown_job_404(client: TestClient) -> None:
    assert client.get("/api/jobs/does-not-exist").status_code == 404
    assert client.get("/api/jobs/does-not-exist/segments").status_code == 404
    assert client.get("/api/jobs/does-not-exist/report").status_code == 404
    assert client.get("/api/jobs/does-not-exist/logs").status_code == 404
    assert client.get("/api/jobs/does-not-exist/master_df").status_code == 404


def test_delete_job_removes_row_and_artefacts(client: TestClient, tiny_parquet_path: Path) -> None:
    job_id = _upload(client, tiny_parquet_path)
    # Confirm artefacts exist
    pre = client.get(f"/api/jobs/{job_id}/report")
    assert pre.status_code == 200

    r = client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_master_df_parquet_download(client: TestClient, tiny_parquet_path: Path) -> None:
    job_id = _upload(client, tiny_parquet_path)
    r = client.get(f"/api/jobs/{job_id}/master_df", params={"format": "parquet"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert len(r.content) > 0


def test_master_df_json_returns_records(client: TestClient, tiny_parquet_path: Path) -> None:
    job_id = _upload(client, tiny_parquet_path)
    r = client.get(f"/api/jobs/{job_id}/master_df", params={"format": "json"})
    assert r.status_code == 200
    records = r.json()
    assert isinstance(records, list)
    assert len(records) == 60
    assert "Time" in records[0]
    assert "blinking_data" in records[0]


def test_byok_keys_accepted_not_persisted_and_tokens_recorded(
    client: TestClient, settings: Settings, tiny_parquet_path: Path
) -> None:
    """A per-request Gemini + AssemblyAI key is accepted, the job still runs
    (stub ignores them), the keys are NEVER written to the Job row, and the
    token-usage fields are populated (0 under the stub provider)."""
    sentinel_gemini = "GEMINI-SECRET-DO-NOT-STORE"
    sentinel_aai = "AAI-SECRET-DO-NOT-STORE"
    with tiny_parquet_path.open("rb") as f:
        r = client.post(
            "/api/jobs",
            files={"video": (tiny_parquet_path.name, f, "application/octet-stream")},
            data={
                "speaker_label": "B",
                "gemini_api_key": sentinel_gemini,
                "assemblyai_api_key": sentinel_aai,
            },
        )
    assert r.status_code == 201, r.text
    job_id = r.json()["id"]

    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["status"] == "succeeded", body
    # Token-usage plumbing ran (stub makes no real calls, so the totals are 0).
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        assert body[field] == 0, body

    # The keys must never land in the durable Job row.
    with session_scope(settings) as session:
        job = session.exec(select(Job).where(Job.id == job_id)).first()
        assert job is not None
        persisted = {str(v) for v in job.model_dump().values()}
        assert sentinel_gemini not in persisted
        assert sentinel_aai not in persisted


def test_free_tier_runs_and_is_persisted(client: TestClient, tiny_parquet_path: Path) -> None:
    """A free-tier job runs the lean single-call path end-to-end (stub), succeeds,
    still produces window notes, and the tier is reported back."""
    with tiny_parquet_path.open("rb") as f:
        r = client.post(
            "/api/jobs",
            files={"video": (tiny_parquet_path.name, f, "application/octet-stream")},
            data={"speaker_label": "B", "tier": "free"},
        )
    assert r.status_code == 201, r.text
    job_id = r.json()["id"]

    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["status"] == "succeeded", body
    assert body["tier"] == "free"
    segments = client.get(f"/api/jobs/{job_id}/segments").json()["items"]
    assert segments, "free tier should still produce window notes"


def test_invalid_tier_rejected(client: TestClient, tiny_parquet_path: Path) -> None:
    with tiny_parquet_path.open("rb") as f:
        r = client.post(
            "/api/jobs",
            files={"video": (tiny_parquet_path.name, f, "application/octet-stream")},
            data={"speaker_label": "B", "tier": "premium"},
        )
    assert r.status_code == 400
    assert "tier" in r.json()["detail"].lower()


def test_logs_returns_tail(client: TestClient, tiny_parquet_path: Path) -> None:
    job_id = _upload(client, tiny_parquet_path)
    r = client.get(f"/api/jobs/{job_id}/logs", params={"tail": 10})
    assert r.status_code == 200
    body = r.json()
    assert "lines" in body
    # Logs are written during stage transitions; should be non-empty for succeeded job.
    assert isinstance(body["lines"], list)
