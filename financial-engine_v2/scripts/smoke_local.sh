#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TICKER="${TICKER:-BHP}"
API_KEY="${API_KEY:-${TENN_API_KEY:-local-dev-key}}"
AUTH_HEADER=("-H" "X-API-Key: ${API_KEY}")

echo "[1/3] Health"
curl -sS "${BASE_URL}/api/health"
echo

echo "[2/3] Sync backfill (no extraction/embeddings by default local mode)"
curl -sS "${AUTH_HEADER[@]}" -X POST "${BASE_URL}/api/backfill/ticker/${TICKER}?years=1&process_documents=false"
echo

echo "[3/3] Docs count"
curl -sS "${AUTH_HEADER[@]}" "${BASE_URL}/api/docs?ticker=${TICKER}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print({"ticker": rows[0]["ticker"] if rows else None, "count": len(rows)})'
