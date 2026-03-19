#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
START_WAIT_SECONDS="${START_WAIT_SECONDS:-1}"

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

if bash scripts/agent_check.sh >/dev/null 2>&1; then
  log "OK: backend reachable"
  exit 0
fi

log "FAIL: backend not reachable after start (pid=${BACKEND_PID}). See log: ${LOG_FILE}" >&2
exit 1

