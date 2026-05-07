# Songa

[![CI](https://github.com/dami3n/songa/actions/workflows/ci.yml/badge.svg)](https://github.com/dami3n/songa/actions/workflows/ci.yml)

Computer vision platform for basketball — automatic tracking, player stats, and performance insights for coaches and academies across Africa.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, Framer Motion |
| CV API | FastAPI, YOLOv8, ByteTrack, OpenCV |
| Reverse proxy | Caddy (auto HTTPS) |
| Infra | Docker Compose, Azure VM, GitHub Actions |

## Architecture

```
Browser
   |
   v
Caddy (songa.ai / api.songa.ai)
   |              |
   v              v
songa-web     songa-cv-api
(Next.js)     (FastAPI)
  :3000          :8000
                  |
         volumes: uploads/
                  output/
                  models/
```

## Local setup

```bash
git clone https://github.com/dami3n/songa.git && cd songa
cp .env.example .env
docker compose -f docker-compose.dev.yml up
```

App available at `http://localhost:3000` — CV API at `http://localhost:8000`.

Hot reload is enabled for both services in dev mode.

## Production deploy

```bash
git push origin main
```

GitHub Actions runs lint + build checks, then auto-deploys to the Azure VM via SSH. No manual steps required.

To deploy manually on the VM:

```bash
cd /opt/apps/songa
git pull origin main
docker compose up --build -d
```

## CV Pipeline architecture

```
Video input (MP4 / stream)
        |
   [ Detector ]       YOLOv8 — player & ball detection
        |
   [ Tracker ]        ByteTrack — multi-object tracking across frames
        |
   [ StatsAggregator ] per-player distance, speed, zone touches, shot attempts
        |
   [ Exporter ]       JSON output → API response / volume
```

### API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Submit a video for processing |
| `GET` | `/jobs/{id}` | Poll job status |
| `GET` | `/results/{id}` | Retrieve processed stats |
| `GET` | `/health` | Health check |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | CV API base URL (browser) |
| `CV_API_URL` | `http://localhost:8000` | CV API base URL (server-side) |
| `DATABASE_URL` | — | PostgreSQL connection string (future) |
| `NEXTAUTH_SECRET` | — | Auth secret (future) |
| `NEXTAUTH_URL` | — | Auth callback URL (future) |

Copy `.env.example` to `.env` and fill in values before running.

## GitHub Actions secrets (required for auto-deploy)

| Secret | Value |
|---|---|
| `AZURE_VM_HOST` | VM public IP or hostname |
| `AZURE_VM_USER` | SSH username (e.g. `azureuser`) |
| `AZURE_VM_SSH_KEY` | Private SSH key (PEM format) |

## Running without GPU

On machines without NVIDIA drivers, use the CPU profile:

```bash
docker compose --profile cpu up
```

This starts `cv-api-cpu` without the GPU device reservation.
