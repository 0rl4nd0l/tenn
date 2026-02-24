#!/usr/bin/env bash
set -euo pipefail

BACKEND_APP_ROOT="${BACKEND_APP_ROOT:-/app_backend}"
if [[ -d "${BACKEND_APP_ROOT}" ]]; then
  # Import backend modules directly from mounted source; avoid runtime pip installs.
  export PYTHONPATH="${BACKEND_APP_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${BACKEND_APP_ROOT}"
fi

exec "$@"
