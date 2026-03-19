#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$1" "$2"
}

trap 'log ERROR "Environment reset failed"' ERR
trap 'log STOP "Environment reset complete"' EXIT

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

kill_matching_pids() {
  local pattern="$1"
  local label="$2"
  local -a pids=()
  mapfile -t pids < <(
    pgrep -af "$pattern" 2>/dev/null \
      | grep "$PROJECT_ROOT" \
      | awk 'index($0, "reset_env.sh") == 0 {print $1}'
      || true
  )

  if (( ${#pids[@]} == 0 )); then
    log START "No ${label} process(es) found"
    return
  fi

  log START "Killing ${#pids[@]} ${label} process(es): ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
  sleep 1

  local -a remaining=()
  mapfile -t remaining < <(
    pgrep -af "$pattern" 2>/dev/null \
      | grep "$PROJECT_ROOT" \
      | awk 'index($0, "reset_env.sh") == 0 {print $1}'
      || true
  )
  if (( ${#remaining[@]} > 0 )); then
    kill -9 "${remaining[@]}" 2>/dev/null || true
  fi
}

log START "Reset using project root: ${PROJECT_ROOT}"
log START "Using virtual environment: ${VENV_PATH}"

kill_matching_pids "uvicorn .*app\.main:app" "uvicorn"
kill_matching_pids "celery .*app\.celery_app\.celery" "celery"

shopt -s nullglob
TMP_PATTERNS=(
  "/tmp/*financial-engine_v2*"
  "/tmp/*financial_engine_v2*"
  "/tmp/*tenn*financial-engine_v2*"
)

for pattern in "${TMP_PATTERNS[@]}"; do
  matches=( ${pattern} )
  for path in "${matches[@]}"; do
    if [[ -e "${path}" ]]; then
      rm -rf "${path}"
      log START "Removed /tmp artifact: ${path}"
    else
      log START "No /tmp artifact for pattern ${pattern}"
    fi
  done
done
shopt -u nullglob
