#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROFILE="${LOCAL_BACKEND_PROFILE:-isolated}"
RUNTIME_DB_FALLBACK="/tmp/financial-engine_v2-fe_local_runtime.db"

load_env_file() {
  local env_file="$1"
  if [[ -f "${env_file}" ]]; then
    echo "[run_local_backend] loading ${env_file}"
    # shellcheck disable=SC1090
    set -a
    source "${env_file}"
    set +a
  fi
}

remember_env_override() {
  local name="$1"
  if [[ -n "${!name+x}" ]]; then
    printf '1'
  else
    printf '0'
  fi
}

remember_env_value() {
  local name="$1"
  if [[ -n "${!name+x}" ]]; then
    printf '%s' "${!name}"
  fi
}

apply_if_not_overridden() {
  local name="$1"
  local value="$2"
  local preset="$3"
  if [[ "$preset" == "1" ]]; then
    return
  fi
  export "${name}=${value}"
}

sqlite_db_readable() {
  local db_url="$1"
  if [[ "$db_url" != sqlite:///* ]]; then
    return 0
  fi

  local db_path="${db_url#sqlite:///}"
  if [[ -z "$db_path" || "$db_path" == ":memory:" || "$db_path" == file:* ]]; then
    return 0
  fi

  python - <<PY >/dev/null 2>&1
import sqlite3
from pathlib import Path

db_path = Path(${db_path@Q})
try:
    conn = sqlite3.connect(str(db_path), timeout=1)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master LIMIT 1")
    cur.fetchone()
    conn.close()
except Exception:
    raise SystemExit(1)
PY
}

sqlite_dir_supports_writes() {
  local db_url="$1"
  if [[ "$db_url" != sqlite:///* ]]; then
    return 0
  fi

  local db_path="${db_url#sqlite:///}"
  if [[ -z "$db_path" || "$db_path" == ":memory:" || "$db_path" == file:* ]]; then
    return 0
  fi

  python - <<PY >/dev/null 2>&1
import sqlite3
from pathlib import Path

db_path = Path(${db_path@Q})
probe_path = db_path.parent / ".sqlite_write_probe.db"
try:
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(probe_path), timeout=1)
    cur = conn.cursor()
    cur.execute("create table if not exists probe (id integer primary key, value text)")
    conn.commit()
    conn.close()
    probe_path.unlink(missing_ok=True)
    journal_path = probe_path.with_name(probe_path.name + "-journal")
    journal_path.unlink(missing_ok=True)
except Exception:
    raise SystemExit(1)
PY
}

DATA_ROOT_PRESET="$(remember_env_override DATA_ROOT)"
DATABASE_URL_PRESET="$(remember_env_override DATABASE_URL)"
DOCS_ROOT_PRESET="$(remember_env_override DOCS_ROOT)"
TASK_MODE_PRESET="$(remember_env_override TASK_MODE)"
AUTO_CREATE_TABLES_PRESET="$(remember_env_override AUTO_CREATE_TABLES)"
ENABLE_EMBEDDINGS_PRESET="$(remember_env_override ENABLE_EMBEDDINGS)"
ENABLE_QDRANT_PRESET="$(remember_env_override ENABLE_QDRANT)"
ENABLE_EXTRACTION_PRESET="$(remember_env_override ENABLE_EXTRACTION)"
ENABLE_MARKETINDEX_FALLBACK_PRESET="$(remember_env_override ENABLE_MARKETINDEX_FALLBACK)"
REDIS_URL_PRESET="$(remember_env_override REDIS_URL)"
CELERY_BROKER_URL_PRESET="$(remember_env_override CELERY_BROKER_URL)"
CELERY_RESULT_BACKEND_PRESET="$(remember_env_override CELERY_RESULT_BACKEND)"
QDRANT_URL_PRESET="$(remember_env_override QDRANT_URL)"
OLLAMA_URL_PRESET="$(remember_env_override OLLAMA_URL)"
LLM_URL_PRESET="$(remember_env_override LLM_URL)"
LLAMACPP_URL_PRESET="$(remember_env_override LLAMACPP_URL)"
LLM_API_KEY_PRESET="$(remember_env_override LLM_API_KEY)"
EMBEDDING_API_KEY_PRESET="$(remember_env_override EMBEDDING_API_KEY)"
EMBED_MODEL_PRESET="$(remember_env_override EMBED_MODEL)"
EMBEDDING_MODEL_PRESET="$(remember_env_override EMBEDDING_MODEL)"
EXTRACT_MODEL_PRESET="$(remember_env_override EXTRACT_MODEL)"
ROUTER_FEEDBACK_ENABLED_PRESET="$(remember_env_override ROUTER_FEEDBACK_ENABLED)"
ANALYZER_MAX_AGE_SECONDS_PRESET="$(remember_env_override ANALYZER_MAX_AGE_SECONDS)"
MARKETINDEX_ANNOUNCEMENTS_FILE_PRESET="$(remember_env_override MARKETINDEX_ANNOUNCEMENTS_FILE)"

DATA_ROOT_VALUE="$(remember_env_value DATA_ROOT)"
DATABASE_URL_VALUE="$(remember_env_value DATABASE_URL)"
DOCS_ROOT_VALUE="$(remember_env_value DOCS_ROOT)"
TASK_MODE_VALUE="$(remember_env_value TASK_MODE)"
AUTO_CREATE_TABLES_VALUE="$(remember_env_value AUTO_CREATE_TABLES)"
ENABLE_EMBEDDINGS_VALUE="$(remember_env_value ENABLE_EMBEDDINGS)"
ENABLE_QDRANT_VALUE="$(remember_env_value ENABLE_QDRANT)"
ENABLE_EXTRACTION_VALUE="$(remember_env_value ENABLE_EXTRACTION)"
ENABLE_MARKETINDEX_FALLBACK_VALUE="$(remember_env_value ENABLE_MARKETINDEX_FALLBACK)"
REDIS_URL_VALUE="$(remember_env_value REDIS_URL)"
CELERY_BROKER_URL_VALUE="$(remember_env_value CELERY_BROKER_URL)"
CELERY_RESULT_BACKEND_VALUE="$(remember_env_value CELERY_RESULT_BACKEND)"
QDRANT_URL_VALUE="$(remember_env_value QDRANT_URL)"
OLLAMA_URL_VALUE="$(remember_env_value OLLAMA_URL)"
LLM_URL_VALUE="$(remember_env_value LLM_URL)"
LLAMACPP_URL_VALUE="$(remember_env_value LLAMACPP_URL)"
LLM_API_KEY_VALUE="$(remember_env_value LLM_API_KEY)"
EMBEDDING_API_KEY_VALUE="$(remember_env_value EMBEDDING_API_KEY)"
EMBED_MODEL_VALUE="$(remember_env_value EMBED_MODEL)"
EMBEDDING_MODEL_VALUE="$(remember_env_value EMBEDDING_MODEL)"
EXTRACT_MODEL_VALUE="$(remember_env_value EXTRACT_MODEL)"
ROUTER_FEEDBACK_ENABLED_VALUE="$(remember_env_value ROUTER_FEEDBACK_ENABLED)"
ANALYZER_MAX_AGE_SECONDS_VALUE="$(remember_env_value ANALYZER_MAX_AGE_SECONDS)"
MARKETINDEX_ANNOUNCEMENTS_FILE_VALUE="$(remember_env_value MARKETINDEX_ANNOUNCEMENTS_FILE)"

load_env_file "${ROOT_DIR}/.env"
load_env_file "${ROOT_DIR}/.env.local"

if [[ "${DATA_ROOT_PRESET}" == "1" ]]; then
  export "DATA_ROOT=${DATA_ROOT_VALUE}"
fi
apply_if_not_overridden DATABASE_URL "${DATABASE_URL:-}" "${DATABASE_URL_PRESET}"
if [[ "${DATABASE_URL_PRESET}" == "1" ]]; then
  export "DATABASE_URL=${DATABASE_URL_VALUE}"
fi
if [[ "${DOCS_ROOT_PRESET}" == "1" ]]; then
  export "DOCS_ROOT=${DOCS_ROOT_VALUE}"
fi
if [[ "${TASK_MODE_PRESET}" == "1" ]]; then
  export "TASK_MODE=${TASK_MODE_VALUE}"
fi
if [[ "${AUTO_CREATE_TABLES_PRESET}" == "1" ]]; then
  export "AUTO_CREATE_TABLES=${AUTO_CREATE_TABLES_VALUE}"
fi
if [[ "${ENABLE_EMBEDDINGS_PRESET}" == "1" ]]; then
  export "ENABLE_EMBEDDINGS=${ENABLE_EMBEDDINGS_VALUE}"
fi
if [[ "${ENABLE_QDRANT_PRESET}" == "1" ]]; then
  export "ENABLE_QDRANT=${ENABLE_QDRANT_VALUE}"
fi
if [[ "${ENABLE_EXTRACTION_PRESET}" == "1" ]]; then
  export "ENABLE_EXTRACTION=${ENABLE_EXTRACTION_VALUE}"
fi
if [[ "${ENABLE_MARKETINDEX_FALLBACK_PRESET}" == "1" ]]; then
  export "ENABLE_MARKETINDEX_FALLBACK=${ENABLE_MARKETINDEX_FALLBACK_VALUE}"
fi
if [[ "${REDIS_URL_PRESET}" == "1" ]]; then
  export "REDIS_URL=${REDIS_URL_VALUE}"
fi
if [[ "${CELERY_BROKER_URL_PRESET}" == "1" ]]; then
  export "CELERY_BROKER_URL=${CELERY_BROKER_URL_VALUE}"
fi
if [[ "${CELERY_RESULT_BACKEND_PRESET}" == "1" ]]; then
  export "CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND_VALUE}"
fi
if [[ "${QDRANT_URL_PRESET}" == "1" ]]; then
  export "QDRANT_URL=${QDRANT_URL_VALUE}"
fi
if [[ "${OLLAMA_URL_PRESET}" == "1" ]]; then
  export "OLLAMA_URL=${OLLAMA_URL_VALUE}"
fi
if [[ "${LLM_URL_PRESET}" == "1" ]]; then
  export "LLM_URL=${LLM_URL_VALUE}"
fi
if [[ "${LLAMACPP_URL_PRESET}" == "1" ]]; then
  export "LLAMACPP_URL=${LLAMACPP_URL_VALUE}"
fi
if [[ "${LLM_API_KEY_PRESET}" == "1" ]]; then
  export "LLM_API_KEY=${LLM_API_KEY_VALUE}"
fi
if [[ "${EMBEDDING_API_KEY_PRESET}" == "1" ]]; then
  export "EMBEDDING_API_KEY=${EMBEDDING_API_KEY_VALUE}"
fi
if [[ "${EMBED_MODEL_PRESET}" == "1" ]]; then
  export "EMBED_MODEL=${EMBED_MODEL_VALUE}"
fi
if [[ "${EMBEDDING_MODEL_PRESET}" == "1" ]]; then
  export "EMBEDDING_MODEL=${EMBEDDING_MODEL_VALUE}"
fi
if [[ "${EXTRACT_MODEL_PRESET}" == "1" ]]; then
  export "EXTRACT_MODEL=${EXTRACT_MODEL_VALUE}"
fi
if [[ "${ROUTER_FEEDBACK_ENABLED_PRESET}" == "1" ]]; then
  export "ROUTER_FEEDBACK_ENABLED=${ROUTER_FEEDBACK_ENABLED_VALUE}"
fi
if [[ "${ANALYZER_MAX_AGE_SECONDS_PRESET}" == "1" ]]; then
  export "ANALYZER_MAX_AGE_SECONDS=${ANALYZER_MAX_AGE_SECONDS_VALUE}"
fi
if [[ "${MARKETINDEX_ANNOUNCEMENTS_FILE_PRESET}" == "1" ]]; then
  export "MARKETINDEX_ANNOUNCEMENTS_FILE=${MARKETINDEX_ANNOUNCEMENTS_FILE_VALUE}"
fi

if ! command -v python >/dev/null 2>&1; then
  echo "python not found in PATH"
  echo "Activate your chosen venv first, then rerun this script."
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/backend${PYTHONPATH:+:${PYTHONPATH}}"
export DATA_ROOT="${DATA_ROOT:-./data}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${DATA_ROOT}/fe_local.db}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-${REDIS_URL}}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://127.0.0.1:6379/1}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
export QDRANT_COLLECTION="${QDRANT_COLLECTION:-asx_docs}"
export DOCS_ROOT="${DOCS_ROOT:-${DATA_ROOT}/asx/docs}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export LLM_URL="${LLM_URL:-http://127.0.0.1:8001}"
export LLAMACPP_URL="${LLAMACPP_URL:-http://127.0.0.1:8001/v1}"
export LLM_API_KEY="${LLM_API_KEY:-local-openai-key}"
export EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-${LLM_API_KEY}}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export EXTRACT_MODEL="${EXTRACT_MODEL:-llama3:latest}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-${EMBED_MODEL}}"
export LLM_MODEL="${LLM_MODEL:-${EXTRACT_MODEL}}"
export ROUTER_FEEDBACK_ENABLED="${ROUTER_FEEDBACK_ENABLED:-true}"
export ANALYZER_MAX_AGE_SECONDS="${ANALYZER_MAX_AGE_SECONDS:-600}"
export MARKETINDEX_ANNOUNCEMENTS_FILE="${MARKETINDEX_ANNOUNCEMENTS_FILE:-${DATA_ROOT}/raw/marketindex_announcements.json}"

case "${PROFILE}" in
  isolated)
    apply_if_not_overridden DATABASE_URL "sqlite:////tmp/financial-engine_v2-fe_local_runtime.db" "${DATABASE_URL_PRESET}"
    apply_if_not_overridden DOCS_ROOT "${DATA_ROOT}/asx/docs" "${DOCS_ROOT_PRESET}"
    apply_if_not_overridden TASK_MODE "sync" "${TASK_MODE_PRESET}"
    apply_if_not_overridden AUTO_CREATE_TABLES "true" "${AUTO_CREATE_TABLES_PRESET}"
    apply_if_not_overridden ENABLE_EMBEDDINGS "false" "${ENABLE_EMBEDDINGS_PRESET}"
    apply_if_not_overridden ENABLE_QDRANT "false" "${ENABLE_QDRANT_PRESET}"
    apply_if_not_overridden ENABLE_EXTRACTION "false" "${ENABLE_EXTRACTION_PRESET}"
    apply_if_not_overridden ENABLE_MARKETINDEX_FALLBACK "true" "${ENABLE_MARKETINDEX_FALLBACK_PRESET}"
    ;;
  full)
    apply_if_not_overridden DOCS_ROOT "${DATA_ROOT}/asx/docs" "${DOCS_ROOT_PRESET}"
    export TASK_MODE="${TASK_MODE:-sync}"
    export AUTO_CREATE_TABLES="${AUTO_CREATE_TABLES:-true}"
    export ENABLE_EMBEDDINGS="${ENABLE_EMBEDDINGS:-true}"
    export ENABLE_QDRANT="${ENABLE_QDRANT:-true}"
    export ENABLE_EXTRACTION="${ENABLE_EXTRACTION:-true}"
    export ENABLE_MARKETINDEX_FALLBACK="${ENABLE_MARKETINDEX_FALLBACK:-true}"
    # Embeddings route to Ollama (nomic-embed-text) — separate from llama.cpp instruct models
    export EMBEDDING_URL="${EMBEDDING_URL:-${OLLAMA_URL}}"
    ;;
  *)
    echo "Unsupported LOCAL_BACKEND_PROFILE='${PROFILE}'" >&2
    echo "Use one of: isolated, full" >&2
    exit 1
    ;;
