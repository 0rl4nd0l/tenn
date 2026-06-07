#!/usr/bin/env bash
# Nightly ASX news ingest wrapper.
# Cron target: 0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
set -euo pipefail

TENN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${TENN_ROOT}"

PYTHON_BIN="${NIGHTLY_NEWS_PYTHON:-python3}"
LOG_DIR="${NIGHTLY_NEWS_LOG_DIR:-${TENN_ROOT}/reports/ops_checks/nightly}"
mkdir -p "${LOG_DIR}"

STAMP="$(date +%F_%H%M%S)"
LOG_FILE="${LOG_DIR}/nightly_news_${STAMP}.log"
STATUS_FILE="${LOG_DIR}/nightly_news_${STAMP}.status.json"
FETCH_OUTPUT_FILE="${LOG_DIR}/nightly_news_${STAMP}.fetch.json"
CHUNK_OUTPUT_FILE="${LOG_DIR}/nightly_news_${STAMP}.chunks.json"
HEALTH_FILE="${LOG_DIR}/nightly_news_${STAMP}.health.json"

RUN_STARTED_AT="$(date -Iseconds)"
CURRENT_PHASE="initializing"
INIT_STATUS="running"
FETCH_STATUS="pending"
BUILD_STATUS="pending"
HEALTH_STATUS="pending"
FINISH_STATUS="pending"
WARNING_TEXT=""

DRY_RUN="false"
if [[ "${NIGHTLY_NEWS_DRY_RUN:-0}" == "1" ]]; then
  DRY_RUN="true"
fi

NEWS_PROVIDERS="${NIGHTLY_NEWS_PROVIDERS:-${NEWS_PROVIDERS:-newspaper4k}}"
NEWS_SINCE_HOURS="${NIGHTLY_NEWS_SINCE_HOURS:-${NEWS_SINCE_HOURS:-36}}"
NEWS_LANE="${NIGHTLY_NEWS_LANE:-${NEWS_LANE:-high_precision}}"
NEWS_MAX_TICKERS="${NIGHTLY_NEWS_MAX_TICKERS:-${NEWS_MAX_TICKERS:-0}}"
NEWS_TICKERS="${NIGHTLY_NEWS_TICKERS:-${NEWS_TICKERS:-}}"
NEWS_ASX_WIDE="${NIGHTLY_NEWS_ASX_WIDE:-${NEWS_ASX_WIDE:-0}}"
NEWS_ALLOW_MISSING_EODHD_CAPTURES="${NIGHTLY_NEWS_ALLOW_MISSING_EODHD_CAPTURES:-${NEWS_ALLOW_MISSING_EODHD_CAPTURES:-0}}"
NEWS_MIN_FETCHED="${NIGHTLY_NEWS_MIN_FETCHED:-1}"
NEWS_MIN_CHUNKS="${NIGHTLY_NEWS_MIN_CHUNKS:-1}"
NEWS_MAX_ERRORS="${NIGHTLY_NEWS_MAX_ERRORS:-0}"

