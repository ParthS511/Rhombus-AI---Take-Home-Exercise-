#!/usr/bin/env sh
set -eu

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Checking API health..."
curl -sf "${BASE_URL}/api/health/" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'

echo "Checking Celery ping (web -> Redis -> worker -> Redis -> web)..."
PING_RESPONSE="$(curl -sf -X POST "${BASE_URL}/api/tasks/ping/")"
echo "${PING_RESPONSE}" | grep -Eq '"result"[[:space:]]*:[[:space:]]*"pong"'

echo "Checking LLM regex fallback..."
LLM_RESPONSE="$(curl -sf -X POST "${BASE_URL}/api/llm/regex/" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"replace email addresses"}')"
echo "${LLM_RESPONSE}" | grep -Eq '"source"[[:space:]]*:[[:space:]]*"fallback"'

echo "Checking regex replace endpoint..."
REGEX_RESPONSE="$(curl -sf -X POST "${BASE_URL}/api/regex/" \
  -H "Content-Type: application/json" \
  -d '{"text":"Order 123","pattern":"\\\\d+","replacement":"#"}')"
echo "${REGEX_RESPONSE}" | grep -Eq '"result"[[:space:]]*:[[:space:]]*"Order #"'

echo "All Docker verification checks passed."
