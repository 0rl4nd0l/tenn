#!/usr/bin/env bash
set -euo pipefail

IMAGE="${QDRANT_MCP_IMAGE:-mcp-server-qdrant:latest}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for qdrant MCP server" >&2
  exit 1
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  cat >&2 <<EOF
Qdrant MCP image not found: ${IMAGE}
Build it once with:
  docker build -t mcp-server-qdrant:latest https://github.com/qdrant/mcp-server-qdrant.git
Or set QDRANT_MCP_IMAGE to an existing image name.
EOF
  exit 1
fi

export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"

env_args=(
  "-e" "QDRANT_URL"
)

for key in QDRANT_API_KEY COLLECTION_NAME; do
  if [[ -n "${!key:-}" ]]; then
    env_args+=("-e" "${key}")
  fi
done

# Force stdio transport for MCP clients (Codex/Claude/Cursor expect stdio command servers).
docker run --rm -i --network host "${env_args[@]}" "${IMAGE}" mcp-server-qdrant --transport stdio "$@"
