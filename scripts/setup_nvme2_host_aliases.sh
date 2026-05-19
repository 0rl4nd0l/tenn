#!/usr/bin/env bash
set -euo pipefail

DATA_TARGET="/mnt/tenn-nvme2/tenn/financial-engine_v2/data"
REPORTS_TARGET="/mnt/tenn-nvme2/tenn/financial-engine_v2/reports"

ensure_alias() {
  local link_path="$1"
  local target_path="$2"

  if [[ ! -d "$target_path" ]]; then
    echo "ERROR: target is missing or not a directory: $target_path" >&2
    return 1
  fi

  if [[ -L "$link_path" ]]; then
    local resolved
    resolved="$(readlink -f "$link_path")"
    if [[ "$resolved" == "$target_path" ]]; then
      echo "OK: $link_path -> $resolved"
      return 0
    fi
    echo "ERROR: $link_path already points to $resolved, expected $target_path" >&2
    return 1
  fi

  if [[ -e "$link_path" ]]; then
    echo "ERROR: $link_path exists and is not a symlink; refusing to overwrite" >&2
    return 1
  fi

  ln -s "$target_path" "$link_path"
  echo "CREATED: $link_path -> $target_path"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: this script must run with sudo/root to create host-root aliases" >&2
  echo "Run: sudo $0" >&2
  exit 1
fi

ensure_alias /data "$DATA_TARGET"
ensure_alias /reports "$REPORTS_TARGET"

readlink -f /data
readlink -f /reports