NEWS_GDELT_MAX_RECORDS="${NIGHTLY_NEWS_GDELT_MAX_RECORDS:-${NEWS_GDELT_MAX_RECORDS:-250}}"
NEWS_GDELT_TICKER_QUERY_BATCH_SIZE="${NIGHTLY_NEWS_GDELT_TICKER_QUERY_BATCH_SIZE:-${NEWS_GDELT_TICKER_QUERY_BATCH_SIZE:-10}}"
NEWS_GDELT_MAX_TICKER_BATCHES="${NIGHTLY_NEWS_GDELT_MAX_TICKER_BATCHES:-${NEWS_GDELT_MAX_TICKER_BATCHES:-5}}"
NEWS_GDELT_REQUEST_RETRIES="${NIGHTLY_NEWS_GDELT_REQUEST_RETRIES:-${NEWS_GDELT_REQUEST_RETRIES:-3}}"
NEWS_GDELT_RETRY_BACKOFF_SECONDS="${NIGHTLY_NEWS_GDELT_RETRY_BACKOFF_SECONDS:-${NEWS_GDELT_RETRY_BACKOFF_SECONDS:-2.0}}"
NEWS_GDELT_MAX_RETRY_SLEEP_SECONDS="${NIGHTLY_NEWS_GDELT_MAX_RETRY_SLEEP_SECONDS:-${NEWS_GDELT_MAX_RETRY_SLEEP_SECONDS:-120.0}}"
NEWS_NEWSPAPER4K_SOURCE_PROFILE="${NIGHTLY_NEWS_NEWSPAPER4K_SOURCE_PROFILE:-${NEWS_NEWSPAPER4K_SOURCE_PROFILE:-daily}}"
NEWS_NEWSPAPER4K_SOURCES_FILE="${NIGHTLY_NEWS_NEWSPAPER4K_SOURCES_FILE:-${NEWS_NEWSPAPER4K_SOURCES_FILE:-}}"
NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE="${NIGHTLY_NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE:-${NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE:-15}}"
NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES="${NIGHTLY_NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES:-${NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES:-60}}"
NEWS_NEWSPAPER4K_REQUEST_TIMEOUT_SECONDS="${NIGHTLY_NEWS_NEWSPAPER4K_REQUEST_TIMEOUT_SECONDS:-${NEWS_NEWSPAPER4K_REQUEST_TIMEOUT_SECONDS:-10}}"
NEWS_NEWSPAPER4K_SLEEP_SECONDS="${NIGHTLY_NEWS_NEWSPAPER4K_SLEEP_SECONDS:-${NEWS_NEWSPAPER4K_SLEEP_SECONDS:-0.5}}"
NEWS_NEWSPAPER4K_NO_PLAYWRIGHT="${NIGHTLY_NEWS_NEWSPAPER4K_NO_PLAYWRIGHT:-${NEWS_NEWSPAPER4K_NO_PLAYWRIGHT:-1}}"

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
TICKERS_FILE="${NEWS_TICKERS_FILE:-${TENN_ROOT}/financial-engine_v2/data/raw/asx_ticker_universe.txt}"
IDENTITY_MAP_PATH="${NEWS_IDENTITY_MAP_PATH:-${TENN_ROOT}/financial-engine_v2/config/ticker_identity_map.json}"
EODHD_CAPTURE_DIR="${NEWS_EODHD_CAPTURE_DIR:-${TENN_NEWS_EODHD_CAPTURE_DIR:-${TENN_ROOT}/reports/provider_captures/eodhd}}"
WORLDMONITOR_CAPTURE_PATH="${NEWS_WORLDMONITOR_CAPTURE_PATH:-${TENN_NEWS_WORLDMONITOR_CAPTURE_PATH:-${TENN_ROOT}/reports/provider_captures/worldmonitor/api-cache.json}}"
if [[ -n "${NEWS_EODHD_API_KEY:-}" && -z "${EODHD_API_KEY:-}" ]]; then
  export EODHD_API_KEY="${NEWS_EODHD_API_KEY}"
fi

mkdir -p "${NEWS_ARTIFACT_ROOT}" "${NEWS_RUNS_ROOT}"
export PYTHONPATH="${TENN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}"
FETCH_PYTHON_BIN="${PYTHON_BIN}"
if [[ -z "${NIGHTLY_NEWS_PYTHON:-}" && ",${NEWS_PROVIDERS}," == *",newspaper4k,"* && -x "${TENN_ROOT}/integrations/newspaper4k_au/.venv/bin/python" ]]; then
  FETCH_PYTHON_BIN="${TENN_ROOT}/integrations/newspaper4k_au/.venv/bin/python"
