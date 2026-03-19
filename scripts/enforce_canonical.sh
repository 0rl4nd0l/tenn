#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

warn() { echo "[enforce_canonical] WARNING: $*" >&2; }
ok() { echo "[enforce_canonical] OK: $*"; }

# Heuristic-only guardrails: no hard fails, no runtime changes.

if curl -fsS --connect-timeout 2 --max-time 3 "${BASE_URL}/api/health" >/dev/null; then
  ok "backend reachable (${BASE_URL}/api/health)"
else
  warn "backend not reachable (${BASE_URL}/api/health). Canonical start: bash financial-engine_v2/scripts/run_local_backend.sh"
fi

if ps aux | rg -n "(^|/)python(3)?\\s+run\\.py(\\s|$)" >/dev/null 2>&1; then
  warn "detected 'python run.py' process. This is a batch runner, not the canonical agent startup."
fi

if ps aux | rg -n "uvicorn\\s+app\\.main:app" >/dev/null 2>&1; then
  ok "uvicorn app.main:app process detected"
else
  warn "no 'uvicorn app.main:app' process detected"
fi

warn "canonical path for agents is financial-engine_v2/scripts/run_local_backend.sh (see docs/entrypoints.md)"
exit 0

