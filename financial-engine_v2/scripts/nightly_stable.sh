#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

LOG_DIR="${REPO_ROOT}/reports/ops_checks/nightly"
mkdir -p "${LOG_DIR}"
STAMP="$(date +%F_%H%M%S)"
LOG_FILE="${LOG_DIR}/nightly_stable_${STAMP}.log"

{
  echo "[nightly] started_at=$(date -Iseconds)"

  # Stable baseline toggles
  export TASK_MODE="${TASK_MODE:-sync}"
  export ENABLE_QDRANT="${ENABLE_QDRANT:-false}"
  export ENABLE_EMBEDDINGS="${ENABLE_EMBEDDINGS:-true}"
  export ENABLE_EXTRACTION="${ENABLE_EXTRACTION:-true}"
  export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
  export OLLAMA_GENERATE_NUM_CTX_DEFAULT="${OLLAMA_GENERATE_NUM_CTX_DEFAULT:-8192}"
  export OLLAMA_MODEL_CTX_CAPS_JSON="${OLLAMA_MODEL_CTX_CAPS_JSON:-{\"qwen2.5:32b\":8192,\"llama3:latest\":8192,\"llama3.1:8b\":8192}}"
  export EMBEDDING_CHUNK_MAX_CHARS="${EMBEDDING_CHUNK_MAX_CHARS:-3000}"
  export EMBEDDING_CHUNK_OVERLAP_CHARS="${EMBEDDING_CHUNK_OVERLAP_CHARS:-250}"

  echo "[nightly] env: TASK_MODE=${TASK_MODE} ENABLE_QDRANT=${ENABLE_QDRANT} ENABLE_EMBEDDINGS=${ENABLE_EMBEDDINGS} ENABLE_EXTRACTION=${ENABLE_EXTRACTION}"
  echo "[nightly] env: OLLAMA_URL=${OLLAMA_URL} OLLAMA_GENERATE_NUM_CTX_DEFAULT=${OLLAMA_GENERATE_NUM_CTX_DEFAULT}"

  ./scripts/gpu_validate.sh
  ./scripts/healthcheck.sh

  python run.py

  echo "[nightly] finished_at=$(date -Iseconds)"
} | tee "${LOG_FILE}"

# Keep the most recent 30 nightly logs.
ls -1t "${LOG_DIR}"/nightly_stable_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f
