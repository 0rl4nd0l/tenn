#!/usr/bin/env bash
# Nightly news ingestion — fetches the last 36 hours of ASX news via newspaper4k.
# Scheduled via crontab: 0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
set -euo pipefail

TENN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

LOG_DIR="${NIGHTLY_NEWS_LOG_DIR:-${TENN_ROOT}/reports/ops_checks/nightly}"
mkdir -p "${LOG_DIR}"
STAMP="$(date +%F_%H%M%S)"
LOG_FILE="${LOG_DIR}/nightly_news_${STAMP}.log"
STATUS_FILE="${LOG_DIR}/nightly_news_${STAMP}.status.json"
SUMMARY_FILE="${LOG_DIR}/nightly_news_${STAMP}.summary.json"
MEMO_BACKFILL_SUMMARY_FILE="${LOG_DIR}/nightly_news_${STAMP}.memo_backfill.summary.json"

RUN_STARTED_AT="$(date -Iseconds)"
CURRENT_PHASE="initializing"
INIT_STATUS="running"
FETCH_STATUS="pending"
SYNC_STATUS="pending"
MEMO_STATUS="pending"
MEMO_BACKFILL_STATUS="not_requested"
FINISH_STATUS="pending"
WARNING_TEXT=""
DRY_RUN="false"
if [[ "${NIGHTLY_NEWS_DRY_RUN:-0}" == "1" ]]; then
  DRY_RUN="true"
fi
TICKERS_FILE="${NEWS_TICKERS_FILE:-${TENN_ROOT}/financial-engine_v2/data/raw/asx_ticker_universe.txt}"
if [[ -n "${TENN_NEWS_ARTIFACT_ROOT:-}" ]]; then
  NEWS_ARTIFACT_ROOT="${TENN_NEWS_ARTIFACT_ROOT}"
elif [[ -d "/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context" ]]; then
  NEWS_ARTIFACT_ROOT="/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context"
else
  NEWS_ARTIFACT_ROOT="${TENN_ROOT}/reports/qual_context"
fi
NEWS_ARTICLES_DB="${TENN_NEWS_ARTICLES_DB:-${NEWS_ARTIFACT_ROOT}/news_articles.sqlite}"
NEWS_CONTEXT_DB="${TENN_NEWS_CONTEXT_DB:-${NEWS_ARTIFACT_ROOT}/news.sqlite}"
NEWS_RUNS_ROOT="${TENN_NEWS_RUNS_ROOT:-${NEWS_ARTIFACT_ROOT}/news_runs}"
export TENN_NEWS_ARTIFACT_ROOT="${NEWS_ARTIFACT_ROOT}"
mkdir -p "${NEWS_ARTIFACT_ROOT}" "${NEWS_RUNS_ROOT}"

