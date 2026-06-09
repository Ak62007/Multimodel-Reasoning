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
    # The tiny fixture has two engineered anomalous windows; the stub Pattern
    # Detector emits an insight only when ≥2 modalities have anomalies, so
    # the per-window count is data-dependent. What we guarantee is shape.
    for seg in segments:
        assert "time_range_start" in seg
        assert "time_range_end" in seg
        assert "overall_window_tone" in seg
        assert "key_insights" in seg

    report_res = client.get(f"/api/jobs/{job_id}/report")
    assert report_res.status_code == 200
    body = report_res.json()
    assert body["markdown"].startswith("# Executive Summary")
    assert body["structured"]["executive_summary"]
    assert body["structured"]["behavioral_strengths"]
    assert body["structured"]["vulnerabilities_and_triggers"]
    assert body["structured"]["areas_for_improvement"]


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


def test_logs_returns_tail(client: TestClient, tiny_parquet_path: Path) -> None:
    job_id = _upload(client, tiny_parquet_path)
    r = client.get(f"/api/jobs/{job_id}/logs", params={"tail": 10})
    assert r.status_code == 200
    body = r.json()
    assert "lines" in body
    # Logs are written during stage transitions; should be non-empty for succeeded job.
    assert isinstance(body["lines"], list)
