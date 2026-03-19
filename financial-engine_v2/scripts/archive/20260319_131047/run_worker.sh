#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$1" "$2"
}

trap 'log ERROR "Worker startup failed"' ERR
trap 'log STOP "Worker process stopped"' EXIT

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  log START "Dry run enabled - exiting"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/config/system.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

PROJECT_ROOT="${PROJECT_ROOT:-$ROOT_DIR}"
PROJECT_ROOT="${PROJECT_ROOT/#\~/$HOME}"
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
log START "Data root: ${DATA_ROOT}"
log START "Activating virtual environment: ${VENV_PATH}"
source "${VENV_ACTIVATE}"

cd "${PROJECT_ROOT}"
log START "Launching celery worker: app.celery_app.celery"
celery -A app.celery_app.celery worker --loglevel=INFO &
echo $! > /tmp/fe_worker.pid
wait