write_status_json() {
  local exit_code="$1"
  local finished_at="$2"
  local run_status="$3"
  local failed_phase="$4"

  export NIGHTLY_NEWS_RUN_STARTED_AT="${RUN_STARTED_AT}"
  export NIGHTLY_NEWS_FINISHED_AT="${finished_at}"
  export NIGHTLY_NEWS_STATUS="${run_status}"
  export NIGHTLY_NEWS_EXIT_CODE="${exit_code}"
  export NIGHTLY_NEWS_CURRENT_PHASE="${CURRENT_PHASE}"
  export NIGHTLY_NEWS_FAILED_PHASE="${failed_phase}"
  export NIGHTLY_NEWS_INIT_STATUS="${INIT_STATUS}"
  export NIGHTLY_NEWS_FETCH_STATUS="${FETCH_STATUS}"
  export NIGHTLY_NEWS_SYNC_STATUS="${SYNC_STATUS}"
  export NIGHTLY_NEWS_MEMO_STATUS="${MEMO_STATUS}"
  export NIGHTLY_NEWS_MEMO_BACKFILL_STATUS="${MEMO_BACKFILL_STATUS}"
  export NIGHTLY_NEWS_FINISH_STATUS="${FINISH_STATUS}"
  export NIGHTLY_NEWS_WARNING_TEXT="${WARNING_TEXT}"
  export NIGHTLY_NEWS_DRY_RUN_EFFECTIVE="${DRY_RUN}"
  export NIGHTLY_NEWS_LOG_FILE="${LOG_FILE}"
  export NIGHTLY_NEWS_STATUS_FILE="${STATUS_FILE}"
  export NIGHTLY_NEWS_SUMMARY_FILE="${SUMMARY_FILE}"
  export NIGHTLY_NEWS_MEMO_BACKFILL_SUMMARY_FILE="${MEMO_BACKFILL_SUMMARY_FILE}"
  export NIGHTLY_NEWS_TICKERS_FILE="${TICKERS_FILE}"
  export NIGHTLY_NEWS_ARTIFACT_ROOT="${NEWS_ARTIFACT_ROOT}"
  export NIGHTLY_NEWS_ARTICLES_DB="${NEWS_ARTICLES_DB}"
  export NIGHTLY_NEWS_CONTEXT_DB="${NEWS_CONTEXT_DB}"
  export NIGHTLY_NEWS_RUNS_ROOT="${NEWS_RUNS_ROOT}"
  export NIGHTLY_NEWS_TENN_ROOT="${TENN_ROOT}"
  export NIGHTLY_NEWS_VENV="${VENV:-}"
  export NIGHTLY_NEWS_BACKEND_VENV="${BACKEND_VENV:-}"

  python3 - "${STATUS_FILE}" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

status_path = Path(sys.argv[1])


def env(name: str) -> str:
    return os.environ.get(name, "")


def env_bool(name: str) -> bool:
    return env(name).strip().lower() == "true"


def env_int(name: str) -> int:
    try:
        return int(env(name))
    except ValueError:
        return 0


summary_file = env("NIGHTLY_NEWS_SUMMARY_FILE")
memo_summary_file = env("NIGHTLY_NEWS_MEMO_BACKFILL_SUMMARY_FILE")
payload = {
    "status": env("NIGHTLY_NEWS_STATUS"),
    "exit_code": env_int("NIGHTLY_NEWS_EXIT_CODE"),
    "started_at": env("NIGHTLY_NEWS_RUN_STARTED_AT"),
    "finished_at": env("NIGHTLY_NEWS_FINISHED_AT"),
    "current_phase": env("NIGHTLY_NEWS_CURRENT_PHASE"),
    "failed_phase": env("NIGHTLY_NEWS_FAILED_PHASE"),
    "dry_run": env_bool("NIGHTLY_NEWS_DRY_RUN_EFFECTIVE"),
    "paths": {
        "tenn_root": env("NIGHTLY_NEWS_TENN_ROOT"),
        "ticker_universe": env("NIGHTLY_NEWS_TICKERS_FILE"),
        "news_artifact_root": env("NIGHTLY_NEWS_ARTIFACT_ROOT"),
        "news_articles_db": env("NIGHTLY_NEWS_ARTICLES_DB"),
        "news_context_db": env("NIGHTLY_NEWS_CONTEXT_DB"),
        "news_runs_root": env("NIGHTLY_NEWS_RUNS_ROOT"),
        "log": env("NIGHTLY_NEWS_LOG_FILE"),
        "status_json": env("NIGHTLY_NEWS_STATUS_FILE"),
        "sync_summary_json": summary_file,
        "memo_backfill_summary_json": memo_summary_file,
    },
    "artifacts": {
        "sync_summary_json_exists": bool(summary_file and Path(summary_file).exists()),
        "memo_backfill_summary_json_exists": bool(memo_summary_file and Path(memo_summary_file).exists()),
    },
    "venvs": {
        "newspaper4k": env("NIGHTLY_NEWS_VENV"),
        "backend": env("NIGHTLY_NEWS_BACKEND_VENV"),
    },
    "phases": {
        "initializing": env("NIGHTLY_NEWS_INIT_STATUS"),
        "fetch": env("NIGHTLY_NEWS_FETCH_STATUS"),
        "sync": env("NIGHTLY_NEWS_SYNC_STATUS"),
        "memo": env("NIGHTLY_NEWS_MEMO_STATUS"),
        "memo_backfill": env("NIGHTLY_NEWS_MEMO_BACKFILL_STATUS"),
        "finish": env("NIGHTLY_NEWS_FINISH_STATUS"),
    },
    "warning": env("NIGHTLY_NEWS_WARNING_TEXT"),
}
status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

mark_failed_phase() {
  local phase="$1"
  case "${phase}" in
    initializing)
      INIT_STATUS="failure"
      ;;
    fetch)
      FETCH_STATUS="failure"
      ;;
    sync)
      SYNC_STATUS="failure"
      ;;
    memo_backfill)
      MEMO_BACKFILL_STATUS="failure"
      ;;
    *)
      ;;
  esac
}