fi

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
  export NIGHTLY_NEWS_BUILD_STATUS="${BUILD_STATUS}"
  export NIGHTLY_NEWS_HEALTH_STATUS="${HEALTH_STATUS}"
  export NIGHTLY_NEWS_FINISH_STATUS="${FINISH_STATUS}"
  export NIGHTLY_NEWS_WARNING_TEXT="${WARNING_TEXT}"
  export NIGHTLY_NEWS_DRY_RUN_EFFECTIVE="${DRY_RUN}"
  export NIGHTLY_NEWS_PROVIDERS_EFFECTIVE="${NEWS_PROVIDERS}"
  export NIGHTLY_NEWS_LANE_EFFECTIVE="${NEWS_LANE}"
  export NIGHTLY_NEWS_SINCE_HOURS_EFFECTIVE="${NEWS_SINCE_HOURS}"
  export NIGHTLY_NEWS_MAX_TICKERS_EFFECTIVE="${NEWS_MAX_TICKERS}"
  export NIGHTLY_NEWS_MIN_FETCHED_EFFECTIVE="${NEWS_MIN_FETCHED}"
  export NIGHTLY_NEWS_MIN_CHUNKS_EFFECTIVE="${NEWS_MIN_CHUNKS}"
  export NIGHTLY_NEWS_MAX_ERRORS_EFFECTIVE="${NEWS_MAX_ERRORS}"
  export NIGHTLY_NEWS_LOG_FILE="${LOG_FILE}"
  export NIGHTLY_NEWS_STATUS_FILE="${STATUS_FILE}"
  export NIGHTLY_NEWS_FETCH_OUTPUT_FILE="${FETCH_OUTPUT_FILE}"
  export NIGHTLY_NEWS_CHUNK_OUTPUT_FILE="${CHUNK_OUTPUT_FILE}"
  export NIGHTLY_NEWS_HEALTH_FILE="${HEALTH_FILE}"
  export NIGHTLY_NEWS_TICKERS_FILE="${TICKERS_FILE}"
  export NIGHTLY_NEWS_IDENTITY_MAP_PATH="${IDENTITY_MAP_PATH}"
  export NIGHTLY_NEWS_ARTIFACT_ROOT="${NEWS_ARTIFACT_ROOT}"
  export NIGHTLY_NEWS_ARTICLES_DB="${NEWS_ARTICLES_DB}"
  export NIGHTLY_NEWS_CONTEXT_DB="${NEWS_CONTEXT_DB}"
  export NIGHTLY_NEWS_RUNS_ROOT="${NEWS_RUNS_ROOT}"
  export NIGHTLY_NEWS_TENN_ROOT="${TENN_ROOT}"

  "${PYTHON_BIN}" - "${STATUS_FILE}" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def env(name: str) -> str:
    return os.environ.get(name, "")


def env_bool(name: str) -> bool:
    return env(name).strip().lower() == "true"


def env_int(name: str) -> int:
    try:
        return int(float(env(name)))
    except Exception:
        return 0


status_path = Path(sys.argv[1])
fetch_output = env("NIGHTLY_NEWS_FETCH_OUTPUT_FILE")
chunk_output = env("NIGHTLY_NEWS_CHUNK_OUTPUT_FILE")
health_file = env("NIGHTLY_NEWS_HEALTH_FILE")
payload = {
    "status": env("NIGHTLY_NEWS_STATUS"),
    "exit_code": env_int("NIGHTLY_NEWS_EXIT_CODE"),
    "started_at": env("NIGHTLY_NEWS_RUN_STARTED_AT"),
    "finished_at": env("NIGHTLY_NEWS_FINISHED_AT"),
    "current_phase": env("NIGHTLY_NEWS_CURRENT_PHASE"),
    "failed_phase": env("NIGHTLY_NEWS_FAILED_PHASE"),
    "dry_run": env_bool("NIGHTLY_NEWS_DRY_RUN_EFFECTIVE"),
    "config": {
        "providers": env("NIGHTLY_NEWS_PROVIDERS_EFFECTIVE"),
        "lane": env("NIGHTLY_NEWS_LANE_EFFECTIVE"),
        "since_hours": env_int("NIGHTLY_NEWS_SINCE_HOURS_EFFECTIVE"),
        "max_tickers": env_int("NIGHTLY_NEWS_MAX_TICKERS_EFFECTIVE"),
        "min_fetched": env_int("NIGHTLY_NEWS_MIN_FETCHED_EFFECTIVE"),
        "min_chunks": env_int("NIGHTLY_NEWS_MIN_CHUNKS_EFFECTIVE"),
        "max_errors": env_int("NIGHTLY_NEWS_MAX_ERRORS_EFFECTIVE"),
    },
    "paths": {
        "tenn_root": env("NIGHTLY_NEWS_TENN_ROOT"),
        "ticker_universe": env("NIGHTLY_NEWS_TICKERS_FILE"),
        "identity_map": env("NIGHTLY_NEWS_IDENTITY_MAP_PATH"),
        "news_artifact_root": env("NIGHTLY_NEWS_ARTIFACT_ROOT"),
        "news_articles_db": env("NIGHTLY_NEWS_ARTICLES_DB"),
        "news_context_db": env("NIGHTLY_NEWS_CONTEXT_DB"),
        "news_runs_root": env("NIGHTLY_NEWS_RUNS_ROOT"),
        "log": env("NIGHTLY_NEWS_LOG_FILE"),
        "status_json": env("NIGHTLY_NEWS_STATUS_FILE"),
        "fetch_json": fetch_output,
        "chunks_json": chunk_output,
        "health_json": health_file,
    },
    "artifacts": {
        "fetch_json_exists": bool(fetch_output and Path(fetch_output).exists()),
        "chunks_json_exists": bool(chunk_output and Path(chunk_output).exists()),
        "health_json_exists": bool(health_file and Path(health_file).exists()),
    },
    "phases": {
        "initializing": env("NIGHTLY_NEWS_INIT_STATUS"),
        "fetch": env("NIGHTLY_NEWS_FETCH_STATUS"),
        "build": env("NIGHTLY_NEWS_BUILD_STATUS"),
        "health": env("NIGHTLY_NEWS_HEALTH_STATUS"),
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
    initializing) INIT_STATUS="failure" ;;
    fetch) FETCH_STATUS="failure" ;;
    build) BUILD_STATUS="failure" ;;
    health) HEALTH_STATUS="failure" ;;
    *) ;;
  esac
}

