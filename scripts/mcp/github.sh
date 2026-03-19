#!/usr/bin/env bash
set -euo pipefail

IMAGE="${GITHUB_MCP_IMAGE:-ghcr.io/github/github-mcp-server:latest}"
READ_ONLY="${GITHUB_READ_ONLY:-1}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for github MCP server" >&2
  exit 1
fi

if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  echo "GITHUB_PERSONAL_ACCESS_TOKEN is required for github MCP server" >&2
  exit 1
fi

export GITHUB_READ_ONLY="${READ_ONLY}"

env_args=(
  "-e" "GITHUB_PERSONAL_ACCESS_TOKEN"
  "-e" "GITHUB_READ_ONLY"
)

for key in GITHUB_TOOLSETS GITHUB_DYNAMIC_TOOLSETS GITHUB_OWNER GITHUB_REPO GITHUB_HOST GITHUB_API_URL; do
  if [[ -n "${!key:-}" ]]; then
    env_args+=("-e" "${key}")
  fi
done

docker run --rm -i "${env_args[@]}" "${IMAGE}" "$@"
