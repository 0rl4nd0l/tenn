#!/usr/bin/env bash

CLOUD_ENV_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cloud_env_init() {
  export PATH="${HOME}/.local/bin:${PATH}"
  export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
  export OLLAMA_URL="${OLLAMA_URL:-http://${OLLAMA_HOST}}"
  export DOCS_ROOT="${DOCS_ROOT:-${CLOUD_ENV_REPO_ROOT}/data/asx/docs}"
  export OLLAMA_MODELS="${OLLAMA_MODELS:-${HOME}/.ollama/models}"
  export OLLAMA_BOOT_MODEL="${OLLAMA_BOOT_MODEL:-qwen2.5:1.5b}"
  export OLLAMA_BOOT_MODEL_FALLBACK="${OLLAMA_BOOT_MODEL_FALLBACK:-qwen2.5:0.5b}"
  mkdir -p "${DOCS_ROOT}" "${OLLAMA_MODELS}" "${HOME}/.local/bin" "${HOME}/.local/ollama"
}