prune_old_artifacts() {
  for pattern in \
    "nightly_news_*.log" \
    "nightly_news_*.status.json" \
    "nightly_news_*.fetch.json" \
    "nightly_news_*.chunks.json" \
    "nightly_news_*.health.json"; do
    ls -1t "${LOG_DIR}"/${pattern} 2>/dev/null | tail -n +31 | xargs -r rm -f
  done
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
  prune_old_artifacts || true
  echo "[nightly_news] status_json=${STATUS_FILE}"
  exit "${exit_code}"
}

count_tickers() {
  "${PYTHON_BIN}" - "${TICKERS_FILE}" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
seen = set()
for line in path.read_text(encoding="utf-8").splitlines():
    raw = line.split("#", 1)[0].strip()
    if not raw:
        continue
    sym = re.sub(r"[^A-Za-z0-9]", "", raw.upper())
    if sym:
        seen.add(sym)
print(len(seen))
PY
}

write_dry_run_health() {
  local ticker_count="$1"
  "${PYTHON_BIN}" - "${HEALTH_FILE}" "${ticker_count}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = {
    "status": "success",
    "dry_run": True,
    "ticker_count": int(sys.argv[2]),
    "totals": {"fetched": 0, "inserted": 0, "deduped": 0, "rejected": 0, "errors": 0, "chunks_written": 0},
    "problems": [],
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

write_health_json() {
  "${PYTHON_BIN}" - \
    "${FETCH_OUTPUT_FILE}" \
    "${CHUNK_OUTPUT_FILE}" \
    "${NEWS_ARTICLES_DB}" \
    "${HEALTH_FILE}" \
    "${NEWS_MIN_FETCHED}" \
    "${NEWS_MIN_CHUNKS}" \
    "${NEWS_MAX_ERRORS}" <<'PY'
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except Exception as exc:
        decoder = json.JSONDecoder()
        payload = None
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if text[index + end :].strip():
                continue
            payload = candidate
            break
        if payload is None:
            raise RuntimeError(f"failed to parse JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object JSON in {path}")
    return payload


fetch_path = Path(sys.argv[1])
chunk_path = Path(sys.argv[2])
articles_db = Path(sys.argv[3])
health_path = Path(sys.argv[4])
min_fetched = int(float(sys.argv[5]))
min_chunks = int(float(sys.argv[6]))
max_errors = int(float(sys.argv[7]))

fetch_payload = read_json(fetch_path)
chunk_payload = read_json(chunk_path)
run_ids = [
    str(run.get("run_id") or "").strip()
    for run in fetch_payload.get("runs", [])
    if isinstance(run, dict) and str(run.get("run_id") or "").strip()
]

runs = []
totals = {"fetched": 0, "inserted": 0, "deduped": 0, "rejected": 0, "errors": 0}
conn = sqlite3.connect(str(articles_db))
conn.row_factory = sqlite3.Row
try:
    for run_id in run_ids:
        row = conn.execute("SELECT * FROM provider_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            runs.append({"run_id": run_id, "missing": True})
            continue
        item = dict(row)
        normalized = {
            "run_id": str(item.get("run_id") or ""),
            "provider": str(item.get("provider") or ""),
            "status": str(item.get("status") or ""),
            "fetched": int(item.get("fetched") or 0),
            "inserted": int(item.get("inserted") or 0),
            "deduped": int(item.get("deduped") or 0),
            "rejected": int(item.get("rejected") or 0),
            "errors": int(item.get("errors") or 0),
        }
        for key in totals:
            totals[key] += int(normalized[key])
        runs.append(normalized)
finally:
    conn.close()

chunk_stats = chunk_payload.get("stats") if isinstance(chunk_payload.get("stats"), dict) else {}
chunks_written = int(chunk_stats.get("chunks_written") or 0)
totals["chunks_written"] = chunks_written

problems = []
if not run_ids:
    problems.append("fetch output did not contain provider run IDs")
if totals["fetched"] < min_fetched:
    problems.append(f"fetched {totals['fetched']} below minimum {min_fetched}")
if chunks_written < min_chunks:
    problems.append(f"chunks_written {chunks_written} below minimum {min_chunks}")
if totals["errors"] > max_errors:
    problems.append(f"errors {totals['errors']} above maximum {max_errors}")
for item in runs:
    status = str(item.get("status") or "")
    if status and status not in {"success"}:
        problems.append(f"provider run {item.get('run_id')} status={status}")

payload = {
    "status": "failure" if problems else "success",
    "dry_run": False,
    "fetch_json": str(fetch_path),
    "chunks_json": str(chunk_path),
    "news_articles_db": str(articles_db),
    "runs": runs,
    "totals": totals,
    "chunk_stats": chunk_stats,
    "thresholds": {
        "min_fetched": min_fetched,
        "min_chunks": min_chunks,
        "max_errors": max_errors,
    },
    "problems": problems,
}
health_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
raise SystemExit(1 if problems else 0)
PY
}

trap on_exit EXIT
exec > >(tee "${LOG_FILE}") 2>&1

echo "[nightly_news] started_at=${RUN_STARTED_AT}"
echo "[nightly_news] tenn_root=${TENN_ROOT}"
echo "[nightly_news] log_file=${LOG_FILE}"
echo "[nightly_news] status_json=${STATUS_FILE}"
echo "[nightly_news] providers=${NEWS_PROVIDERS}"
echo "[nightly_news] fetch_python=${FETCH_PYTHON_BIN}"
echo "[nightly_news] lane=${NEWS_LANE}"
echo "[nightly_news] since_hours=${NEWS_SINCE_HOURS}"
echo "[nightly_news] dry_run=${DRY_RUN}"
echo "[nightly_news] ticker_universe=${TICKERS_FILE}"
echo "[nightly_news] identity_map=${IDENTITY_MAP_PATH}"
echo "[nightly_news] news_articles_db=${NEWS_ARTICLES_DB}"
echo "[nightly_news] news_context_db=${NEWS_CONTEXT_DB}"
echo "[nightly_news] news_runs_root=${NEWS_RUNS_ROOT}"

CURRENT_PHASE="initializing"
if [[ ! -f "${TENN_ROOT}/scripts/fetch_daily_news.py" ]]; then
  echo "[nightly_news] ERROR: missing ${TENN_ROOT}/scripts/fetch_daily_news.py" >&2
  exit 1
fi
if [[ ! -f "${TENN_ROOT}/scripts/build_news_chunks.py" ]]; then
  echo "[nightly_news] ERROR: missing ${TENN_ROOT}/scripts/build_news_chunks.py" >&2
  exit 1
fi
if [[ ! -s "${TICKERS_FILE}" ]]; then
  echo "[nightly_news] ERROR: missing or empty ticker universe: ${TICKERS_FILE}" >&2
  exit 1
fi
if [[ ! -f "${IDENTITY_MAP_PATH}" ]]; then
  echo "[nightly_news] ERROR: missing ticker identity map: ${IDENTITY_MAP_PATH}" >&2
  exit 1
fi

TICKER_COUNT="$(count_tickers)"
if [[ "${TICKER_COUNT}" -le 0 ]]; then
  echo "[nightly_news] ERROR: no tickers resolved from ${TICKERS_FILE}" >&2
  exit 1
fi
echo "[nightly_news] ticker_count=${TICKER_COUNT}"
INIT_STATUS="success"

if [[ "${DRY_RUN}" == "true" ]]; then
  FETCH_STATUS="skipped_dry_run"
  BUILD_STATUS="skipped_dry_run"
  CURRENT_PHASE="health"
  write_dry_run_health "${TICKER_COUNT}"
  HEALTH_STATUS="success"
  exit 0
fi

CURRENT_PHASE="fetch"
FETCH_ARGS=(
  --providers "${NEWS_PROVIDERS}"
  --since-hours "${NEWS_SINCE_HOURS}"
  --lane "${NEWS_LANE}"
  --max-tickers "${NEWS_MAX_TICKERS}"
  --tickers-file "${TICKERS_FILE}"
  --identity-map-path "${IDENTITY_MAP_PATH}"
  --news-articles-db "${NEWS_ARTICLES_DB}"
  --news-runs-root "${NEWS_RUNS_ROOT}"
  --eodhd-capture-dir "${EODHD_CAPTURE_DIR}"
  --worldmonitor-capture-path "${WORLDMONITOR_CAPTURE_PATH}"
  --gdelt-max-records "${NEWS_GDELT_MAX_RECORDS}"
  --gdelt-ticker-query-batch-size "${NEWS_GDELT_TICKER_QUERY_BATCH_SIZE}"
  --gdelt-max-ticker-batches "${NEWS_GDELT_MAX_TICKER_BATCHES}"
  --gdelt-request-retries "${NEWS_GDELT_REQUEST_RETRIES}"
  --gdelt-retry-backoff-seconds "${NEWS_GDELT_RETRY_BACKOFF_SECONDS}"
  --gdelt-max-retry-sleep-seconds "${NEWS_GDELT_MAX_RETRY_SLEEP_SECONDS}"
  --newspaper4k-source-profile "${NEWS_NEWSPAPER4K_SOURCE_PROFILE}"
  --newspaper4k-max-articles-per-source "${NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE}"
  --newspaper4k-max-total-articles "${NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES}"
  --newspaper4k-request-timeout-seconds "${NEWS_NEWSPAPER4K_REQUEST_TIMEOUT_SECONDS}"
  --newspaper4k-sleep-seconds "${NEWS_NEWSPAPER4K_SLEEP_SECONDS}"
)
if [[ -n "${NEWS_NEWSPAPER4K_SOURCES_FILE}" ]]; then
  FETCH_ARGS+=(--newspaper4k-sources-file "${NEWS_NEWSPAPER4K_SOURCES_FILE}")
fi
if [[ "${NEWS_NEWSPAPER4K_NO_PLAYWRIGHT}" == "1" ]]; then
  FETCH_ARGS+=(--newspaper4k-no-playwright)
fi
if [[ -n "${NEWS_TICKERS}" ]]; then
  FETCH_ARGS+=(--tickers "${NEWS_TICKERS}")
fi
if [[ "${NEWS_ASX_WIDE}" == "1" ]]; then
  FETCH_ARGS+=(--asx-wide)
fi
if [[ "${NEWS_ALLOW_MISSING_EODHD_CAPTURES}" == "1" ]]; then
  FETCH_ARGS+=(--allow-missing-eodhd-captures)
fi

echo "[nightly_news] phase=fetch started_at=$(date -Iseconds)"
"${FETCH_PYTHON_BIN}" "${TENN_ROOT}/scripts/fetch_daily_news.py" "${FETCH_ARGS[@]}" | tee "${FETCH_OUTPUT_FILE}"
FETCH_STATUS="success"

CURRENT_PHASE="build"
BUILD_ARGS=(
  --from-db "${NEWS_ARTICLES_DB}"
  --to-db "${NEWS_CONTEXT_DB}"
  --lane "${NEWS_LANE}"
  --embed-backend "${NIGHTLY_NEWS_EMBED_BACKEND:-${NEWS_EMBED_BACKEND:-hash}}"
)
echo "[nightly_news] phase=build started_at=$(date -Iseconds)"
"${PYTHON_BIN}" "${TENN_ROOT}/scripts/build_news_chunks.py" "${BUILD_ARGS[@]}" | tee "${CHUNK_OUTPUT_FILE}"
BUILD_STATUS="success"

CURRENT_PHASE="health"
echo "[nightly_news] phase=health started_at=$(date -Iseconds)"
write_health_json
HEALTH_STATUS="success"
