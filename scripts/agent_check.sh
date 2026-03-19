#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

if curl -fsS "${BASE_URL}/api/health" >/dev/null; then
  echo "[agent_check] OK: ${BASE_URL}/api/health reachable"
  exit 0
fi

echo "[agent_check] FAIL: ${BASE_URL}/api/health not reachable" >&2
exit 1

