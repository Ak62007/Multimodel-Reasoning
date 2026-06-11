# Deployment

This document covers deploying MMR to production. The recommended path
is a small Linux VPS running the bundled `docker compose` stack with
Caddy in front for TLS. A short Fly.io note is included for users who
prefer a PaaS.

> **Audience.** Someone comfortable on a Linux command line who has SSH
> access to a freshly-rented VPS and can edit DNS for one A record.
> No prior MMR knowledge assumed.

---

## 1. What you'll end up with

- A single VPS hosting both services from `docker-compose.yml`:
  - `backend` (FastAPI + pipeline + agents) on internal port `8000`.
  - `frontend` (nginx-served React SPA, with `/api/*` reverse-proxied
    to backend) on internal port `8080`.
- Caddy in front terminating TLS for your domain and forwarding to
  the frontend container.
- A persistent `./data/` directory holding uploaded videos, derived
  parquet files, agent outputs, and the SQLite job-metadata database.
- A `./models/` directory holding the MediaPipe `face_landmarker.task`
  weights (~6.7 MB), mounted read-only into the backend container.

---

## 2. Sizing

| Resource     | Recommended minimum                          | Why                                                                                       |
|--------------|----------------------------------------------|-------------------------------------------------------------------------------------------|
| CPU          | 4 vCPU                                       | The pipeline (MediaPipe face mesh + librosa + whisper) is CPU-bound and parallelises over frames. |
| RAM          | 8 GB                                         | Whisper-timestamped + torch comfortably want 4 GB; the rest covers FastAPI + nginx + headroom. |
| Disk         | 40 GB total, of which 20 GB free for `data/` | Each analysis is ~500 MB upload + ~10 MB derived. 20 GB ≈ 30 analyses before reaping.     |
| Bandwidth    | unmetered or ≥ 1 TB/month                    | Users upload raw video and download the report HTML.                                      |
| Architecture | `linux/amd64`                                | MediaPipe ships wheels only for `manylinux_2_28_x86_64` on Linux (see [§3.4](#34-architecture-note)). |

A $10–20/month VPS (Hetzner CX22, DigitalOcean basic, Linode 2 GB+, OVH
VPS Comfort, etc.) is the sweet spot. Don't pick the cheapest tier
with 1 vCPU + 1 GB RAM — the pipeline will OOM on the whisper step.

---

## 3. VPS deployment (recommended)

### 3.1 Prerequisites

On the VPS, as root or a sudoer:

```bash
# Docker + compose plugin.
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in so the new group membership takes effect.

# Caddy for TLS termination.
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
```

DNS: point an A record (e.g. `mmr.example.com`) at the VPS public IP
before continuing — Caddy provisions Let's Encrypt certificates on
first start and needs the DNS resolving.

### 3.2 Clone and configure

```bash
# Pick a path you control; /opt/mmr is conventional.
sudo mkdir -p /opt/mmr && sudo chown $USER /opt/mmr
cd /opt/mmr
git clone https://github.com/<owner>/mmr.git .

# Provide the MediaPipe weights (they are gitignored).
# Download the face_landmarker.task model from Google's MediaPipe assets:
mkdir -p models
curl -fsSL -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

# Configure environment.
cp .env.example .env
# Then edit .env and set at minimum:
#   GROQ_API_KEY        — required (LLM_PROVIDER=groq)
#   ASSEMBLYAI_API_KEY  — required for diarised transcripts
# Optional but recommended for tuning:
#   AGENT_MAX_CONCURRENCY  (default 4)
#   MAX_UPLOAD_MB          (default 500)
```

### 3.3 Build and start

```bash
docker compose build      # ~10 min first time (backend image is large)
docker compose up -d
docker compose ps         # both services should be Up; backend reaches (healthy) in ~15 s
docker compose logs -f backend | head -50   # sanity-check startup
```

`./data/` is created automatically on first start. The backend will
also create `./data/uploads/` and `./data/processed/` and initialise
the SQLite schema in `./data/mmr.db`.

### 3.4 Architecture note

The backend Dockerfile pins both stages to `--platform=linux/amd64`
because MediaPipe only publishes wheels for `manylinux_2_28_x86_64` on
Linux. If you're deploying to an arm64 VPS (AWS Graviton, Hetzner
ARM), the image still builds via emulation but the pipeline will be
significantly slower. For arm64 hosts, prefer an amd64 instance type
in the same price band.

### 3.5 Put Caddy in front for TLS

Replace `/etc/caddy/Caddyfile` with:

```caddy
mmr.example.com {
    encode zstd gzip

    # Forward to the compose frontend; nginx inside the container
    # serves the SPA and proxies /api to the backend container.
    reverse_proxy localhost:8080

    # Allow large file uploads (cap matches MAX_UPLOAD_MB, default 500).
    request_body {
        max_size 600MB
    }
}
```

Then:

```bash
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Browse to `https://mmr.example.com`. Caddy will provision the
certificate on first request and you should see the upload screen.

### 3.6 Backups

`./data/` is the only stateful directory. A nightly rsync to off-host
storage is enough:

```bash
# Append to root's crontab:
sudo crontab -e
0 3 * * * rsync -a --delete /opt/mmr/data/ backup-host:/backups/mmr/
```

The SQLite file is safe to copy while the service is running because
the job runner uses short transactions; if you want a fully-quiesced
snapshot, `sqlite3 data/mmr.db ".backup data/mmr.db.bak"` first.

### 3.7 Updates

```bash
cd /opt/mmr
git pull
docker compose build
docker compose up -d
docker image prune -f
```

There are no database migrations — the schema is created on startup
from the SQLModel models and is additively safe to extend.

---

## 4. Environment-variable checklist

| Variable                 | Required?               | Default                              | Purpose                                                                       |
|--------------------------|-------------------------|--------------------------------------|-------------------------------------------------------------------------------|
| `LLM_PROVIDER`           | recommended             | `groq`                               | `groq` for production, `stub` for tests/CI (deterministic, no API calls).     |
| `LLM_MODEL`              | recommended             | `llama-3.3-70b-versatile`            | Groq model identifier; swap as Groq's catalogue evolves.                      |
| `GROQ_API_KEY`           | **required** (groq)     | —                                    | Auth for `LLM_PROVIDER=groq`. Get one at <https://console.groq.com>.          |
| `ASSEMBLYAI_API_KEY`     | **required**            | —                                    | Diarised utterance transcription. Get one at <https://www.assemblyai.com>.    |
| `AGENT_MAX_CONCURRENCY`  | optional                | `4`                                  | Bounded concurrency for parallel agent calls per analysis window.             |
| `MAX_UPLOAD_MB`          | optional                | `500`                                | Reject uploads larger than this with HTTP 413.                                |
| `MMR_DB_URL`             | optional                | `sqlite:///./data/mmr.db`            | SQLAlchemy URL for the job DB. Postgres works too if you outgrow SQLite.     |
| `DATA_ROOT`              | optional                | `./data`                             | Where the backend reads/writes uploads + processed artefacts.                 |
| `UPLOAD_DIR`             | optional                | `${DATA_ROOT}/uploads`               | Per-job raw uploads.                                                          |
| `PROCESSED_DIR`          | optional                | `${DATA_ROOT}/processed`             | Per-job master parquet + agent outputs.                                       |
| `MMR_TEST_MODE`          | **never set in prod**   | `0`                                  | `1` lets POST /api/jobs accept a precomputed master parquet and skips the heavy pipeline. CI-only. |
| `VITE_API_BASE_URL`      | build-time              | `""` (same origin via nginx proxy)   | Base URL the SPA uses to reach the backend. Leave empty under the bundled compose stack. |

`.env.example` is the authoritative starter; copy it to `.env` and
fill the two API keys before the first `docker compose up`.

---

## 5. Operational notes

### 5.1 Monitoring

The backend exposes `GET /api/health` which returns `{"status":"ok",
"version":"<app_version>"}` when uvicorn is up and the SQLite handle
is reachable. The bundled Docker healthcheck curls this endpoint
every 30 s; `docker compose ps` reports `(healthy)` / `(unhealthy)`.

For external monitoring (UptimeRobot, BetterStack, Healthchecks.io),
point your check at `https://your-domain/api/health` and alert on
non-200 or non-JSON responses.

### 5.2 Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Backend logs are structured (Python `logging` to stdout); per-job
events include the job UUID so you can `grep <uuid> backend.log` to
follow a single analysis end-to-end.

### 5.3 Secrets rotation

`.env` is read on container start, so rotating `GROQ_API_KEY` or
`ASSEMBLYAI_API_KEY` is `vim .env && docker compose up -d`. No
downtime beyond the few seconds it takes uvicorn to restart.

### 5.4 Disk reaper

The pipeline never deletes uploads on its own. For long-running
deployments add a small reaper that drops `data/uploads/<job_id>/`
when the corresponding row in `mmr.db` has `status='done'` and is
older than your retention window (e.g. 30 days):

```bash
# Sketch — adapt to your retention policy.
sqlite3 /opt/mmr/data/mmr.db \
  "SELECT id FROM jobrecord WHERE status='done' AND created_at < date('now','-30 days')" \
  | xargs -I{} rm -rf /opt/mmr/data/uploads/{}
```

Wire it into cron alongside the rsync backup.

---

## 6. Adding authentication later

The default deployment assumes single-tenant use, typically behind a
VPN or behind a firewall that only your team can reach. If you need
to expose MMR to the public Internet, the lowest-friction options are
(in increasing order of effort):

1. **Caddy basic auth.** Add a `basicauth` directive to the Caddyfile.
   Coarse but zero application changes.
2. **Bearer-token FastAPI dependency.** Add a `Depends(verify_token)`
   to the routers in `backend/app/routers/`, where `verify_token`
   compares against an env var. The SPA's `frontend/src/api/client.ts`
   would need to attach the token to every request — search for the
   `fetch(` calls and add a header.
3. **Full OIDC (Google / Auth0 / Keycloak).** Use `authlib` on the
   backend and a small login screen on the frontend. This is a real
   project — budget a day or two.

None of these are wired up today. Doing so changes the OpenAPI
surface, the SPA, and the deployment shape, all of which are
deliberately out of scope for the initial release.

---

## 7. Fly.io (alternative path)

If you'd rather use a PaaS than rent a VPS, Fly.io is the closest
fit because it speaks Docker images natively. Sketch (not validated
end-to-end here):

```bash
fly launch --copy-config --no-deploy   # answer "yes" to "use existing Dockerfile?" for backend
# Edit the generated fly.toml so internal_port = 8000 and add a [mounts] section
# pointing at /app/data; create the volume:
fly volume create mmr_data --size 20
# Set secrets instead of mounting .env:
fly secrets set GROQ_API_KEY=... ASSEMBLYAI_API_KEY=...
# The MediaPipe weights must be baked into the image — uncomment the
# COPY models models line that the current Dockerfile already has, and
# either commit the .task file or fetch it in a Dockerfile RUN.
fly deploy
```

Then a second `fly launch` for the frontend (no volume needed), with
`VITE_API_BASE_URL=https://<backend-app>.fly.dev` as a build arg.
Cheaper alternatives like Railway have a moving docker-compose story
and are deliberately not documented here.

---

## 8. Troubleshooting

- **`COPY docker/nginx.conf` fails during frontend build.** Make sure
  you're on the post-M7-fix commit; `.dockerignore` has
  `!docker/nginx.conf` to un-ignore that single file.
- **Backend builder fails with "readme file does not exist".** Same
  fix commit restores `README.md` to the build context; ensure it's
  present at the repo root.
- **MediaPipe wheel resolution error on Apple Silicon.** Expected on
  arm64 hosts. The Dockerfile pins `--platform=linux/amd64` which
  triggers Docker's qemu emulation; first build is slow. Use an
  amd64 host in production.
- **Backend container restarts in a loop with `face_landmarker.task`
  errors.** You haven't placed the weights under `./models/`. Run
  the `curl` command from §3.2.
- **`/api/jobs` returns 413.** Upload exceeded `MAX_UPLOAD_MB`. Raise
  the env var *and* the Caddy `request_body max_size` together. If
  you also raised it above 600 MB, raise `client_max_body_size` in
  `docker/nginx.conf` to match.

If something here is wrong or unclear, please open an issue with the
exact command you ran and the output you saw.
