#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROFILE="${LOCAL_BACKEND_PROFILE:-isolated}"
RUNTIME_DB_FALLBACK="/tmp/financial-engine_v2-fe_local_runtime.db"

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

  "$ROOT_DIR/.venv/bin/python" - <<PY >/dev/null 2>&1
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

  "$ROOT_DIR/.venv/bin/python" - <<PY >/dev/null 2>&1
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

DATABASE_URL_PRESET="$(remember_env_override DATABASE_URL)"
DOCS_ROOT_PRESET="$(remember_env_override DOCS_ROOT)"
TASK_MODE_PRESET="$(remember_env_override TASK_MODE)"
AUTO_CREATE_TABLES_PRESET="$(remember_env_override AUTO_CREATE_TABLES)"
ENABLE_EMBEDDINGS_PRESET="$(remember_env_override ENABLE_EMBEDDINGS)"
ENABLE_QDRANT_PRESET="$(remember_env_override ENABLE_QDRANT)"
ENABLE_EXTRACTION_PRESET="$(remember_env_override ENABLE_EXTRACTION)"
ENABLE_MARKETINDEX_FALLBACK_PRESET="$(remember_env_override ENABLE_MARKETINDEX_FALLBACK)"
QDRANT_URL_PRESET="$(remember_env_override QDRANT_URL)"
LLAMACPP_URL_PRESET="$(remember_env_override LLAMACPP_URL)"
LLM_API_KEY_PRESET="$(remember_env_override LLM_API_KEY)"
EMBEDDING_API_KEY_PRESET="$(remember_env_override EMBEDDING_API_KEY)"
EMBED_MODEL_PRESET="$(remember_env_override EMBED_MODEL)"
EMBEDDING_MODEL_PRESET="$(remember_env_override EMBEDDING_MODEL)"
EXTRACT_MODEL_PRESET="$(remember_env_override EXTRACT_MODEL)"
MARKETINDEX_ANNOUNCEMENTS_FILE_PRESET="$(remember_env_override MARKETINDEX_ANNOUNCEMENTS_FILE)"

DATABASE_URL_VALUE="$(remember_env_value DATABASE_URL)"
DOCS_ROOT_VALUE="$(remember_env_value DOCS_ROOT)"
TASK_MODE_VALUE="$(remember_env_value TASK_MODE)"
AUTO_CREATE_TABLES_VALUE="$(remember_env_value AUTO_CREATE_TABLES)"
ENABLE_EMBEDDINGS_VALUE="$(remember_env_value ENABLE_EMBEDDINGS)"
ENABLE_QDRANT_VALUE="$(remember_env_value ENABLE_QDRANT)"
ENABLE_EXTRACTION_VALUE="$(remember_env_value ENABLE_EXTRACTION)"
ENABLE_MARKETINDEX_FALLBACK_VALUE="$(remember_env_value ENABLE_MARKETINDEX_FALLBACK)"
QDRANT_URL_VALUE="$(remember_env_value QDRANT_URL)"
LLAMACPP_URL_VALUE="$(remember_env_value LLAMACPP_URL)"
LLM_API_KEY_VALUE="$(remember_env_value LLM_API_KEY)"
EMBEDDING_API_KEY_VALUE="$(remember_env_value EMBEDDING_API_KEY)"
EMBED_MODEL_VALUE="$(remember_env_value EMBED_MODEL)"
EMBEDDING_MODEL_VALUE="$(remember_env_value EMBEDDING_MODEL)"
EXTRACT_MODEL_VALUE="$(remember_env_value EXTRACT_MODEL)"
MARKETINDEX_ANNOUNCEMENTS_FILE_VALUE="$(remember_env_value MARKETINDEX_ANNOUNCEMENTS_FILE)"

if [[ -f "${ROOT_DIR}/.env.local" ]]; then
  echo "[run_local_backend] loading ${ROOT_DIR}/.env.local"
  # shellcheck disable=SC1091
  set -a
  source "${ROOT_DIR}/.env.local"
  set +a
fi

