#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtualenv at $ROOT_DIR/.venv"
  echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt -r worker/requirements.txt"
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/backend"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./data/fe_local.db}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-memory://}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-cache+memory://}"
export QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
export QDRANT_COLLECTION="${QDRANT_COLLECTION:-asx_docs}"
export DOCS_ROOT="${DOCS_ROOT:-${ROOT_DIR}/data/asx/docs}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export OLLAMA_URL="${OLLAMA_URL:-http://${OLLAMA_HOST}}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export EXTRACT_MODEL="${EXTRACT_MODEL:-llama3:latest}"
export TASK_MODE="${TASK_MODE:-sync}"
export AUTO_CREATE_TABLES="${AUTO_CREATE_TABLES:-true}"
export ENABLE_EMBEDDINGS="${ENABLE_EMBEDDINGS:-false}"
export ENABLE_QDRANT="${ENABLE_QDRANT:-false}"
export ENABLE_EXTRACTION="${ENABLE_EXTRACTION:-false}"
export ENABLE_MARKETINDEX_FALLBACK="${ENABLE_MARKETINDEX_FALLBACK:-true}"
export MARKETINDEX_ANNOUNCEMENTS_FILE="${MARKETINDEX_ANNOUNCEMENTS_FILE:-../data/raw/marketindex_announcements.json}"

mkdir -p "${DOCS_ROOT}"

exec "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
