#!/usr/bin/env bash
set -euo pipefail

fail=0

echo "[validate_system] 1/2 healthcheck"
if bash scripts/agent_check.sh; then
  echo "[validate_system] OK: healthcheck"
else
  echo "[validate_system] FAIL: healthcheck" >&2
  fail=1
fi

SMOKE="financial-engine_v2/scripts/smoke_local.sh"
echo "[validate_system] 2/2 smoke (${SMOKE})"
if [[ -x "${SMOKE}" ]]; then
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

