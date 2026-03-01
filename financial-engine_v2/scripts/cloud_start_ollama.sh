#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cloud_env_common.sh"
cloud_env_init

log() {
  echo "[cloud-ollama] $*"
}

OLLAMA_BIN="${HOME}/.local/bin/ollama"
if [[ ! -x "${OLLAMA_BIN}" ]]; then
  OLLAMA_BIN="$(command -v ollama || true)"
fi

if [[ -z "${OLLAMA_BIN}" || ! -x "${OLLAMA_BIN}" ]]; then
  log "ollama binary not found; run ./financial-engine_v2/scripts/cloud_env_install.sh first"
  exit 1
fi

log "serving ${OLLAMA_URL} (models: ${OLLAMA_MODELS})"
exec env OLLAMA_HOST="${OLLAMA_HOST}" OLLAMA_MODELS="${OLLAMA_MODELS}" "${OLLAMA_BIN}" serve
