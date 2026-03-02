#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cloud_env_common.sh"
cloud_env_init

log() {
  echo "[cloud-env-install] $*"
}

TMP_DIR=""
STARTED_OLLAMA=0
OLLAMA_PID=""

cleanup() {
  if [[ "${STARTED_OLLAMA}" -eq 1 && -n "${OLLAMA_PID}" ]]; then
    kill "${OLLAMA_PID}" >/dev/null 2>&1 || true
    wait "${OLLAMA_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

trap cleanup EXIT

if [[ ! -e "${CLOUD_ENV_REPO_ROOT}/.venv" && -d "/workspace/.venv" ]]; then
  ln -s /workspace/.venv "${CLOUD_ENV_REPO_ROOT}/.venv"
  log "linked ${CLOUD_ENV_REPO_ROOT}/.venv -> /workspace/.venv"
fi

VENV_PYTHON="/workspace/.venv/bin/python"
if [[ ! -x "${VENV_PYTHON}" ]]; then
  VENV_PYTHON="${CLOUD_ENV_REPO_ROOT}/.venv/bin/python"
fi
if [[ ! -x "${VENV_PYTHON}" ]]; then
  log "missing virtualenv python; expected /workspace/.venv/bin/python or ${CLOUD_ENV_REPO_ROOT}/.venv/bin/python"
  exit 1
fi

log "installing Python zstandard in shared venv"
"${VENV_PYTHON}" -m pip install --upgrade zstandard

OLLAMA_BIN="${HOME}/.local/bin/ollama"
if [[ ! -x "${OLLAMA_BIN}" ]]; then
  log "installing Ollama in user space"
  TAG="$(gh release view --repo ollama/ollama --json tagName --jq '.tagName')"
  OLLAMA_ASSET_URL="https://github.com/ollama/ollama/releases/download/${TAG}/ollama-linux-amd64.tar.zst"
  TMP_DIR="$(mktemp -d)"
  ARCHIVE_ZST="${TMP_DIR}/ollama-linux-amd64.tar.zst"
  ARCHIVE_TAR="${TMP_DIR}/ollama-linux-amd64.tar"

  curl -fsSL "${OLLAMA_ASSET_URL}" -o "${ARCHIVE_ZST}"
  "${VENV_PYTHON}" - "${ARCHIVE_ZST}" "${ARCHIVE_TAR}" <<'PY'
import sys

import zstandard

archive_zst = sys.argv[1]
archive_tar = sys.argv[2]

with open(archive_zst, "rb") as src, open(archive_tar, "wb") as dst:
    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_reader(src) as reader:
        while True:
            chunk = reader.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
PY

  rm -rf "${HOME}/.local/ollama"
  mkdir -p "${HOME}/.local/ollama"
  tar -xf "${ARCHIVE_TAR}" -C "${HOME}/.local/ollama"

  if [[ -x "${HOME}/.local/ollama/bin/ollama" ]]; then
    ln -sf "${HOME}/.local/ollama/bin/ollama" "${OLLAMA_BIN}"
  elif [[ -x "${HOME}/.local/ollama/ollama" ]]; then
    ln -sf "${HOME}/.local/ollama/ollama" "${OLLAMA_BIN}"
  else
    log "unable to locate ollama binary in ${HOME}/.local/ollama"
    exit 1
  fi
fi

if [[ ! -x "${OLLAMA_BIN}" ]]; then
  log "Ollama install did not produce ${OLLAMA_BIN}"
  exit 1
fi

if ! curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
  log "starting temporary ollama server for model pre-pull"
  OLLAMA_HOST="${OLLAMA_HOST}" OLLAMA_MODELS="${OLLAMA_MODELS}" "${OLLAMA_BIN}" serve >/tmp/ollama_bootstrap.log 2>&1 &
  OLLAMA_PID=$!
  STARTED_OLLAMA=1
  for _ in {1..90}; do
    if curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
  log "ollama failed to become ready at ${OLLAMA_URL}"
  exit 1
fi

if "${OLLAMA_BIN}" list | rg -Fq "${OLLAMA_BOOT_MODEL}"; then
  log "model already present: ${OLLAMA_BOOT_MODEL}"
else
  log "pulling model: ${OLLAMA_BOOT_MODEL}"
  if ! "${OLLAMA_BIN}" pull "${OLLAMA_BOOT_MODEL}"; then
    log "failed to pull ${OLLAMA_BOOT_MODEL}, trying ${OLLAMA_BOOT_MODEL_FALLBACK}"
    "${OLLAMA_BIN}" pull "${OLLAMA_BOOT_MODEL_FALLBACK}"
  fi
fi

if [[ "${STARTED_OLLAMA}" -eq 1 ]]; then
  log "stopping temporary ollama server"
fi

log "done"
