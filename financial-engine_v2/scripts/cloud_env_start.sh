#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cloud_env_common.sh"
cloud_env_init

log() {
  echo "[cloud-env-start] $*"
}

PROFILE_DIR="${HOME}/.config/financial_engine_v2"
PROFILE_FILE="${PROFILE_DIR}/cloud_env.sh"
BASHRC_FILE="${HOME}/.bashrc"
SOURCE_LINE='source "$HOME/.config/financial_engine_v2/cloud_env.sh"'

mkdir -p "${PROFILE_DIR}"
cat >"${PROFILE_FILE}" <<EOF
export OLLAMA_HOST="${OLLAMA_HOST}"
export OLLAMA_URL="${OLLAMA_URL}"
export DOCS_ROOT="${DOCS_ROOT}"
EOF

if [[ -f "${BASHRC_FILE}" ]]; then
  if ! rg -Fq "${SOURCE_LINE}" "${BASHRC_FILE}"; then
    {
      echo ""
      echo "# financial-engine_v2 Cursor Cloud defaults"
      echo "${SOURCE_LINE}"
    } >>"${BASHRC_FILE}"
  fi
else
  {
    echo "# financial-engine_v2 Cursor Cloud defaults"
    echo "${SOURCE_LINE}"
  } >"${BASHRC_FILE}"
fi

log "wrote shell defaults (OLLAMA_HOST=${OLLAMA_HOST}, DOCS_ROOT=${DOCS_ROOT})"