esac

mkdir -p "${DOCS_ROOT}"

if [[ "${PROFILE}" == "isolated" && "${DATABASE_URL_PRESET}" == "0" ]]; then
  if ! sqlite_db_readable "${DATABASE_URL}" || ! sqlite_dir_supports_writes "${DATABASE_URL}"; then
    echo "[run_local_backend] isolated sqlite DB is not usable; switching to ${RUNTIME_DB_FALLBACK}"
    export DATABASE_URL="sqlite:///${RUNTIME_DB_FALLBACK#./}"
  fi
fi

echo "[run_local_backend] profile=${PROFILE}"
echo "[run_local_backend] data_root=${DATA_ROOT}"
echo "[run_local_backend] database=${DATABASE_URL}"
echo "[run_local_backend] docs_root=${DOCS_ROOT}"
echo "[run_local_backend] task_mode=${TASK_MODE}"
echo "[run_local_backend] embeddings=${ENABLE_EMBEDDINGS} qdrant=${ENABLE_QDRANT} extraction=${ENABLE_EXTRACTION}"
echo "[startup] LLAMACPP_URL=${LLAMACPP_URL}"
echo "[startup] EXTRACTION_LLAMACPP_URL=${EXTRACTION_LLAMACPP_URL:-<unset, falls back to LLAMACPP_URL>}"
echo "[startup] OLLAMA_URL=${OLLAMA_URL}"
echo "[startup] EMBEDDING_URL=${EMBEDDING_URL:-<unset, falls back to OLLAMA_URL>}"
echo "[startup] OLLAMA_NUM_GPU=${OLLAMA_NUM_GPU:-<unset>}"

# Warn if port is already occupied (e.g. Docker backend running)
BACKEND_PORT="${PORT:-8000}"
if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} " 2>/dev/null; then
  echo ""
  echo "⚠  WARNING: port ${BACKEND_PORT} is already in use."
  echo "   A Docker backend may be running. Stop it first:"
  echo "   docker compose stop backend"
  echo ""
fi

# Isolate backend to its own OpenViking workspace (operator override via OPENVIKING_CONFIG_FILE)
if [[ -z "${OPENVIKING_CONFIG_FILE:-}" ]]; then
  export OPENVIKING_CONFIG_FILE="${HOME}/.openviking/backend.ov.conf"
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
