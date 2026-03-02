#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cloud_env_common.sh"
cloud_env_init

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
HEALTHCHECK_TIMEOUT_SECONDS="${HEALTHCHECK_TIMEOUT_SECONDS:-120}"

log() {
  echo "[cloud-startup-health] $*"
}

wait_for_endpoint() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local deadline
  deadline=$((SECONDS + timeout_seconds))
  while ((SECONDS < deadline)); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      log "${name}: ok (${url})"
      return 0
    fi
    sleep 1
  done
  log "${name}: failed (${url})"
  return 1
}

log "checking Ollama and backend startup health"
wait_for_endpoint "ollama tags" "${OLLAMA_URL}/api/tags" "${HEALTHCHECK_TIMEOUT_SECONDS}"
wait_for_endpoint "backend health" "${BACKEND_URL}/api/health" "${HEALTHCHECK_TIMEOUT_SECONDS}"
log "PASS"
