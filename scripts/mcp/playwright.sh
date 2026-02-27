#!/usr/bin/env bash
set -euo pipefail

IMAGE="${PLAYWRIGHT_MCP_IMAGE:-mcr.microsoft.com/playwright/mcp:latest}"
PULL_POLICY="${PLAYWRIGHT_MCP_PULL_POLICY:-missing}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for playwright MCP server" >&2
  exit 1
fi

docker run --rm -i --init --network host --pull "${PULL_POLICY}" "${IMAGE}" "$@"
