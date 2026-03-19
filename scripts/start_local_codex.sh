#!/usr/bin/env bash
set -euo pipefail

PROVIDER="${LOCAL_CODEX_PROVIDER:-openai}"
MODEL="${CODEX_LOCAL_MODEL:-${LOCAL_CODEX_MODEL:-}}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
OPENAI_BASE_URL="${LOCAL_CODEX_OPENAI_BASE_URL:-http://127.0.0.1:8001/v1}"
OPENAI_API_KEY="${LOCAL_CODEX_OPENAI_API_KEY:-local-openai-key}"
WORKSPACE="${1:-$(pwd)}"

if [[ -z "${MODEL}" ]]; then
  if [[ "${PROVIDER}" == "ollama" ]]; then
    MODEL="qwen2.5-coder:14b"
  else
    MODEL="qwen2.5-coder-14b"
  fi
fi

echo "[local-codex] provider=${PROVIDER}"
echo "[local-codex] model=${MODEL}"
echo "[local-codex] workspace=${WORKSPACE}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[local-codex] error: python3 not found in PATH" >&2
  exit 1
fi

case "${PROVIDER}" in
  openai)
    echo "[local-codex] base_url=${OPENAI_BASE_URL}"
    exec python3 scripts/local_codex_agent.py \
      --model "${MODEL}" \
      --provider openai \
      --base-url "${OPENAI_BASE_URL}" \
      --api-key "${OPENAI_API_KEY}" \
      --workspace "${WORKSPACE}" \
      --all-files
    ;;
  ollama)
    if ! command -v ollama >/dev/null 2>&1; then
      echo "[local-codex] error: ollama not found in PATH" >&2
      exit 1
    fi

    if ! ollama list >/dev/null 2>&1; then
      echo "[local-codex] warning: could not reach Ollama, attempting to continue" >&2
    fi

    echo "[local-codex] ensuring model is available: ${MODEL}"
    ollama pull "${MODEL}"

    exec python3 scripts/local_codex_agent.py \
      --model "${MODEL}" \
      --provider ollama \
      --base-url "${OLLAMA_URL}" \
      --workspace "${WORKSPACE}" \
      --all-files
    ;;
  *)
    echo "[local-codex] error: unsupported LOCAL_CODEX_PROVIDER '${PROVIDER}'" >&2
    echo "[local-codex] use 'openai' for llama.cpp or 'ollama' for compatibility mode" >&2
    exit 1
    ;;
esac