on_exit() {
  local exit_code=$?
  set +e
  trap - EXIT
  local finished_at
  finished_at="$(date -Iseconds)"
  local run_status="success"
  local failed_phase=""
  if [[ "${exit_code}" -eq 0 ]]; then
    INIT_STATUS="success"
    FINISH_STATUS="success"
    echo "[nightly_news] finished_at=${finished_at}"
  else
    run_status="failure"
    failed_phase="${CURRENT_PHASE}"
    FINISH_STATUS="skipped"
    mark_failed_phase "${failed_phase}"
    echo "[nightly_news] failed_at=${finished_at} phase=${failed_phase} exit_code=${exit_code}" >&2
  fi
  write_status_json "${exit_code}" "${finished_at}" "${run_status}" "${failed_phase}" || true
  echo "[nightly_news] status_json=${STATUS_FILE}"
  exit "${exit_code}"
}

trap on_exit EXIT
exec > >(tee "${LOG_FILE}") 2>&1

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

INIT_STATUS="success"

echo "[nightly_news] started_at=${RUN_STARTED_AT}"
echo "[nightly_news] log_file=${LOG_FILE}"
echo "[nightly_news] status_json=${STATUS_FILE}"
echo "[nightly_news] ticker_universe=${TICKERS_FILE}"
echo "[nightly_news] news_artifact_root=${NEWS_ARTIFACT_ROOT}"
echo "[nightly_news] news_articles_db=${NEWS_ARTICLES_DB}"
echo "[nightly_news] news_context_db=${NEWS_CONTEXT_DB}"
echo "[nightly_news] news_runs_root=${NEWS_RUNS_ROOT}"
echo "[nightly_news] phase=fetch python=$(command -v python3) venv=${VENV} dry_run=${DRY_RUN}"

CURRENT_PHASE="fetch"
FETCH_ARGS=(
    --providers newspaper4k
    --since-hours 36
    --lane high_precision
    --tickers-file "${TICKERS_FILE}"
    --news-articles-db "${NEWS_ARTICLES_DB}"
    --news-runs-root "${NEWS_RUNS_ROOT}"
    --newspaper4k-source-profile daily
    --newspaper4k-max-articles-per-source 15
    --newspaper4k-max-total-articles 60
    --newspaper4k-request-timeout-seconds 10
    --newspaper4k-no-playwright
)
if [[ "${DRY_RUN}" == "true" ]]; then
  FETCH_ARGS+=(--dry-run)
fi
python3 "${TENN_ROOT}/scripts/fetch_daily_news.py" "${FETCH_ARGS[@]}"
FETCH_STATUS="success"

if [[ "${DRY_RUN}" == "true" ]]; then
  SYNC_STATUS="skipped_dry_run"
  MEMO_STATUS="skipped_dry_run"
  echo "[nightly_news] phase=sync skipped reason=dry_run"
