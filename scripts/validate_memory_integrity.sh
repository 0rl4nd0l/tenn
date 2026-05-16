#!/usr/bin/env bash
set -euo pipefail

if [[ "${TENN_VALIDATE_MEMORY_INTEGRITY:-1}" != "1" ]]; then
  echo "[validate_memory_integrity] SKIP: disabled (set TENN_VALIDATE_MEMORY_INTEGRITY=1 to enable)"
  exit 0
fi

MARKET_DB="${TENN_MEMORY_MARKET_DB:-financial-engine_v2/data/reports/research_memory/market_memory.sqlite}"
IDENTITY_MAP="${TENN_TICKER_IDENTITY_MAP:-financial-engine_v2/config/ticker_identity_map.json}"
FALLBACK_ROOT="${TENN_MEMORY_FALLBACK_ROOT:-financial-engine_v2/backend/reports/research_memory}"
COMPANY_DB="${TENN_MEMORY_COMPANY_DB:-financial-engine_v2/data/reports/research_memory/company_memory.sqlite}"
MANUAL_REVIEW_CSV="${TENN_MEMORY_MANUAL_REVIEW_CSV:-reports/memory_interticker_contamination_manifest_20260513_043646/csv/manual_review_rows.csv}"

if [[ ! -f "scripts/audit_memory_integrity.py" ]]; then
  echo "[validate_memory_integrity] SKIP: memory integrity script missing" >&2
  exit 0
elif [[ ! -f "${MARKET_DB}" ]]; then
  echo "[validate_memory_integrity] SKIP: market DB missing (${MARKET_DB})"
  exit 0
elif [[ ! -f "${IDENTITY_MAP}" ]]; then
  echo "[validate_memory_integrity] SKIP: identity map missing (${IDENTITY_MAP})"
  exit 0
fi

memory_args=(
  --market-memory "${MARKET_DB}"
  --identity-map "${IDENTITY_MAP}"
  --fallback-root "${FALLBACK_ROOT}"
  --require-no-fallback-sqlite
  --forbidden-token BE
)

if [[ -f "${COMPANY_DB}" ]]; then
  memory_args+=(--company-memory "${COMPANY_DB}")
fi
if [[ -f "${MANUAL_REVIEW_CSV}" ]]; then
  memory_args+=(--company-manual-review-csv "${MANUAL_REVIEW_CSV}")
fi

python3 scripts/audit_memory_integrity.py "${memory_args[@]}"
