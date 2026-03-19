#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
START_WAIT_SECONDS="${START_WAIT_SECONDS:-1}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-5}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-0.25}"

log() { echo "[start_system] $*"; }

log "checking health (${BASE_URL}/api/health)"
if bash scripts/agent_check.sh >/dev/null 2>&1; then
  log "OK: already running"
  exit 0
fi

log "starting canonical backend: financial-engine_v2/scripts/run_local_backend.sh"
LOG_FILE="${LOG_FILE:-/tmp/tenn_backend.log}"
bash financial-engine_v2/scripts/run_local_backend.sh >"${LOG_FILE}" 2>&1 &
BACKEND_PID=$!
log "backend_pid=${BACKEND_PID} log=${LOG_FILE}"

sleep "${START_WAIT_SECONDS}"

deadline_ms="$(( $(date +%s%3N) + (MAX_WAIT_SECONDS * 1000) ))"
while true; do
  if bash scripts/agent_check.sh >/dev/null 2>&1; then
    log "OK: backend reachable"
    exit 0
  fi

  if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    log "FAIL: backend process exited early (pid=${BACKEND_PID}). Last log lines:" >&2
    tail -n 30 "${LOG_FILE}" 2>/dev/null || true
    exit 1
  fi

  now_ms="$(date +%s%3N)"
  if [[ "${now_ms}" -ge "${deadline_ms}" ]]; then
    break
  fi

  sleep "${POLL_INTERVAL_SECONDS}"
done

log "FAIL: backend not reachable after start (pid=${BACKEND_PID}) within ${MAX_WAIT_SECONDS}s. Last log lines:" >&2
tail -n 30 "${LOG_FILE}" 2>/dev/null || true
exit 1