else
  # --- Phase 2: Sync to Qdrant & Trigger Extraction ---
  CURRENT_PHASE="sync"
  echo "[nightly_news] phase=sync started_at=$(date -Iseconds)"

  # We need the backend venv for this step
  BACKEND_VENV="${TENN_ROOT}/financial-engine_v2/.venv"
  if [[ -f "${BACKEND_VENV}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${BACKEND_VENV}/bin/activate"
    echo "[nightly_news] phase=sync python=$(command -v python3) venv=${BACKEND_VENV}"

    # Add backend to PYTHONPATH for app.* imports
    export PYTHONPATH="${TENN_ROOT}/financial-engine_v2/backend:${TENN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}"
    MEMO_DIAGNOSTICS_PATH="${TENN_ROOT}/financial-engine_v2/data/reports/research_memory/news_memos.jsonl"

    # Sync articles to Qdrant, dispatch memo extraction, and refresh the
    # canonical news.sqlite fallback used by Cockpit local news paths. Memo
    # extraction is background enrichment by default; set NEWS_WAIT_FOR_MEMOS=1
    # for explicit bounded wait diagnostics.
    SYNC_ARGS=(
      --since-hours 36
      --db-path "${NEWS_ARTICLES_DB}"
      --news-context-db "${NEWS_CONTEXT_DB}"
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
        MEMO_STATUS="deferred_to_backfill"
      else
        SYNC_ARGS+=(
          --wait-for-memos
          --memo-wait-timeout-seconds "${NEWS_MEMO_WAIT_TIMEOUT_SECONDS:-2700}"
          --memo-wait-poll-interval-seconds "${NEWS_MEMO_WAIT_POLL_INTERVAL_SECONDS:-10}"
        )
        MEMO_STATUS="wait_requested"
      fi
    elif [[ -n "${JSON_ERROR_FALLBACK_MODEL}" ]]; then
      echo "[nightly_news] NEWS_JSON_ERROR_FALLBACK_MODEL ignored because NEWS_WAIT_FOR_MEMOS is not 1" >&2
    fi
    if [[ "${NEWS_FORCE_DISPATCH_MEMOS:-0}" == "1" && "${USE_BOUNDED_MEMO_BACKFILL}" != "true" ]]; then
      SYNC_ARGS+=(--force-dispatch-memos)
      MEMO_STATUS="force_dispatch_requested"
    elif [[ "${MEMO_STATUS}" == "pending" ]]; then
      MEMO_STATUS="dispatch_requested"
    fi
    python3 "${TENN_ROOT}/scripts/load_news_to_qdrant.py" "${SYNC_ARGS[@]}"
    SYNC_STATUS="success"
    if [[ "${MEMO_STATUS}" == "dispatch_requested" || "${MEMO_STATUS}" == "force_dispatch_requested" ]]; then
      MEMO_STATUS="dispatched"
    elif [[ "${MEMO_STATUS}" == "wait_requested" ]]; then
      MEMO_STATUS="wait_completed"
    fi
    echo "[nightly_news] summary_json=${SUMMARY_FILE}"
    if [[ "${USE_BOUNDED_MEMO_BACKFILL}" == "true" ]]; then
      CURRENT_PHASE="memo_backfill"
      MEMO_BACKFILL_STATUS="running"
      echo "[nightly_news] phase=memo_backfill started_at=$(date -Iseconds)"
      BACKFILL_ARGS=(
        --since-hours 36
        --db-path "${NEWS_ARTICLES_DB}"
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
      MEMO_BACKFILL_STATUS="success"
      MEMO_STATUS="backfill_completed"
      echo "[nightly_news] memo_backfill_summary_json=${MEMO_BACKFILL_SUMMARY_FILE}"
    fi
  else
    WARNING_TEXT="Backend venv not found at ${BACKEND_VENV}; skipped Qdrant sync and memo work"
    SYNC_STATUS="skipped_backend_venv_missing"
    MEMO_STATUS="skipped_backend_venv_missing"
    echo "[nightly_news] WARNING: ${WARNING_TEXT}" >&2
  fi
fi

CURRENT_PHASE="retention"
# Keep the most recent 30 nightly news logs and status artifacts.
ls -1t "${LOG_DIR}"/nightly_news_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f || true
ls -1t "${LOG_DIR}"/nightly_news_*.status.json 2>/dev/null | tail -n +31 | xargs -r rm -f || true
CURRENT_PHASE="finish"
