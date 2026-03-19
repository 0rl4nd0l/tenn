#!/usr/bin/env bash
set -euo pipefail

fail=0
health_skipped=0

echo "[validate_system] 1/2 healthcheck"
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
echo "[validate_system] 2/2 smoke (${SMOKE})"
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

exit "${fail}"
