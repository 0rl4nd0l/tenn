#!/usr/bin/env bash
# Dedicated llama.cpp instance for PDF extraction on port 8002.
# Runs the instruct model in single-model mode (no router).
# Safe to run alongside run_llama_server.sh (separate lockfile, no pkill).
set -euo pipefail

LOCKFILE="${LOCKFILE:-/tmp/llama-extraction-server.lock}"
if [[ -f "${LOCKFILE}" ]]; then
  LOCK_PID="$(cat "${LOCKFILE}" 2>/dev/null || true)"
  if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
    echo "ERROR: extraction server already running (PID ${LOCK_PID}, lock at ${LOCKFILE})" >&2
    exit 1
  fi
  echo "Removing stale lock ${LOCKFILE}"
  rm -f "${LOCKFILE}"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_PATH="${LLAMA_SERVER_BIN:-${ROOT_DIR}/tools/llama.cpp/build-cuda/bin/llama-server}"
if [[ ! -x "${BIN_PATH}" ]]; then
  BIN_PATH_FALLBACK="${ROOT_DIR}/tools/llama.cpp/build/bin/llama-server"
  if [[ -x "${BIN_PATH_FALLBACK}" ]]; then
    BIN_PATH="${BIN_PATH_FALLBACK}"
  fi
fi
if [[ ! -x "${BIN_PATH}" ]]; then
  echo "llama-server binary not found at ${BIN_PATH}" >&2
  exit 1
fi

# Defaults — override via env or ~/.config/tenn/llama-server.env
HOST="${EXTRACTION_SERVER_HOST:-127.0.0.1}"
PORT="${EXTRACTION_SERVER_PORT:-8002}"
MODEL_PATH="${EXTRACTION_SERVER_MODEL:-${ROOT_DIR}/models/qwen2.5-14b-instruct-q4_k_m.gguf}"
MODEL_ALIAS="${EXTRACTION_SERVER_ALIAS:-qwen2.5-14b-instruct}"
API_KEY="${LLAMA_SERVER_API_KEY:-${LLM_API_KEY:-local-openai-key}}"
CTX_SIZE="${EXTRACTION_SERVER_CTX_SIZE:-16384}"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "Extraction model not found at ${MODEL_PATH}" >&2
  echo "Set EXTRACTION_SERVER_MODEL to an existing GGUF file." >&2
  exit 1
fi

# Write PID to lockfile for clean detection
trap 'rm -f "${LOCKFILE}"' EXIT
echo $$ > "${LOCKFILE}"

cmd=(
  "${BIN_PATH}"
  -m "${MODEL_PATH}"
  -a "${MODEL_ALIAS}"
  --ctx-size "${CTX_SIZE}"
  --batch-size 1024
  --ubatch-size 512
  --n-gpu-layers 999
  --main-gpu 0
  --threads 4
  --host "${HOST}"
  --port "${PORT}"
  --parallel 1
)

# Same knob as scripts/run_llama_server.sh: mmap can stall CUDA load on Maxwell (M40).
if [[ "${LLAMA_SERVER_MMAP:-1}" == "0" ]]; then
  cmd+=(--no-mmap)
fi

if [[ -n "${API_KEY}" ]]; then
  cmd+=(--api-key "${API_KEY}")
fi

echo "[extraction-server] BIN_PATH=${BIN_PATH}"
echo "[extraction-server] MODEL=${MODEL_PATH}"
echo "[extraction-server] ALIAS=${MODEL_ALIAS}"
echo "[extraction-server] HOST=${HOST}:${PORT}"
echo "[extraction-server] CTX_SIZE=${CTX_SIZE}"
echo "[extraction-server] LLAMA_SERVER_MMAP=${LLAMA_SERVER_MMAP:-1} (0=--no-mmap)"

exec "${cmd[@]}"
