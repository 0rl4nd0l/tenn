#!/usr/bin/env bash
set -euo pipefail

LOCKFILE="${LOCKFILE:-/tmp/llama-server.lock}"
if [[ -f "${LOCKFILE}" ]]; then
  if ! pgrep -f llama-server > /dev/null; then
    echo "Removing stale lock ${LOCKFILE}"
    rm -f "${LOCKFILE}"
  else
    echo "ERROR: llama-server already running (lock exists at ${LOCKFILE})" >&2
    exit 1
  fi
fi
trap 'rm -f "${LOCKFILE}"' EXIT
touch "${LOCKFILE}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_PATH="${LLAMA_SERVER_BIN:-${ROOT_DIR}/tools/llama.cpp/build-cuda/bin/llama-server}"
if [[ ! -x "${BIN_PATH}" ]]; then
  BIN_PATH_FALLBACK="${ROOT_DIR}/tools/llama.cpp/build/bin/llama-server"
  if [[ -x "${BIN_PATH_FALLBACK}" ]]; then
    BIN_PATH="${BIN_PATH_FALLBACK}"
  fi
fi

if pgrep -f llama-server > /dev/null; then
  echo "Killing existing llama-server processes"
  pkill -f llama-server
  sleep 2
fi
MODEL_PATH="${LLAMA_SERVER_MODEL:-${ROOT_DIR}/models/model.gguf}"
HF_MODEL="${LLAMA_SERVER_HF_REPO:-${LLAMA_SERVER_HF_MODEL:-${LLAMA_SERVER_HUGGINGFACE_REPO:-}}}"
MODEL_ALIAS="${LLAMA_SERVER_ALIAS:-qwen2.5-coder-14b}"
API_KEY="${LLAMA_SERVER_API_KEY:-${LLM_API_KEY:-local-openai-key}}"
PROFILE="${LLAMA_SERVER_PROFILE:-balanced}"
HOST="${LLAMA_SERVER_HOST:-127.0.0.1}"
PORT="${LLAMA_SERVER_PORT:-8001}"

if [[ ! -x "${BIN_PATH}" ]]; then
  echo "llama-server binary not found at ${BIN_PATH}" >&2
  exit 1
fi

if [[ -n "${HF_MODEL}" ]]; then
  echo "[llama-server] using Hugging Face model ref=${HF_MODEL}"
  echo "[llama-server] Set LLAMA_SERVER_HF_REPO or LLAMA_SERVER_HF_MODEL to use this mode." >&2
  :
elif [[ ! -f "${MODEL_PATH}" ]]; then
  echo "Model not found at ${MODEL_PATH}" >&2
  echo "Set LLAMA_SERVER_MODEL to an existing GGUF file, or set LLAMA_SERVER_HF_REPO to pull a Hugging Face GGUF." >&2
  exit 1
fi

case "${PROFILE}" in
  interactive)
    default_ctx_size=8192
    default_batch_size=512
    default_ubatch_size=256
    ;;
  balanced)
    default_ctx_size=16384
    default_batch_size=1024
    default_ubatch_size=512
    ;;
  throughput)
    default_ctx_size=32768
    default_batch_size=2048
    default_ubatch_size=512
    ;;
  *)
    echo "Unsupported LLAMA_SERVER_PROFILE '${PROFILE}'." >&2
    echo "Use one of: interactive, balanced, throughput." >&2
    exit 1
    ;;
esac

cmd=(
  "${BIN_PATH}"
  --ctx-size "${LLAMA_SERVER_CTX_SIZE:-${default_ctx_size}}"
  --batch-size "${LLAMA_SERVER_BATCH_SIZE:-${default_batch_size}}"
  --ubatch-size "${LLAMA_SERVER_UBATCH_SIZE:-${default_ubatch_size}}"
  --n-gpu-layers "${LLAMA_SERVER_N_GPU_LAYERS:-999}"
  --main-gpu "${LLAMA_SERVER_MAIN_GPU:-0}"
  --threads "${LLAMA_SERVER_THREADS:-4}"
  --host "${HOST}"
  --port "${PORT}"
  --pooling mean
  --embeddings
)

if [[ -n "${HF_MODEL}" ]]; then
  cmd+=(--hf "${HF_MODEL}")
else
  cmd+=(-m "${MODEL_PATH}")
fi

# mmap is enabled by default in this llama.cpp build. That keeps the model
# on the kernel page-cache path, which uses prefetch/readahead during startup.
if [[ "${LLAMA_SERVER_MMAP:-1}" == "0" ]]; then
  cmd+=(--no-mmap)
fi

if [[ -n "${MODEL_ALIAS}" ]]; then
  cmd+=(-a "${MODEL_ALIAS}")
fi

if [[ -n "${API_KEY}" ]]; then
  cmd+=(--api-key "${API_KEY}")
fi

echo "Starting llama-server (PID $$)"
echo "[llama-server] BIN_PATH=${BIN_PATH}"
echo "[llama-server] MODEL_SOURCE=${HF_MODEL:+hf_repo|${HF_MODEL}, }${LLAMA_SERVER_MODEL:-${ROOT_DIR}/models/model.gguf}"
echo "[llama-server] PROFILE=${PROFILE}"
echo "[llama-server] HOST=${HOST}"
echo "[llama-server] PORT=${PORT}"
echo "[llama-server] EMBEDDINGS=enabled"
cmd+=(--parallel 1)

exec "${cmd[@]}"
