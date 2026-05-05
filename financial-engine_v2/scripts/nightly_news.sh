#!/usr/bin/env bash
# Nightly news ingestion — fetches the last 36 hours of ASX news via newspaper4k.
# Scheduled via crontab: 0 2 * * * /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
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
    
    # Sync articles to Qdrant, dispatch memo extraction, and refresh the
    # canonical news.sqlite fallback used by Cockpit local news paths.
    python3 "${TENN_ROOT}/scripts/load_news_to_qdrant.py" \
      --since-hours 36 \
      --refresh-sqlite-fallback \
      --summary-json "${SUMMARY_FILE}"
    echo "[nightly_news] summary_json=${SUMMARY_FILE}"
  else
    echo "[nightly_news] WARNING: Backend venv not found at ${BACKEND_VENV}, skipping Qdrant sync/extraction" >&2
  fi

  echo "[nightly_news] finished_at=$(date -Iseconds)"
} | tee "${LOG_FILE}"

# Keep the most recent 30 nightly news logs.
ls -1t "${LOG_DIR}"/nightly_news_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f
