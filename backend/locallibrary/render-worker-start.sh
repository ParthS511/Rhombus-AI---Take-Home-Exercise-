#!/usr/bin/env sh
set -eu

exec celery -A core worker --loglevel=info --pool=solo --concurrency=1
