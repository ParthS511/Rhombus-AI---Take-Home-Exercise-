# Rhombus AI Take-Home Exercise

Django API for regex find/replace, async Celery jobs, Spark processing, and LLM-assisted regex generation.

## Stack

- **web** — Django REST API
- **worker** — Celery worker (Redis broker/backend)
- **postgres** — job persistence
- **redis** — Celery broker + result backend
- **PySpark runtime** — available inside the app/worker image for Spark engine jobs

## Local development with Docker

Prerequisites: Docker Desktop running.

```bash
docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| API | http://localhost:8000/api/ |
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

# LLM regex (uses Groq when GROQ_API_KEY is set; otherwise fallback)
curl -X POST http://localhost:8000/api/llm/regex/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"replace email addresses"}'

# Async job with Spark engine
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"input_text":"Order 123","pattern":"\\d+","replacement":"#","engine":"spark"}'
```

Optional: set `GROQ_API_KEY` in your environment to use Groq instead of fallback patterns. You can also set `GROQ_MODEL`; it defaults to `llama-3.1-8b-instant`.

## Backend Behavior

- `POST /api/jobs/` creates a persisted queued job and immediately returns `202` with a job ID.
- `GET /api/jobs/<id>/` polls status, progress, task ID, error message, and result metadata.
- `GET /api/jobs/<id>/result/` returns processed output as paginated rows.
- `POST /api/jobs/<id>/cancel/` best-effort cancels queued/running work by revoking the Celery task and marking the job `canceled`.
- Jobs use statuses `pending`, `running`, `succeeded`, `failed`, and `canceled`; `pending` is the queue state.

## Celery, Redis, And Caching

Celery uses Redis as both broker and result backend:

```text
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

The LLM regex layer also uses Redis as a cache in Docker/Render:

```text
REDIS_CACHE_URL=redis://redis:6379/2
```

LLM regex outputs are cached by normalized prompt plus model, so repeated natural-language prompts reuse the previous regex instead of calling Groq again. Celery tasks update job progress in the database, use Celery `PROGRESS` state updates at task start, and retry transient failures up to three times with exponential backoff. Invalid or unsafe regex patterns fail fast without retry.

## Spark Processing

CSV uploads are saved by the web process and processed asynchronously by Celery. Spark reads the uploaded CSV with header/schema inference, applies `regexp_replace` as a column transformation over the selected target columns, writes the full result to Parquet under `MEDIA_ROOT/results/job_<id>/`, and stores only a small CSV preview for browser pagination.

The Spark path uses DataFrame transformations instead of pandas row loops. In local Docker it runs with `local[*]`, allowing Spark to parallelize work across available cores and input partitions; on a real cluster the same DataFrame transformation can scale horizontally by changing the Spark master/deployment configuration. The current implementation supports CSV files; Excel upload parsing is not implemented.

## Assessment Coverage

Covered:

- Django API, model persistence, job status/progress, result retrieval, and cancellation.
- Celery worker execution with Redis broker/result backend.
- Redis-backed LLM regex caching keyed by normalized prompt and model.
- Natural-language regex generation through Groq when configured, with deterministic fallback patterns for local testing.
- Regex validation/safety checks before execution.
- PySpark CSV processing with DataFrame transformations over selected target columns.
- Paginated frontend result viewing instead of returning full large outputs to the browser.
- Docker Compose stack for Django, Celery, Postgres, Redis, and the Spark runtime.
- Tests for API behavior, job orchestration, safety checks, and Spark file processing.

Trade-offs:

- CSV uploads are implemented end-to-end. Excel upload parsing is noted as future work because Spark needs an additional Excel reader package or a conversion step.
- Progress is surfaced at key pipeline milestones. Per-partition row-level progress would require a more involved Spark progress listener.
- The deployment skeleton is included, but a public URL and demo video should be added before final submission if required by the evaluator.

## Deploy skeleton (Render)

The repo includes `render.yaml` for a hosted skeleton (web service with an embedded Celery worker + Postgres + Redis). Spark runs in local mode through the PySpark runtime included in the Docker image.

1. Push this repo to GitHub.
2. In [Render](https://render.com), create a **Blueprint** from the repo.
3. Set `GROQ_API_KEY` in the Render dashboard (optional, but required for real LLM use).
4. Deploy — Render runs `render-start.sh`, which applies migrations, starts Celery, and starts gunicorn on the web service.

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

If Spark fails to start, confirm Java is available in the image and check the worker logs.
