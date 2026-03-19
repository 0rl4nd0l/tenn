#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-3}"

# Exit 2 when the runtime forbids socket creation (sandboxed/offline environments).
if command -v python3 >/dev/null 2>&1; then
  if ! python3 - <<'PY' >/dev/null 2>&1
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.close()
PY
  then
    echo "[agent_check] SKIP due restricted environment: socket operations are not permitted."
    exit 2
  fi
fi

if curl -fsS --connect-timeout "${TIMEOUT_SECONDS}" --max-time "${TIMEOUT_SECONDS}" "${BASE_URL}/api/health" >/dev/null; then
  echo "[agent_check] OK: backend reachable (${BASE_URL}/api/health)"
  exit 0
fi

echo "[agent_check] FAIL: backend not reachable (${BASE_URL}/api/health)" >&2
exit 1
