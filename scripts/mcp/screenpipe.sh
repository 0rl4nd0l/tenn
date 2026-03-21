#!/usr/bin/env bash
set -euo pipefail

# Screenpipe MCP server — bridges stdio (Claude Code) to Screenpipe's HTTP/SSE endpoint.
# Screenpipe must be running on the Mac and port 3030 forwarded via SSH tunnel:
#   ssh -L 3030:localhost:3030 <mac-host>
#
# Override endpoint via SCREENPIPE_URL env var if needed.
SCREENPIPE_URL="${SCREENPIPE_URL:-http://localhost:3030/sse}"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required for screenpipe MCP (install Node.js)" >&2
  exit 1
fi

exec npx -y mcp-remote "${SCREENPIPE_URL}" "$@"
