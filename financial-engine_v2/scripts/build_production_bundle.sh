#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASES_DIR="${ROOT_DIR}/releases"
TS="$(date +%Y%m%d_%H%M%S)"
PACKAGE_NAME="financial_engine_v2_production_${TS}"
STAGE_DIR="${RELEASES_DIR}/${PACKAGE_NAME}"
APP_DIR="${STAGE_DIR}/financial-engine_v2"
ZIP_PATH="${RELEASES_DIR}/${PACKAGE_NAME}.zip"

mkdir -p "${RELEASES_DIR}"
rm -rf "${STAGE_DIR}"
mkdir -p "${APP_DIR}"

copy_file() {
  local src="$1"
  local dst="$2"
  mkdir -p "$(dirname "${dst}")"
  cp "${src}" "${dst}"
}

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  rsync -a \
    --exclude "__pycache__" \
    --exclude ".venv" \
    --exclude ".pytest_cache" \
    --exclude ".ruff_cache" \
    --exclude "*.pyc" \
    "${src}" "${dst}/"
}

copy_file "${ROOT_DIR}/README.md" "${APP_DIR}/README.md"
copy_file "${ROOT_DIR}/.env.example" "${APP_DIR}/.env.example"
copy_file "${ROOT_DIR}/Makefile" "${APP_DIR}/Makefile"
copy_file "${ROOT_DIR}/docker-compose.yml" "${APP_DIR}/docker-compose.yml"

copy_tree "${ROOT_DIR}/backend" "${APP_DIR}"
copy_tree "${ROOT_DIR}/worker" "${APP_DIR}"

mkdir -p "${APP_DIR}/scripts"
copy_file "${ROOT_DIR}/scripts/run_local_backend.sh" "${APP_DIR}/scripts/run_local_backend.sh"
copy_file "${ROOT_DIR}/scripts/smoke_local.sh" "${APP_DIR}/scripts/smoke_local.sh"
copy_file "${ROOT_DIR}/scripts/full_history_ticker_sync.py" "${APP_DIR}/scripts/full_history_ticker_sync.py"
copy_file "${ROOT_DIR}/scripts/resume_pending_downloads.py" "${APP_DIR}/scripts/resume_pending_downloads.py"
copy_file "${ROOT_DIR}/scripts/recover_marketindex_headed.py" "${APP_DIR}/scripts/recover_marketindex_headed.py"
copy_file "${ROOT_DIR}/scripts/rename_document_files.py" "${APP_DIR}/scripts/rename_document_files.py"
copy_file "${ROOT_DIR}/scripts/marketindex_ingest.py" "${APP_DIR}/scripts/marketindex_ingest.py"
copy_file "${ROOT_DIR}/scripts/marketindex_download_pdfs.py" "${APP_DIR}/scripts/marketindex_download_pdfs.py"
copy_file "${ROOT_DIR}/scripts/daily_marketindex_action.py" "${APP_DIR}/scripts/daily_marketindex_action.py"
copy_file "${ROOT_DIR}/scripts/daily_asx_all_announcements_action.py" "${APP_DIR}/scripts/daily_asx_all_announcements_action.py"
copy_file "${ROOT_DIR}/scripts/asx_enrichment_sweep_action.py" "${APP_DIR}/scripts/asx_enrichment_sweep_action.py"
copy_file "${ROOT_DIR}/scripts/test_marketindex_headed_recovery_logic.py" "${APP_DIR}/scripts/test_marketindex_headed_recovery_logic.py"
copy_file "${ROOT_DIR}/scripts/build_production_bundle.sh" "${APP_DIR}/scripts/build_production_bundle.sh"

chmod +x "${APP_DIR}/scripts/run_local_backend.sh"
chmod +x "${APP_DIR}/scripts/smoke_local.sh"
chmod +x "${APP_DIR}/scripts/recover_marketindex_headed.py"
chmod +x "${APP_DIR}/scripts/build_production_bundle.sh"

mkdir -p "${APP_DIR}/data/raw"
mkdir -p "${APP_DIR}/data/asx/docs"
mkdir -p "${APP_DIR}/data/marketindex/pdfs"
mkdir -p "${APP_DIR}/reports/marketindex"

cat > "${APP_DIR}/PACKAGE_MANIFEST.md" <<'EOF'
# Production Bundle Manifest

Included production workflows:

- Ticker full-history ingestion:
  - `python3 scripts/full_history_ticker_sync.py --ticker BHP --years 10`
- Daily MarketIndex scrape/download:
  - `python3 scripts/daily_marketindex_action.py`
- Daily ASX all-announcements ingest:
  - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18`
- Bulk ASX enrichment sweep:
  - `python3 scripts/asx_enrichment_sweep_action.py --days-back 30 --process-documents`
- Headed MarketIndex blocked-doc recovery:
  - `python3 scripts/recover_marketindex_headed.py`

Data directories are initialized empty:

- `data/raw`
- `data/asx/docs`
- `data/marketindex/pdfs`
- `reports/marketindex`
EOF

(
  cd "${RELEASES_DIR}"
  rm -f "${ZIP_PATH}"
  zip -r "${ZIP_PATH}" "${PACKAGE_NAME}" >/dev/null
)

echo "Bundle directory: ${STAGE_DIR}"
echo "Bundle zip: ${ZIP_PATH}"
