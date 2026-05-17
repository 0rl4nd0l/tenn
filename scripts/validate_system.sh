#!/usr/bin/env bash
set -euo pipefail

fail=0
health_skipped=0
step_count=4

echo "[validate_system] 1/${step_count} healthcheck"
if bash scripts/agent_check.sh; then
  echo "[validate_system] OK: healthcheck"
else
  rc=$?
  if [[ "${rc}" -eq 2 ]]; then
    echo "[validate_system] SKIP due restricted environment: healthcheck (socket operations unavailable)"
    health_skipped=1
  else
    echo "[validate_system] FAIL: healthcheck" >&2
    fail=1
  fi
fi

SMOKE="financial-engine_v2/scripts/smoke_local.sh"
echo "[validate_system] 2/${step_count} smoke (${SMOKE})"
if [[ "${health_skipped}" -eq 1 ]]; then
  echo "[validate_system] SKIP due restricted environment: smoke (health checks unavailable)"
elif [[ -x "${SMOKE}" ]]; then
  if bash "${SMOKE}"; then
    echo "[validate_system] OK: smoke"
  else
    echo "[validate_system] FAIL: smoke" >&2
    fail=1
  fi
else
  echo "[validate_system] SKIP: smoke script not executable or missing (${SMOKE})" >&2
fi

echo "[validate_system] 3/${step_count} cockpit routing smoke"
if [[ "${COCKPIT_VALIDATE_ROUTING_SMOKE:-0}" != "1" ]]; then
  echo "[validate_system] SKIP: cockpit routing smoke (set COCKPIT_VALIDATE_ROUTING_SMOKE=1 to enable)"
elif [[ "${health_skipped}" -eq 1 ]]; then
  echo "[validate_system] SKIP due restricted environment: cockpit routing smoke (health checks unavailable)"
elif [[ -x "scripts/cockpit" ]]; then
  # shellcheck disable=SC2206
  routing_args=(${COCKPIT_ROUTING_SMOKE_ARGS:-})
  if scripts/cockpit smoke routing "${routing_args[@]}"; then
    echo "[validate_system] OK: cockpit routing smoke"
  else
    echo "[validate_system] FAIL: cockpit routing smoke" >&2
    fail=1
  fi
else
  echo "[validate_system] SKIP: scripts/cockpit not executable or missing" >&2
fi

echo "[validate_system] 4/${step_count} memory integrity"
if [[ "${TENN_VALIDATE_MEMORY_INTEGRITY:-1}" != "1" ]]; then
  echo "[validate_system] SKIP: memory integrity (set TENN_VALIDATE_MEMORY_INTEGRITY=1 to enable)"
elif [[ ! -f "scripts/audit_memory_integrity.py" ]]; then
  echo "[validate_system] SKIP: memory integrity script missing" >&2
elif [[ ! -f "${TENN_MEMORY_MARKET_DB:-financial-engine_v2/data/reports/research_memory/market_memory.sqlite}" ]]; then
  echo "[validate_system] SKIP: memory integrity market DB missing (${TENN_MEMORY_MARKET_DB:-financial-engine_v2/data/reports/research_memory/market_memory.sqlite})"
elif [[ ! -f "${TENN_TICKER_IDENTITY_MAP:-financial-engine_v2/config/ticker_identity_map.json}" ]]; then
  echo "[validate_system] SKIP: memory integrity identity map missing (${TENN_TICKER_IDENTITY_MAP:-financial-engine_v2/config/ticker_identity_map.json})"
else
  memory_args=(
    --market-memory "${TENN_MEMORY_MARKET_DB:-financial-engine_v2/data/reports/research_memory/market_memory.sqlite}"
    --identity-map "${TENN_TICKER_IDENTITY_MAP:-financial-engine_v2/config/ticker_identity_map.json}"
    --fallback-root "${TENN_MEMORY_FALLBACK_ROOT:-financial-engine_v2/backend/reports/research_memory}"
    --require-no-fallback-sqlite
    --forbidden-token BE
  )
  if [[ -f "${TENN_MEMORY_COMPANY_DB:-financial-engine_v2/data/reports/research_memory/company_memory.sqlite}" ]]; then
    memory_args+=(--company-memory "${TENN_MEMORY_COMPANY_DB:-financial-engine_v2/data/reports/research_memory/company_memory.sqlite}")
  fi
  if [[ -f "${TENN_MEMORY_MANUAL_REVIEW_CSV:-reports/memory_interticker_contamination_manifest_20260513_043646/csv/manual_review_rows.csv}" ]]; then
    memory_args+=(--company-manual-review-csv "${TENN_MEMORY_MANUAL_REVIEW_CSV:-reports/memory_interticker_contamination_manifest_20260513_043646/csv/manual_review_rows.csv}")
  fi
  if python3 scripts/audit_memory_integrity.py "${memory_args[@]}"; then
    echo "[validate_system] OK: memory integrity"
  else
    echo "[validate_system] FAIL: memory integrity" >&2
    fail=1
  fi
fi

exit "${fail}"
