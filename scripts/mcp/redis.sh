#!/usr/bin/env bash
set -euo pipefail

IMAGE="${REDIS_MCP_IMAGE:-mcp/redis:latest}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for redis MCP server" >&2
  exit 1
fi

export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"

env_args=(
  "-e" "REDIS_HOST"
  "-e" "REDIS_PORT"
)

for key in REDIS_USERNAME REDIS_PWD REDIS_DB REDIS_TLS REDIS_CA_CERT_PATH REDIS_CLIENT_CERT_PATH REDIS_CLIENT_KEY_PATH; do
  if [[ -n "${!key:-}" ]]; then
    env_args+=("-e" "${key}")
  fi
done

docker run --rm -i --network host "${env_args[@]}" "${IMAGE}" "$@"
