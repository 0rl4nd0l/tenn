#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${STATE_DIR:-$ROOT_DIR/reports/change_review_agents}"
PID_DIR="$STATE_DIR/pids"
ROLES=(consistency validation planner)

stop_role() {
  local role="$1"
  local pid_file="$PID_DIR/$role.pid"
  if [[ ! -f "$pid_file" ]]; then
    echo "[change-review] $role not running (no pid file)"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "[change-review] stopped $role pid=$pid"
  else
    echo "[change-review] $role already stopped"
  fi
  rm -f "$pid_file"
}

for role in "${ROLES[@]}"; do
  stop_role "$role"
done
