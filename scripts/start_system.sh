#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="${ROOT_DIR}/financial-engine_v2/.venv/bin"
if [[ -d "${VENV_BIN}" ]]; then
  export PATH="${VENV_BIN}:${PATH}"
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
export BASE_URL
START_WAIT_SECONDS="${START_WAIT_SECONDS:-30}"
START_INITIAL_DELAY_SECONDS="${START_INITIAL_DELAY_SECONDS:-1}"
START_MAX_DELAY_SECONDS="${START_MAX_DELAY_SECONDS:-5}"

log() { echo "[start_system] $*"; }

log "checking health (${BASE_URL}/api/health)"
if bash scripts/agent_check.sh >/dev/null 2>&1; then
  log "OK: already running"
  exit 0
else
  CHECK_RC=$?
  if [[ "${CHECK_RC}" -eq 2 ]]; then
    log "SKIP due restricted environment: health checks unavailable; proceeding with process-based startup check"
  fi
fi

log "starting canonical backend: financial-engine_v2/scripts/run_local_backend.sh"
LOG_FILE="${LOG_FILE:-/tmp/tenn_backend.log}"
nohup bash financial-engine_v2/scripts/run_local_backend.sh >"${LOG_FILE}" 2>&1 &
BACKEND_PID=$!
log "backend_pid=${BACKEND_PID} log=${LOG_FILE}"

elapsed=0
delay=${START_INITIAL_DELAY_SECONDS}
attempt=1
while (( elapsed < START_WAIT_SECONDS )); do
  log "readiness attempt=${attempt} elapsed=${elapsed}s/${START_WAIT_SECONDS}s"
  if bash scripts/agent_check.sh >/dev/null 2>&1; then
    log "OK: backend reachable"
    exit 0
  else
    CHECK_RC=$?
    if [[ "${CHECK_RC}" -eq 2 ]]; then
      if kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
        log "OK: backend process running (SKIP due restricted environment: health checks unavailable)"
        exit 0
      fi
    fi
  fi
  if ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    log "FAIL: backend process exited before readiness (pid=${BACKEND_PID}). See log: ${LOG_FILE}" >&2
    exit 1
  fi

  sleep_for=${delay}
  remaining=$((START_WAIT_SECONDS - elapsed))
  if (( sleep_for > remaining )); then
    sleep_for=${remaining}
  fi
  if (( sleep_for <= 0 )); then
    break
  fi

  sleep "${sleep_for}"
  elapsed=$((elapsed + sleep_for))
  if (( delay < START_MAX_DELAY_SECONDS )); then
    delay=$((delay * 2))
    if (( delay > START_MAX_DELAY_SECONDS )); then
      delay=${START_MAX_DELAY_SECONDS}
    fi
  fi
  attempt=$((attempt + 1))
done

log "FAIL: backend not reachable after start (pid=${BACKEND_PID}). See log: ${LOG_FILE}" >&2
exit 1
