#!/usr/bin/env sh
set -eu

python manage.py migrate
celery -A core worker --loglevel=info --concurrency=1 &
exec gunicorn core.wsgi:application --bind "0.0.0.0:${PORT}"
