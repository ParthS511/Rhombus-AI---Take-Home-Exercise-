# Rhombus Frontend

React/Vite interface for the NL-to-regex processing backend.

## Run Locally

Start the backend first:

```bash
docker compose up --build
```

Then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Use The Render Backend

```bash
cd frontend
VITE_API_BASE=https://regex-web.onrender.com npm run dev
```

## Features

- CSV upload with local header detection.
- Natural-language pattern prompt and replacement value.
- Target-column selection from the CSV header.
- Groq regex preview.
- Async job creation, polling, progress, cancellation, and recent-job list.
- Paginated processed results.
- Small regex sandbox for quick backend checks.
