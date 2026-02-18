#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TICKER="${TICKER:-BHP}"

echo "[1/3] Health"
curl -sS "${BASE_URL}/api/health"
echo

echo "[2/3] Sync backfill (no extraction/embeddings by default local mode)"
curl -sS -X POST "${BASE_URL}/api/backfill/ticker/${TICKER}?years=1&process_documents=false"
echo

echo "[3/3] Docs count"
curl -sS "${BASE_URL}/api/docs?ticker=${TICKER}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print({"ticker": rows[0]["ticker"] if rows else None, "count": len(rows)})'
