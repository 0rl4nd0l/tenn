#!/usr/bin/env bash
# DEPRECATED: Standalone extraction server on port 8002.
#
# The canonical setup is now a SINGLE llama-server instance in router mode
# on port 8001 (see run_llama_server.sh). Extraction requests use the same
# port with model selection via the request body's "model" field.
#
# This script is kept for manual debugging or when you need to isolate
# extraction on a dedicated port. It is NOT started by the systemd service.
#
# To use the canonical single-instance setup instead:
#   LLAMA_SERVER_ROUTER_MODE=1 bash scripts/run_llama_server.sh
set -euo pipefail

LLAMA_SERVER_ENV_FILE="${LLAMA_SERVER_ENV_FILE:-${HOME}/.config/tenn/llama-server.env}"

load_launcher_defaults() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 0

  while IFS= read -r line; do
    local key="${line%%=*}"
    case "${key}" in
      LLAMA_SERVER_*|EXTRACTION_SERVER_*|LLM_API_KEY)
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
DEFAULT_MODEL_PATH="/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf"
MODEL_PATH="${EXTRACTION_SERVER_MODEL:-${DEFAULT_MODEL_PATH}}"
MODEL_ALIAS="${EXTRACTION_SERVER_ALIAS:-qwen2.5-14b-instruct}"
API_KEY="${LLAMA_SERVER_API_KEY:-${LLM_API_KEY:-local-openai-key}}"
# 8K context is sufficient — extraction prompts are clipped to ~18,000 chars (~4.5K tokens).
# Halved from 16K to reduce VRAM pressure when running dual 14B models on 24 GB M40.
CTX_SIZE="${EXTRACTION_SERVER_CTX_SIZE:-8192}"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "Extraction model not found at ${MODEL_PATH}" >&2
  echo "Set EXTRACTION_SERVER_MODEL to an existing NVMe-backed GGUF file." >&2
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
  # KV cache quantization: halves KV VRAM at negligible quality cost (q8_0 ~ f16)
  --cache-type-k q8_0 --cache-type-v q8_0
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
