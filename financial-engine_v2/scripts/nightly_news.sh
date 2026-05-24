#!/usr/bin/env bash
# Nightly news ingestion — fetches the last 36 hours of ASX news via newspaper4k.
# Scheduled via crontab: 0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
set -euo pipefail

TENN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# newspaper4k requires its own isolated venv — the main tenn venv does not have it.
VENV="${TENN_ROOT}/integrations/newspaper4k_au/.venv"
if [[ ! -f "${VENV}/bin/activate" ]]; then
  echo "[nightly_news] ERROR: newspaper4k venv not found at ${VENV}" >&2
  echo "[nightly_news] Run: python3 -m venv ${VENV} && ${VENV}/bin/pip install -r ${TENN_ROOT}/integrations/newspaper4k_au/requirements.txt" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

# Add scripts/ to PYTHONPATH so news_pipeline package resolves correctly.
export PYTHONPATH="${TENN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}"

LOG_DIR="${TENN_ROOT}/reports/ops_checks/nightly"
mkdir -p "${LOG_DIR}"
STAMP="$(date +%F_%H%M%S)"
LOG_FILE="${LOG_DIR}/nightly_news_${STAMP}.log"
SUMMARY_FILE="${LOG_DIR}/nightly_news_${STAMP}.summary.json"
MEMO_BACKFILL_SUMMARY_FILE="${LOG_DIR}/nightly_news_${STAMP}.memo_backfill.summary.json"

{
  echo "[nightly_news] started_at=$(date -Iseconds)"
  echo "[nightly_news] phase=fetch python=$(which python3) venv=${VENV}"

  python3 "${TENN_ROOT}/scripts/fetch_daily_news.py" \
    --providers newspaper4k \
    --since-hours 36 \
    --lane high_precision

  # --- Phase 2: Sync to Qdrant & Trigger Extraction ---
  echo "[nightly_news] phase=sync started_at=$(date -Iseconds)"
  
  # We need the backend venv for this step
  BACKEND_VENV="${TENN_ROOT}/financial-engine_v2/.venv"
  if [[ -f "${BACKEND_VENV}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${BACKEND_VENV}/bin/activate"
    echo "[nightly_news] phase=sync python=$(which python3) venv=${BACKEND_VENV}"
    
    # Add backend to PYTHONPATH for app.* imports
    export PYTHONPATH="${TENN_ROOT}/financial-engine_v2/backend:${TENN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}"
    MEMO_DIAGNOSTICS_PATH="${TENN_ROOT}/financial-engine_v2/data/reports/research_memory/news_memos.jsonl"
    
    # Sync articles to Qdrant, dispatch memo extraction, and refresh the
    # canonical news.sqlite fallback used by Cockpit local news paths. Memo
    # extraction is background enrichment by default; set NEWS_WAIT_FOR_MEMOS=1
    # for explicit bounded wait diagnostics.
    SYNC_ARGS=(
      --since-hours 36
      --refresh-sqlite-fallback
      --memo-diagnostics-path "${MEMO_DIAGNOSTICS_PATH}"
      --memo-max-article-chars "${NEWS_MEMO_MAX_ARTICLE_CHARS:-5000}"
      --summary-json "${SUMMARY_FILE}"
    )
    WAIT_FOR_MEMOS=false
    USE_BOUNDED_MEMO_BACKFILL=false
    JSON_ERROR_FALLBACK_MODEL="${NEWS_JSON_ERROR_FALLBACK_MODEL:-}"
    if [[ "${NEWS_WAIT_FOR_MEMOS:-0}" == "1" ]]; then
      WAIT_FOR_MEMOS=true
      if [[ -n "${JSON_ERROR_FALLBACK_MODEL}" ]]; then
        # Keep wait-mode fallback bounded and observable through the dedicated
        # backfill runner; the loader still performs Qdrant and SQLite sync.
        USE_BOUNDED_MEMO_BACKFILL=true
        SYNC_ARGS+=(--no-dispatch-memos)
      else
        SYNC_ARGS+=(
          --wait-for-memos
          --memo-wait-timeout-seconds "${NEWS_MEMO_WAIT_TIMEOUT_SECONDS:-2700}"
          --memo-wait-poll-interval-seconds "${NEWS_MEMO_WAIT_POLL_INTERVAL_SECONDS:-10}"
        )
      fi
    elif [[ -n "${JSON_ERROR_FALLBACK_MODEL}" ]]; then
      echo "[nightly_news] NEWS_JSON_ERROR_FALLBACK_MODEL ignored because NEWS_WAIT_FOR_MEMOS is not 1" >&2
    fi
    if [[ "${NEWS_FORCE_DISPATCH_MEMOS:-0}" == "1" && "${USE_BOUNDED_MEMO_BACKFILL}" != "true" ]]; then
      SYNC_ARGS+=(--force-dispatch-memos)
    fi
    python3 "${TENN_ROOT}/scripts/load_news_to_qdrant.py" "${SYNC_ARGS[@]}"
    echo "[nightly_news] summary_json=${SUMMARY_FILE}"
    if [[ "${USE_BOUNDED_MEMO_BACKFILL}" == "true" ]]; then
      echo "[nightly_news] phase=memo_backfill started_at=$(date -Iseconds)"
      BACKFILL_ARGS=(
        --since-hours 36
        --limit 0
        --wait-for-memos
        --dispatch-batch-size "${NEWS_MEMO_DISPATCH_BATCH_SIZE:-25}"
        --memo-wait-timeout-seconds "${NEWS_MEMO_WAIT_TIMEOUT_SECONDS:-2700}"
        --memo-wait-poll-interval-seconds "${NEWS_MEMO_WAIT_POLL_INTERVAL_SECONDS:-10}"
        --memo-diagnostics-path "${MEMO_DIAGNOSTICS_PATH}"
        --memo-max-article-chars "${NEWS_MEMO_MAX_ARTICLE_CHARS:-5000}"
        --json-error-fallback-model "${JSON_ERROR_FALLBACK_MODEL}"
        --json-error-fallback-limit "${NEWS_JSON_ERROR_FALLBACK_LIMIT:-3}"
        --summary-json "${MEMO_BACKFILL_SUMMARY_FILE}"
      )
      if [[ "${NEWS_FORCE_DISPATCH_MEMOS:-0}" == "1" ]]; then
        BACKFILL_ARGS+=(--force)
      fi
      python3 "${TENN_ROOT}/scripts/backfill_missing_news_memos.py" "${BACKFILL_ARGS[@]}"
      echo "[nightly_news] memo_backfill_summary_json=${MEMO_BACKFILL_SUMMARY_FILE}"
    fi
  else
    echo "[nightly_news] WARNING: Backend venv not found at ${BACKEND_VENV}, skipping Qdrant sync/extraction" >&2
  fi

  echo "[nightly_news] finished_at=$(date -Iseconds)"
} | tee "${LOG_FILE}"

# Keep the most recent 30 nightly news logs.
ls -1t "${LOG_DIR}"/nightly_news_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f
