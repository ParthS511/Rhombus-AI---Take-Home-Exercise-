# Regex Pattern Matching and Replacement Web App

This is my take-home project for building an asynchronous regex processing app. It lets a user upload a CSV, describe a pattern in natural language, choose the target column(s), and run a backend pipeline that generates a regex, validates it, applies the replacement with Spark, and shows the processed result back in the browser.

The project is built around the same kind of architecture I would use for a real long-running data workflow: a web API for requests, a worker for background processing, Redis for queueing/caching, Postgres for job state, and PySpark for the actual transformation work.

## Demo

Live frontend:

```text
https://rhombus-ai-take-home-exercise-h3g6.vercel.app
```

Backend API:

```text
https://regex-web.onrender.com
```

Demo video:

[Watch the demo video](https://drive.google.com/file/d/12HsK-tP7QDmscW2skl8bwG_mcABLC3NH/view?usp=sharing)

Note: the hosted Render services can take a little while to wake up after being idle. The local Docker setup is the most reliable way to run the full stack exactly as intended.

## What It Does

- Uploads CSV files from the React frontend.
- Lets the user describe a regex pattern in natural language.
- Uses an LLM to generate a regex pattern when needed.
- Caches generated regex patterns in Redis so repeated prompts do not call the LLM again.
- Runs file processing asynchronously with Celery.
- Uses PySpark DataFrame transformations for regex replacement instead of row-by-row pandas loops.
- Stores job status, progress, errors, and result previews in Postgres.
- Lets the frontend poll job status and render paginated results once the job completes.
- Supports retry, failure handling, and best-effort cancellation.

## Tech Stack

- React + Vite
- Django + Django REST-style JSON endpoints
- Celery
- Redis
- Postgres
- PySpark
- Groq/OpenAI-compatible LLM client
- Docker Compose
- Vercel for the frontend
- Render for the hosted backend services

## Architecture

The app is split into five main pieces:

- **React frontend**: handles upload, prompt input, target-column selection, status polling, and result rendering.
- **Django API**: creates jobs, accepts uploads, dispatches Celery tasks, exposes status/result endpoints, and handles cancellation.
- **Celery worker**: performs regex generation and Spark processing outside the web request cycle.
- **Redis**: acts as the Celery broker/result backend and as the LLM regex cache.
- **Postgres**: stores job records, status, progress, task IDs, errors, and result metadata.

The flow is:

1. The user uploads a CSV and submits a prompt, replacement value, and target columns.
2. Django creates a job in Postgres.
3. Django queues a Celery task through Redis.
4. The Celery worker picks up the job.
5. If the user provided natural language, the LLM generates a regex.
6. The regex is validated before execution.
7. Spark reads the CSV and applies `regexp_replace` over the selected columns.
8. The worker saves a result preview and marks the job complete.
9. The frontend polls the API and displays the processed data.

## Why I Chose This Architecture

I used Celery because file parsing and Spark jobs should not run inside a normal web request. The API should stay responsive while the worker handles heavier processing in the background.

I used Redis because it is a natural fit for Celery and also works well as a cache layer. In this project, LLM-generated regex patterns are cached by normalized prompt/model so repeated prompts can reuse the previous result.

I used PySpark because the core transformation should be expressed as a distributed DataFrame operation. The regex replacement is done with Spark's `regexp_replace`, which keeps the processing model scalable compared with iterating row by row in Python.

I used Postgres because job status and result metadata need to survive across requests and be available to the polling API.

## Local Setup

Prerequisites:

- Docker Desktop
- Node.js/npm if running the frontend separately

From the repo root:

```bash
docker compose up --build
```

This starts:

- Django API on `http://localhost:8000`
- Celery worker
- Redis
- Postgres
- PySpark runtime inside the app/worker image

Check the backend:

```bash
curl http://localhost:8000/api/health/
```

Expected:

```json
{"status":"ok"}
```

Check Celery/Redis:

```bash
curl -X POST http://localhost:8000/api/tasks/ping/
```

Expected:

```json
{"result":"pong"}
```

## Running The Frontend Locally

In a second terminal:

```bash
cd frontend
npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```

Then open the Vite URL, usually:

```text
http://localhost:5173
```

## Environment Variables

Backend:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<secret>
DJANGO_ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=<frontend-url>
POSTGRES_DB=<db-name>
POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<db-password>
POSTGRES_HOST=<db-host>
POSTGRES_PORT=5432
CELERY_BROKER_URL=<redis-url>
CELERY_RESULT_BACKEND=<redis-url>
REDIS_CACHE_URL=<redis-url>
GROQ_API_KEY=<optional-api-key>
GROQ_MODEL=llama-3.1-8b-instant
```

Frontend:

```text
VITE_API_BASE=<backend-api-url>
```

For the deployed frontend, I used:

```text
VITE_API_BASE=https://regex-web.onrender.com
```

## Spark Processing

For CSV uploads, Spark reads the uploaded file with headers enabled. The app keeps columns as strings to avoid unnecessary schema inference overhead.

The replacement is applied as a Spark transformation:

```text
regexp_replace(column, pattern, replacement)
```

This keeps the core replacement logic inside Spark instead of pulling the full dataset into pandas. In local Docker, the stack runs with a dedicated worker container and is the best environment for evaluating the complete Spark pipeline.

For the hosted demo, I optimized the Spark path to return a small preview quickly because free-tier hosting has tighter CPU/memory/runtime constraints.

## Progress, Failure, Retry, And Cancellation

Jobs use these statuses:

```text
pending
running
succeeded
failed
canceled
```

Progress is milestone-based. The API surfaces progress values through polling so the frontend can show the user whether the job is queued, running, or complete.

Celery retries transient failures with backoff. Invalid or unsafe regex patterns fail fast. Cancellation is supported by revoking the Celery task and marking the job as canceled, although Spark cancellation is best-effort once work has already started.

## Deployment

The frontend is deployed on Vercel.

The backend is deployed on Render with:

- `regex-web`: Django/Gunicorn API service
- `regex-worker`: Celery worker service
- `regex-redis`: Redis
- `regex-db`: Postgres

Important deployment variables:

```text
CORS_ALLOWED_ORIGINS=https://rhombus-ai-take-home-exercise-h3g6.vercel.app
VITE_API_BASE=https://regex-web.onrender.com
```

Render free-tier services can sleep after inactivity, so the first request after idle time may be slower. PySpark also has startup overhead because it launches a JVM.

## Manual API Checks

Backend health:

```bash
curl https://regex-web.onrender.com/api/health/
```

Celery/Redis ping:

```bash
curl -X POST https://regex-web.onrender.com/api/tasks/ping/
```

Local Spark job:

```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"input_text":"Order 123","pattern":"\\d+","replacement":"#","engine":"spark"}'
```

## Tests

With local Python dependencies installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/locallibrary/manage.py test jobs
```

Or inside Docker:

```bash
docker compose run --rm web python manage.py test jobs
```

## Trade-Offs

- CSV upload is implemented end-to-end. Excel upload support is not implemented yet.
- Progress is milestone-based rather than true row-level or partition-level Spark progress.
- The hosted Render deployment is constrained by free-tier CPU/memory/sleep behavior, so small demo files are best for the public URL.
- The local Docker Compose setup is the most reliable way to evaluate the complete async Spark pipeline.
- For production, I would store uploaded files and full processed outputs in object storage such as S3.
- For production-scale Spark, I would run Spark on a real cluster or managed Spark platform instead of local mode.

## Troubleshooting

If `docker compose up --build` fails with Docker blob or input/output errors, the issue is usually Docker Desktop's local image store rather than the app. The most reliable fix is:

1. Quit Docker Desktop.
2. Open Docker Desktop.
3. Go to Troubleshoot.
4. Run Clean / Purge data.
5. Restart Docker Desktop.
6. Run `docker compose up --build` again.

If Spark fails to start, check the worker logs and confirm Java is available in the image.
