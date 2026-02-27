# MCP Servers (Codex)

This repo now includes Docker-backed MCP wrappers in `scripts/mcp/` and wired entries in `.mcp.json`.

## Configured servers

- `axon`: repo code intelligence (existing).
- `github`: GitHub API tools.
- `playwright`: browser automation/testing tools.
- `redis`: Redis inspection/tools.
- `qdrant`: Qdrant vector DB tools.

## Required env vars

Set these before launching Codex:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
export GITHUB_READ_ONLY=1
```

Optional overrides:

```bash
export GITHUB_TOOLSETS="repos,issues,pull_requests,actions"
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="6379"
export QDRANT_URL="http://127.0.0.1:6333"
export COLLECTION_NAME="documents"
```

## One-time setup for Qdrant MCP image

The qdrant wrapper expects a local Docker image named `mcp-server-qdrant:latest`.

```bash
docker build -t mcp-server-qdrant:latest https://github.com/qdrant/mcp-server-qdrant.git
```

Note: this repo's wrapper forces `--transport stdio` for Codex MCP compatibility.

If you prefer a different image name, set:

```bash
export QDRANT_MCP_IMAGE="your-image:tag"
```

## Script locations

- `scripts/mcp/github.sh`
- `scripts/mcp/playwright.sh`
- `scripts/mcp/redis.sh`
- `scripts/mcp/qdrant.sh`
