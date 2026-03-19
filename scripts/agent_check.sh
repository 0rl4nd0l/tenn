#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-3}"

if curl -fsS --connect-timeout "${TIMEOUT_SECONDS}" --max-time "${TIMEOUT_SECONDS}" "${BASE_URL}/api/health" >/dev/null; then
  echo "[agent_check] OK: backend reachable (${BASE_URL}/api/health)"
  exit 0
fi

echo "[agent_check] FAIL: backend not reachable (${BASE_URL}/api/health)" >&2
exit 1

