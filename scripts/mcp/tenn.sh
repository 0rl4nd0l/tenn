#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

DEFAULT_VENV_PY="${REPO_ROOT}/.venv-autodev/bin/python"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="${PYTHON_BIN}"
elif [[ -x "${DEFAULT_VENV_PY}" ]]; then
  PYTHON_BIN="${DEFAULT_VENV_PY}"
else
  PYTHON_BIN="python3"
fi

exec "${PYTHON_BIN}" -m openclaw.tenn_mcp_server --repo-root "${REPO_ROOT}" "$@"
