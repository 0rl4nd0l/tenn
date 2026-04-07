#!/usr/bin/env bash
set -euo pipefail

LLAMA_SERVER_ENV_FILE="${LLAMA_SERVER_ENV_FILE:-${HOME}/.config/tenn/llama-server.env}"

load_launcher_defaults() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 0

  while IFS= read -r line; do
    local key="${line%%=*}"
    case "${key}" in
      LLAMA_SERVER_*|LLM_API_KEY)
        if [[ -z "${!key+x}" ]]; then
          export "${line}"
        fi
        ;;
    esac
  done < <(
    bash -c 'set -a; source "$1"; env' bash "${env_file}" 2>/dev/null
  )
}

load_launcher_defaults "${LLAMA_SERVER_ENV_FILE}"

LOCKFILE="${LOCKFILE:-/tmp/llama-server.lock}"
exec 200>"${LOCKFILE}"
if ! flock -n 200; then
  echo "ERROR: llama-server already running (lock at ${LOCKFILE})" >&2
  exit 1
fi
echo $$ > "${LOCKFILE}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_PATH="${LLAMA_SERVER_BIN:-${ROOT_DIR}/tools/llama.cpp/build-cuda/bin/llama-server}"
if [[ ! -x "${BIN_PATH}" ]]; then
  BIN_PATH_FALLBACK="${ROOT_DIR}/tools/llama.cpp/build/bin/llama-server"
  if [[ -x "${BIN_PATH_FALLBACK}" ]]; then
    BIN_PATH="${BIN_PATH_FALLBACK}"
  fi
fi

# Only kill llama-server processes bound to OUR port.
PORT="${LLAMA_SERVER_PORT:-8001}"
if pgrep -af "llama-server.*--port ${PORT}\\b" > /dev/null 2>&1; then
  echo "Killing existing llama-server on port ${PORT}"
  pkill -f "llama-server.*--port ${PORT}" || true
  sleep 2
fi
DEFAULT_MODEL_PATH="/mnt/nvme/tenn/models/Qwen3-30B-A3B-Instruct-2507-Q3_K_M.gguf"
MODEL_PATH="${LLAMA_SERVER_MODEL:-${DEFAULT_MODEL_PATH}}"
HF_MODEL="${LLAMA_SERVER_HF_REPO:-${LLAMA_SERVER_HF_MODEL:-${LLAMA_SERVER_HUGGINGFACE_REPO:-}}}"
MODEL_ALIAS="${LLAMA_SERVER_ALIAS:-qwen3-30b-a3b-instruct}"
API_KEY="${LLAMA_SERVER_API_KEY:-${LLM_API_KEY:-local-openai-key}}"
PROFILE="${LLAMA_SERVER_PROFILE:-balanced}"
HOST="${LLAMA_SERVER_HOST:-127.0.0.1}"
PORT="${LLAMA_SERVER_PORT:-8001}"

if [[ ! -x "${BIN_PATH}" ]]; then
  echo "llama-server binary not found at ${BIN_PATH}" >&2
  echo "Build llama.cpp first (e.g. scripts/build_llama_cpp.sh) or set LLAMA_SERVER_BIN to a valid executable path." >&2
  exit 1
fi

if [[ -n "${HTTPS_PROXY:-${https_proxy:-}}" ]] || [[ -n "${HTTP_PROXY:-${http_proxy:-}}" ]]; then
  echo "[llama-server] NOTE: proxy environment detected. If HF downloads fail, configure allow-list/auth in your proxy." >&2
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
  # KV cache quantization: halves KV VRAM at negligible quality cost (q8_0 ~ f16)
  --cache-type-k q8_0 --cache-type-v q8_0
  --spec-type ngram-simple
)

supports_flag() {
  local flag="$1"
  "${BIN_PATH}" --help 2>&1 | grep -q -- "${flag}"
}

# Router mode (DEFAULT): --models-dir serves all GGUFs in a directory,
# loading one at a time (--models-max 1). Clients select model per-request.
# Set LLAMA_SERVER_ROUTER_MODE=0 to fall back to single-model mode.
ROUTER_MODE="${LLAMA_SERVER_ROUTER_MODE:-1}"
DEFAULT_MODELS_DIR="/mnt/nvme/tenn/models"
MODELS_DIR="${LLAMA_SERVER_MODELS_DIR:-${DEFAULT_MODELS_DIR}}"
PRESET_PATH="${LLAMA_SERVER_PRESET:-${HOME}/.config/tenn/llamacpp-presets.ini}"

echo "[llama-server] ROUTER_MODE_REQUESTED=${ROUTER_MODE}"

if [[ "${ROUTER_MODE}" == "1" ]]; then
  if [[ ! -d "${MODELS_DIR}" ]]; then
    echo "[llama-server] models dir not found at ${MODELS_DIR}" >&2
    echo "[llama-server] Set LLAMA_SERVER_MODELS_DIR to an existing NVMe-backed GGUF directory." >&2
    exit 1
  fi
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
  # Single-model fallback (set LLAMA_SERVER_ROUTER_MODE=0 to use).
  if [[ -n "${HF_MODEL}" ]]; then
    if supports_flag "--hf"; then
      cmd+=(--hf "${HF_MODEL}")
      if [[ -z "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-${HF_HUB_TOKEN:-}}}" ]]; then
        echo "[llama-server] WARNING: no HF token detected (HF_TOKEN / HUGGING_FACE_HUB_TOKEN / HF_HUB_TOKEN)." >&2
        echo "[llama-server] Public models may still work; private or gated repos require a token." >&2
      fi
    else
      echo "[llama-server] WARNING: --hf is not supported by this llama-server build; falling back to local GGUF mode (-m)." >&2
      if [[ ! -f "${MODEL_PATH}" ]]; then
        echo "[llama-server] HF fallback failed: local model not found at ${MODEL_PATH}" >&2
        echo "[llama-server] Action: either upgrade llama-server to a build with --hf support, or set LLAMA_SERVER_MODEL to an existing local GGUF." >&2
        exit 1
      fi
      cmd+=(-m "${MODEL_PATH}")
    fi
  else
    cmd+=(-m "${MODEL_PATH}")
  fi
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
echo "[llama-server] MODEL_SOURCE=${HF_MODEL:+hf_repo|${HF_MODEL}, }${LLAMA_SERVER_MODEL:-${DEFAULT_MODEL_PATH}}"
echo "[llama-server] ROUTER_MODE=${ROUTER_MODE}"
echo "[llama-server] PROFILE=${PROFILE}"
echo "[llama-server] HOST=${HOST}"
echo "[llama-server] PORT=${PORT}"
cmd+=(--parallel 1)

if [[ -n "${HF_MODEL}" ]]; then
  echo "[llama-server] If startup fails with network/auth errors, check: (1) HF token scope, (2) proxy allow-list, (3) repo access permissions." >&2
fi

exec "${cmd[@]}"
