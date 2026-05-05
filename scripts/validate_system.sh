#!/usr/bin/env bash
set -euo pipefail

fail=0
health_skipped=0

echo "[validate_system] 1/3 healthcheck"
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
echo "[validate_system] 2/3 smoke (${SMOKE})"
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

echo "[validate_system] 3/3 cockpit routing smoke"
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

exit "${fail}"