apply_if_not_overridden DATABASE_URL "${DATABASE_URL}" "${DATABASE_URL_PRESET}"
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
if [[ "${QDRANT_URL_PRESET}" == "1" ]]; then
  export "QDRANT_URL=${QDRANT_URL_VALUE}"
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
if [[ "${MARKETINDEX_ANNOUNCEMENTS_FILE_PRESET}" == "1" ]]; then
  export "MARKETINDEX_ANNOUNCEMENTS_FILE=${MARKETINDEX_ANNOUNCEMENTS_FILE_VALUE}"
fi

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
export DOCS_ROOT="${DOCS_ROOT:-./data/asx/docs}"
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export LLAMACPP_URL="${LLAMACPP_URL:-http://127.0.0.1:8001/v1}"
export LLM_API_KEY="${LLM_API_KEY:-local-openai-key}"
export EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-${LLM_API_KEY}}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export EXTRACT_MODEL="${EXTRACT_MODEL:-llama3:latest}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-${EMBED_MODEL}}"
export LLM_MODEL="${LLM_MODEL:-${EXTRACT_MODEL}}"
export MARKETINDEX_ANNOUNCEMENTS_FILE="${MARKETINDEX_ANNOUNCEMENTS_FILE:-../data/raw/marketindex_announcements.json}"

case "${PROFILE}" in
  isolated)
    apply_if_not_overridden DATABASE_URL "sqlite:////tmp/financial-engine_v2-fe_local_runtime.db" "${DATABASE_URL_PRESET}"
    apply_if_not_overridden DOCS_ROOT "./data/asx/docs" "${DOCS_ROOT_PRESET}"
    apply_if_not_overridden TASK_MODE "sync" "${TASK_MODE_PRESET}"
    apply_if_not_overridden AUTO_CREATE_TABLES "true" "${AUTO_CREATE_TABLES_PRESET}"
    apply_if_not_overridden ENABLE_EMBEDDINGS "false" "${ENABLE_EMBEDDINGS_PRESET}"
    apply_if_not_overridden ENABLE_QDRANT "false" "${ENABLE_QDRANT_PRESET}"
    apply_if_not_overridden ENABLE_EXTRACTION "false" "${ENABLE_EXTRACTION_PRESET}"
    apply_if_not_overridden ENABLE_MARKETINDEX_FALLBACK "true" "${ENABLE_MARKETINDEX_FALLBACK_PRESET}"
    ;;
  full)
    export TASK_MODE="${TASK_MODE:-sync}"
    export AUTO_CREATE_TABLES="${AUTO_CREATE_TABLES:-true}"
    export ENABLE_EMBEDDINGS="${ENABLE_EMBEDDINGS:-true}"
    export ENABLE_QDRANT="${ENABLE_QDRANT:-true}"
    export ENABLE_EXTRACTION="${ENABLE_EXTRACTION:-true}"
    export ENABLE_MARKETINDEX_FALLBACK="${ENABLE_MARKETINDEX_FALLBACK:-true}"
    ;;
  *)
    echo "Unsupported LOCAL_BACKEND_PROFILE='${PROFILE}'" >&2
    echo "Use one of: isolated, full" >&2
    exit 1
    ;;
esac

mkdir -p ./data/asx/docs

if [[ "${PROFILE}" == "isolated" && "${DATABASE_URL_PRESET}" == "0" ]]; then
  if ! sqlite_db_readable "${DATABASE_URL}" || ! sqlite_dir_supports_writes "${DATABASE_URL}"; then
    echo "[run_local_backend] isolated sqlite DB is not usable; switching to ${RUNTIME_DB_FALLBACK}"
    export DATABASE_URL="sqlite:///${RUNTIME_DB_FALLBACK#./}"
  fi
fi

echo "[run_local_backend] profile=${PROFILE}"
echo "[run_local_backend] database=${DATABASE_URL}"
echo "[run_local_backend] docs_root=${DOCS_ROOT}"
echo "[run_local_backend] embeddings=${ENABLE_EMBEDDINGS} qdrant=${ENABLE_QDRANT} extraction=${ENABLE_EXTRACTION}"

exec "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
