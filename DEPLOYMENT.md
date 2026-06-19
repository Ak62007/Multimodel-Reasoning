# Deployment

MMR ships as two containers — `mmr-backend` (FastAPI + pipeline + agent chain)
and `mmr-frontend` (nginx + React build). Spec §12 asks for one concrete
deployment recipe; this doc covers two:

1. **[Generic VPS via `docker compose`](#1-vps-via-docker-compose)** — the
   straightforward "rent a box and SSH in" path. Recommended.
2. **[Fly.io](#2-flyio)** — for users who want managed infra without writing
   a kubernetes manifest. Two `Procfile`-style apps.

Production-grade observability, secrets management, and rolling deploys are
out of scope here; both recipes get you to "the URL works" with a sensible
disk/memory footprint.

---

## Environment variable checklist

Same for every deployment. Copy `.env.example`, fill in the **required** rows.

| Var | Required? | Notes |
| --- | --- | --- |
| `GROQ_API_KEY` | ✅ | From `console.groq.com`. |
| `ASSEMBLYAI_API_KEY` | ✅ | From `assemblyai.com`. |
| `LLM_PROVIDER` | ⚠ | Default `groq`. Set to `stub` to skip LLM calls (testing only). |
| `LLM_MODEL` | – | Default `llama-3.3-70b-versatile`. |
| `AGENT_MAX_CONCURRENCY` | – | Default `4`. Bump if you hit Groq rate limits less often than expected. |
| `MAX_UPLOAD_MB` | – | Default `500`. Match nginx `client_max_body_size` in `docker/nginx.conf` if you raise it. |
| `WHISPER_MODEL_SIZE` | – | `tiny` for fast iteration; `medium` for accuracy; default `small`. |
| `WHISPER_DEVICE` | – | `cpu` (default) or `cuda` (requires CUDA-built torch). |
| `SPEAKER_LABEL` | – | Default `B` — assumes AssemblyAI labels interviewer=A, interviewee=B. |
| `CORS_ORIGINS` | ⚠ | **Set to your production frontend origin**, e.g. `["https://mmr.example.com"]`. |
| `DATA_ROOT` | – | Default `/app/data` inside the container. |
| `DB_PATH` | – | Default `/app/data/mmr.db`. |
| `MMR_TEST_MODE` | ⚠ | **Leave `0` in production.** Setting to `1` allows uploading pre-computed parquets, bypassing the pipeline. |

Also required at the filesystem layer:

- **`models/face_landmarker.task`** — MediaPipe model file. Download:
  ```
  curl -L https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task \
    -o models/face_landmarker.task
  ```

- **A persistent disk volume mounted at `/app/data`** in the backend container.
  Without it, every container restart drops the SQLite DB + every job's
  artefacts. The data volume holds:
  - `data/mmr.db` — SQLite (Job rows + history)
  - `data/uploads/{job-id}.{ext}` — raw uploads
  - `data/processed/{job-id}/{master.parquet,segments.json,report.json,report.md,job.log}` — pipeline outputs

  A reasonable initial size is **20 GB** (each 10-minute 1080p interview is
  ~500 MB on disk plus a few hundred KB of derived artefacts; budget more
  if you keep history forever).

---

## 1. VPS via `docker compose`

This is the recommended path. Any 2 vCPU / 4 GB RAM Linux box works for
small-volume use; bump RAM to **8 GB** if you'll run `WHISPER_MODEL_SIZE=medium`
or process multiple interviews in parallel.

### 1.1 Prepare the box

```bash
# On the VPS (Ubuntu 22.04 / 24.04 used as example)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
newgrp docker

# Clone the repo
git clone <repo-url> /opt/mmr
cd /opt/mmr

# Secrets
cp .env.example .env
$EDITOR .env  # fill in GROQ_API_KEY, ASSEMBLYAI_API_KEY, CORS_ORIGINS

# MediaPipe model
mkdir -p models
curl -L https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task \
  -o models/face_landmarker.task
```

### 1.2 Bring up the stack

```bash
docker compose up -d --build

# Verify
curl http://127.0.0.1:8000/api/health      # backend direct
curl http://127.0.0.1:5173/api/health      # through nginx proxy
```

Both should return `{"status":"ok","version":"0.1.0"}`.

### 1.3 Front it with HTTPS

The compose file exposes nginx on `:5173`. Put a TLS terminator in front
(Caddy is the quickest):

```caddyfile
# /etc/caddy/Caddyfile
mmr.example.com {
  reverse_proxy localhost:5173
}
```

Then point your DNS A record at the VPS IP and `sudo systemctl reload caddy`.

> Remember to update `CORS_ORIGINS` in `.env` to the public origin
> (`https://mmr.example.com`) and `docker compose up -d` to pick it up.

### 1.4 Updates

```bash
cd /opt/mmr
git pull
docker compose up -d --build  # rebuilds changed images, recreates containers
```

### 1.5 Backups

The only mutable state is the `./data` directory. A nightly `rsync` of
`/opt/mmr/data/` to off-box storage is sufficient:

```cron
# crontab -e
0 3 * * * /usr/bin/rsync -a /opt/mmr/data/ user@backup-host:/backups/mmr/$(date +\%F)/
```

`mmr.db` is plain SQLite — if you need point-in-time backups, copy it via
`sqlite3 data/mmr.db ".backup data/mmr.db.bak"` to get a consistent snapshot
while the backend is still serving.

---

## 2. Fly.io

Fly's volumes give us persistent storage and its proxy handles TLS. Two
apps (backend + frontend) share a Fly internal network.

### 2.1 Backend

```bash
fly launch --no-deploy --name mmr-backend \
    --dockerfile docker/Dockerfile.backend \
    --vm-size shared-cpu-2x --vm-memory 4096
```

In `fly.toml`:

```toml
app = "mmr-backend"
primary_region = "iad"

[build]
  dockerfile = "docker/Dockerfile.backend"

[env]
  DATA_ROOT = "/app/data"
  DB_PATH = "/app/data/mmr.db"
  FACE_LANDMARKER_PATH = "/app/models/face_landmarker.task"
  AGENT_MAX_CONCURRENCY = "4"
  WHISPER_MODEL_SIZE = "small"
  WHISPER_DEVICE = "cpu"
  CORS_ORIGINS = '["https://mmr-frontend.fly.dev"]'

[[mounts]]
  source = "mmr_data"
  destination = "/app/data"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1
```

Create the volume + ship secrets:

```bash
fly volumes create mmr_data --size 20 --region iad
fly secrets set \
  GROQ_API_KEY=... \
  ASSEMBLYAI_API_KEY=...
```

Bundle `models/face_landmarker.task` into the image (so the volume only
holds runtime state). Either add it to the repo (it's a 3.6 MB binary;
arguably fine to commit) or inject at build time with:

```dockerfile
# Append to docker/Dockerfile.backend before EXPOSE:
ADD https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task /app/models/face_landmarker.task
```

Then:

```bash
fly deploy
```

### 2.2 Frontend

```bash
cd frontend
fly launch --no-deploy --name mmr-frontend \
    --dockerfile ../docker/Dockerfile.frontend \
    --vm-size shared-cpu-1x --vm-memory 256
```

In `frontend/fly.toml`:

```toml
app = "mmr-frontend"
primary_region = "iad"

[build]
  dockerfile = "../docker/Dockerfile.frontend"
  [build.args]
    VITE_API_BASE_URL = "https://mmr-backend.fly.dev"

[http_service]
  internal_port = 80
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
```

Update `docker/nginx.conf`'s `proxy_pass` to the public backend URL — or
strip the `/api/` location block entirely and let the SPA hit
`VITE_API_BASE_URL` directly (browser CORS handles it).

Then:

```bash
cd frontend && fly deploy
```

### 2.3 Smoke check

```bash
curl https://mmr-backend.fly.dev/api/health
open https://mmr-frontend.fly.dev/
```

---

## Operational notes

### Sizing

- **CPU:** the pipeline is single-threaded per job. Whisper-small on a
  2 vCPU box runs at ~1× real-time. For sustained throughput, scale by
  running multiple backend replicas behind a load balancer (each with
  its own data volume); the agent chain handles its own concurrency
  per-job via `AGENT_MAX_CONCURRENCY`.
- **RAM:** baseline ~1.5 GB. Whisper-small adds ~1 GB; whisper-medium
  adds ~3 GB. Process one job at a time per container.
- **Disk:** 500 MB per 10-minute 1080p interview after compression.
  Reaper script idea — delete jobs older than 30 days:
  ```
  curl -s http://localhost:8000/api/jobs?status=succeeded | \
    jq -r '.items[] | select(.updated_at < (now - 86400*30 | strftime("%Y-%m-%dT%H:%M:%S"))) | .id' | \
    xargs -I{} curl -X DELETE http://localhost:8000/api/jobs/{}
  ```

### Monitoring

- **Health:** `GET /api/health` returns 200 + version.
- **Job state:** `GET /api/jobs` with `?status=failed` to find stuck jobs.
  Each job's `error` field has the failure reason; `GET /api/jobs/{id}/logs`
  returns the captured stage output.
- **Logging:** stage transitions land in stdout (visible via `docker logs`)
  AND in `data/processed/{job-id}/job.log` (per-job file). Ship to your
  log aggregator with the Docker JSON driver or sidecar Fluent Bit.

### Secrets rotation

Set the new key, restart the container:

```bash
$EDITOR .env
docker compose restart backend
```

Or on Fly:

```bash
fly secrets set GROQ_API_KEY=new-value -a mmr-backend
# Fly redeploys automatically.
```

---

## What we don't do

This guide doesn't cover authentication, multi-tenancy, observability
beyond logs, or autoscaling. The codebase isn't designed for those
yet — see "Known limitations" in `README.md`.
