#!/usr/bin/env bash
# Launch the Tenn code-change monitoring agents.
# Usage:
#   bash .claude/monitors/run_monitors.sh              # continuous (default 120s interval)
#   bash .claude/monitors/run_monitors.sh --once       # one-shot
#   bash .claude/monitors/run_monitors.sh --interval 60 --reset

set -euo pipefail

VENV_PYTHON="/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/monitor_agents.py"

if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' CLI not found on PATH." >&2
  exit 1
fi

exec "$VENV_PYTHON" "$SCRIPT" "$@"
