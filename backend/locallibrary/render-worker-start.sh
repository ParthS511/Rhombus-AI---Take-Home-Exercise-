#!/usr/bin/env sh
set -eu

celery -A core worker --loglevel=info --pool=solo --concurrency=1 &
exec python -m http.server "${PORT}" --bind 0.0.0.0
