#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${STATE_DIR:-$ROOT_DIR/reports/change_review_agents}"
PID_DIR="$STATE_DIR/pids"
ROLES=(consistency validation planner)

for role in "${ROLES[@]}"; do
  pid_file="$PID_DIR/$role.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "[change-review] $role running pid=$pid"
    else
      echo "[change-review] $role stale pid file ($pid)"
    fi
  else
    echo "[change-review] $role stopped"
  fi
done

if [[ -f "$STATE_DIR/latest/overview.md" ]]; then
  echo "[change-review] overview: $STATE_DIR/latest/overview.md"
fi
if [[ -f "$STATE_DIR/alerts.jsonl" ]]; then
  echo "[change-review] alerts: $STATE_DIR/alerts.jsonl"
fi
