#!/usr/bin/env bash
set -euo pipefail

LOCKFILE="${LOCKFILE:-/tmp/llama-server.lock}"
if [[ -f "${LOCKFILE}" ]]; then
  LOCK_PID="$(cat "${LOCKFILE}" 2>/dev/null || true)"
  if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
    echo "ERROR: llama-server already running (PID ${LOCK_PID}, lock at ${LOCKFILE})" >&2
    exit 1
  fi
  echo "Removing stale lock ${LOCKFILE}"
  rm -f "${LOCKFILE}"
fi
trap 'rm -f "${LOCKFILE}"' EXIT
echo $$ > "${LOCKFILE}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_PATH="${LLAMA_SERVER_BIN:-${ROOT_DIR}/tools/llama.cpp/build-cuda/bin/llama-server}"
if [[ ! -x "${BIN_PATH}" ]]; then
  BIN_PATH_FALLBACK="${ROOT_DIR}/tools/llama.cpp/build/bin/llama-server"
  if [[ -x "${BIN_PATH_FALLBACK}" ]]; then
    BIN_PATH="${BIN_PATH_FALLBACK}"
  fi
fi

# Only kill llama-server processes bound to OUR port (not the extraction server).
PORT="${LLAMA_SERVER_PORT:-8001}"
if pgrep -af "llama-server.*--port ${PORT}\\b" > /dev/null 2>&1; then
  echo "Killing existing llama-server on port ${PORT}"
  pkill -f "llama-server.*--port ${PORT}" || true
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
elif [[ "${LLAMA_SERVER_ROUTER_MODE:-0}" != "1" ]] && [[ ! -f "${MODEL_PATH}" ]]; then
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
)

# Router mode: --models-dir replaces -m for zero-downtime model switching.
# Set LLAMA_SERVER_ROUTER_MODE=1 to enable.
ROUTER_MODE="${LLAMA_SERVER_ROUTER_MODE:-0}"
MODELS_DIR="${LLAMA_SERVER_MODELS_DIR:-${ROOT_DIR}/models}"
PRESET_PATH="${LLAMA_SERVER_PRESET:-${HOME}/.config/tenn/llamacpp-presets.ini}"

echo "[llama-server] ROUTER_MODE_REQUESTED=${ROUTER_MODE}"

if [[ "${ROUTER_MODE}" == "1" ]]; then
  # Verify the binary supports --models-dir.
  if "${BIN_PATH}" --help 2>&1 | grep -q 'models-dir'; then
    cmd+=(--models-dir "${MODELS_DIR}" --models-max 1)
    if [[ -f "${PRESET_PATH}" ]]; then
      cmd+=(--models-preset "${PRESET_PATH}")
    fi
    echo "[llama-server] ROUTER_MODE=enabled (models-dir=${MODELS_DIR})"
  else
    echo "[llama-server] WARNING: binary does not support --models-dir, falling back to single-model mode" >&2
    echo "[llama-server] ROUTER_MODE=disabled (unsupported binary)"
    ROUTER_MODE=0
  fi
fi

if [[ "${ROUTER_MODE}" != "1" ]]; then
  # Single-model mode (original behavior).
  if [[ -n "${HF_MODEL}" ]]; then
    cmd+=(--hf "${HF_MODEL}")
  else
    cmd+=(-m "${MODEL_PATH}")
  fi
  cmd+=(--pooling mean --embeddings)
  if [[ -n "${MODEL_ALIAS}" ]]; then
    cmd+=(-a "${MODEL_ALIAS}")
  fi
  echo "[llama-server] ROUTER_MODE=disabled (single-model)"
fi

# mmap is enabled by default in this llama.cpp build. That keeps the model
# on the kernel page-cache path, which uses prefetch/readahead during startup.
if [[ "${LLAMA_SERVER_MMAP:-1}" == "0" ]]; then
  cmd+=(--no-mmap)
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
cmd+=(--parallel 1)

exec "${cmd[@]}"
