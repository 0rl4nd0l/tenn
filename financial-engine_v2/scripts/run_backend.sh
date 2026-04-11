#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$1" "$2"
}

trap 'log ERROR "Backend startup failed"' ERR
trap 'log STOP "Backend process stopped"' EXIT

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  log START "Dry run enabled - exiting"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TENN_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
if [[ -z "${PYTHON_BIN}" ]]; then
  log ERROR "python3 or python required for Tenn storage guard"
  exit 1
fi
"${PYTHON_BIN}" "${TENN_REPO}/scripts/storage_guard.py" || exit 1

ENV_FILE="${ROOT_DIR}/config/system.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

PROJECT_ROOT="${PROJECT_ROOT:-$ROOT_DIR}"
PROJECT_ROOT="${PROJECT_ROOT/#\~/$HOME}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
VENV_PATH="${VENV_PATH:-.venv}"
VENV_PATH="${VENV_PATH/#\~/$HOME}"
DATA_ROOT="${DATA_ROOT:-${PROJECT_ROOT}/data}"
DATA_ROOT="${DATA_ROOT/#\~/$HOME}"
if [[ "${VENV_PATH}" != /* ]]; then
  VENV_PATH="${PROJECT_ROOT%/}/${VENV_PATH}"
fi

export DATA_ROOT
export PYTHONPATH="${PROJECT_ROOT}/backend"

VENV_ACTIVATE="${VENV_PATH}/bin/activate"
if [[ ! -f "${VENV_ACTIVATE}" ]]; then
  log ERROR "Missing virtual environment at ${VENV_PATH}"
  exit 1
fi

log START "Project root: ${PROJECT_ROOT}"
log START "Backend port: ${BACKEND_PORT}"
log START "Data root: ${DATA_ROOT}"
log START "Activating virtual environment: ${VENV_PATH}"
source "${VENV_ACTIVATE}"

kill_existing_uvicorn() {
  local -a pids=()
  mapfile -t pids < <(
    pgrep -af "uvicorn .*app\.main:app" \
    | grep "$PROJECT_ROOT" \
    | awk '{print $1}'
  )
  if (( ${#pids[@]} == 0 )); then
    log START "No existing uvicorn processes to stop"
    return
  fi
  log START "Stopping existing uvicorn process(es): ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
  sleep 1
  for pid in "${pids[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  done
}

cd "${PROJECT_ROOT}"
kill_existing_uvicorn

sleep 1

if lsof -i :${BACKEND_PORT} >/dev/null 2>&1; then
  log ERROR "Port ${BACKEND_PORT} still in use after cleanup"
  exit 1
fi

log START "Launching backend on 127.0.0.1:${BACKEND_PORT}"
log START "Command: uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}"
uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
echo $! > /tmp/fe_backend.pid
wait
