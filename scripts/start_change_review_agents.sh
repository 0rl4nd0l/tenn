#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${STATE_DIR:-$ROOT_DIR/reports/change_review_agents}"
LOG_DIR="$STATE_DIR/logs"
PID_DIR="$STATE_DIR/pids"
POLL_SECONDS="${POLL_SECONDS:-6}"
DEFAULT_PYTHON_BIN="$ROOT_DIR/financial-engine_v2/.venv/bin/python"
if [[ -x "$DEFAULT_PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON_BIN}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
SETSID_BIN="${SETSID_BIN:-$(command -v setsid || true)}"
ROLES=(consistency validation planner)

mkdir -p "$LOG_DIR" "$PID_DIR"

start_role() {
  local role="$1"
  local pid_file="$PID_DIR/$role.pid"
  local log_file="$LOG_DIR/$role.log"
  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" >/dev/null 2>&1; then
      echo "[change-review] $role already running pid=$existing_pid log=$log_file"
      return
    fi
  fi

  if [[ -n "$SETSID_BIN" ]]; then
    nohup env PYTHONUNBUFFERED=1 "$SETSID_BIN" "$PYTHON_BIN" "$ROOT_DIR/scripts/change_review_agents.py" \
      --role "$role" \
      --repo-root "$ROOT_DIR" \
      --state-dir "$STATE_DIR" \
      --poll-seconds "$POLL_SECONDS" \
      </dev/null >"$log_file" 2>&1 &
  else
    nohup env PYTHONUNBUFFERED=1 "$PYTHON_BIN" "$ROOT_DIR/scripts/change_review_agents.py" \
      --role "$role" \
      --repo-root "$ROOT_DIR" \
      --state-dir "$STATE_DIR" \
      --poll-seconds "$POLL_SECONDS" \
      </dev/null >"$log_file" 2>&1 &
  fi
  local pid=$!
  disown "$pid" 2>/dev/null || true
  sleep 0.2
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    echo "[change-review] failed to start $role; see $log_file" >&2
    return 1
  fi
  echo "$pid" >"$pid_file"
  echo "[change-review] started $role pid=$pid log=$log_file"
}

for role in "${ROLES[@]}"; do
  start_role "$role"
done

echo "[change-review] latest overview: $STATE_DIR/latest/overview.md"
echo "[change-review] alerts: $STATE_DIR/alerts.jsonl"
