# Rhombus AI Take-Home Exercise

Django API for regex find/replace, async Celery jobs, Spark processing, and LLM-assisted regex generation.

## Stack

- **web** — Django REST API
- **worker** — Celery worker (Redis broker/backend)
- **postgres** — job persistence
- **redis** — Celery broker + result backend
- **spark + spark-worker** — standalone Spark cluster for Spark engine jobs

## Local development with Docker

Prerequisites: Docker Desktop running.

```bash
docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| API | http://localhost:8000/api/ |
| Spark UI | http://localhost:8080/ |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

### Verify everything is wired

In another terminal:

```bash
chmod +x scripts/docker-verify.sh
./scripts/docker-verify.sh
```

This checks:

1. `GET /api/health/`
2. `POST /api/tasks/ping/` — proves web → Redis → Celery worker → Redis → web
3. `POST /api/llm/regex/` — LLM fallback without an API key
4. `POST /api/regex/` — synchronous regex replace

Watch the worker handle ping:

```bash
docker compose logs -f worker
```

### Manual curl examples

```bash
# Celery ping (returns pong when worker is healthy)
curl -X POST http://localhost:8000/api/tasks/ping/

# LLM regex (fallback without OPENAI_API_KEY)
curl -X POST http://localhost:8000/api/llm/regex/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"replace email addresses"}'

# Async job with Spark engine
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"input_text":"Order 123","pattern":"\\d+","replacement":"#","engine":"spark"}'
```

Optional: set `OPENAI_API_KEY` in `docker-compose.yml` under `web` / `worker` to use the real LLM instead of fallback patterns.

## Deploy skeleton (Render)

The repo includes `render.yaml` for a hosted skeleton (web + Celery worker + Postgres + Redis). Spark runs locally via Docker Compose only.

1. Push this repo to GitHub.
2. In [Render](https://render.com), create a **Blueprint** from the repo.
3. Set `OPENAI_API_KEY` in the Render dashboard (optional).
4. Deploy — Render runs migrations and starts gunicorn on the web service.

Health check: `GET /api/health/`

## Run tests without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend/locallibrary
python manage.py test jobs
```

## Troubleshooting Docker Desktop

If `docker compose up` fails with blob / I/O errors:

1. Quit Docker Desktop completely.
2. Open Docker Desktop → **Troubleshoot** → **Clean / Purge data** (or restart).
3. Retry `docker compose up --build`.

If Spark fails to start, confirm port `8080` and `7077` are free.
