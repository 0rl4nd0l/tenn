# MCP Servers

MCP (Model Context Protocol) servers extend Claude Code with direct access to external services. They are configured in `.mcp.json` at the repo root and launched as stdio subprocesses.

## Source Trace
- `.mcp.json` (Confirmed)
- `scripts/mcp/*.sh` (Confirmed — launcher scripts; not all launchers are enabled by default)
- `.claude/settings.local.json` → `enabledMcpjsonServers` (Confirmed)

---

## Server Reference

| Server | Launcher | Docker Image | Purpose |
|--------|----------|-------------|---------|
| **qdrant** | `scripts/mcp/qdrant.sh` | `mcp-server-qdrant:latest` | Search vectors, inspect collections, verify embeddings |
| **redis** | `scripts/mcp/redis.sh` | `mcp/redis:latest` | Inspect Celery task queues, check worker state, monitor backlog |
| **playwright** | `scripts/mcp/playwright.sh` | `mcr.microsoft.com/playwright/mcp:latest` | Browser automation, API response inspection, Lighthouse audits |
| **github** | `scripts/mcp/github.sh` | `ghcr.io/github/github-mcp-server:latest` | GitHub issues, PRs, checks, releases — active as of 2026-03-22 |
| **tenn** | `scripts/mcp/tenn.sh` | _(native Python)_ | Disabled by default; custom Tenn/OpenClaw MCP server (`openclaw.tenn_mcp_server`) |
| **screenpipe** | `scripts/mcp/screenpipe.sh` | _(native macOS app + npx mcp-remote)_ | Query screen/audio history captured by Screenpipe on Mac |

### Default `.mcp.json` (token-light)

The checked-in `.mcp.json` enables only **redis**, **qdrant**, and **jam** so MCP tool schemas stay small in Cursor/Claude. The Tenn MCP server is intentionally not registered by default.

### Optional: add repo launcher MCPs

Merge any of these into `mcpServers` when needed:

```json
"github":     { "command": "./scripts/mcp/github.sh" },
"playwright": { "command": "./scripts/mcp/playwright.sh" },
"screenpipe": { "command": "./scripts/mcp/screenpipe.sh" }
```

### Optional: generic `npx` MCP packages

| Package | Purpose |
|---------|---------|
| `@modelcontextprotocol/server-sequential-thinking` | Step-by-step reasoning tool |
| `@modelcontextprotocol/server-everything` | Large bundled demo surface (very heavy on context) |

```json
"sequential-thinking": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"] },
"everything": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"] }
```

---

## Prerequisites

| Server | Requirements |
|--------|-------------|
| **qdrant** | Docker; `mcp-server-qdrant:latest` image (build: `docker build -t mcp-server-qdrant:latest https://github.com/qdrant/mcp-server-qdrant.git`) |
| **redis** | Docker; `mcp/redis:latest` image (`docker pull mcp/redis`) |
| **playwright** | Docker; image auto-pulls on first use |
| **github** | Docker; `GITHUB_PERSONAL_ACCESS_TOKEN` env var set; image must be pulled (`docker pull ghcr.io/github/github-mcp-server:latest`) |
| **screenpipe** | Screenpipe app installed and running on Mac; Node.js/npx on Linux; SSH tunnel on port 3030 active |

---

## Environment Variables

MCP launcher scripts read these from the environment:

| Variable | Default | Used By |
|----------|---------|---------|
| `SCREENPIPE_URL` | `http://localhost:3030/sse` | screenpipe |
| `QDRANT_URL` | `http://127.0.0.1:6333` | qdrant |
| `QDRANT_API_KEY` | _(none)_ | qdrant (optional) |
| `COLLECTION_NAME` | _(none)_ | qdrant (optional) |
| `REDIS_HOST` | `127.0.0.1` | redis |
| `REDIS_PORT` | `6379` | redis |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | _(required)_ | github |
| `GITHUB_READ_ONLY` | `1` | github |

---

## Startup

MCP servers start automatically when Claude Code launches, if `.mcp.json` exists and the server is listed in `enabledMcpjsonServers` in `.claude/settings.local.json`.

All servers use `--network host` for Docker, so they connect to localhost services (Qdrant, Redis) without extra configuration.

**Verify server availability:** MCP tools appear in `ToolSearch` results and system reminders at session start. If a server fails to start, its tools will be absent.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| MCP tools not appearing | `.mcp.json` missing at repo root | Confirm `/home/l4nd0/tenn/.mcp.json` exists |
| MCP tools not appearing | Server not in `enabledMcpjsonServers` | Add to `.claude/settings.local.json` |
| Qdrant MCP fails to start | Docker image not built | `docker build -t mcp-server-qdrant:latest https://github.com/qdrant/mcp-server-qdrant.git` |
| GitHub MCP fails to start | Missing PAT | Export `GITHUB_PERSONAL_ACCESS_TOKEN` |
| Server starts but can't reach service | Service not running | Start the backing service (Qdrant, Redis, etc.) |
| Screenpipe MCP fails | SSH tunnel not active | `ssh -L 3030:localhost:3030 <mac-host>` |
| Screenpipe MCP fails | Screenpipe not running on Mac | Launch Screenpipe.app on Mac |
| Screenpipe MCP fails | npx not installed | Install Node.js on Linux host |

---

## Workflow Integration

**Financial pipeline verification:**
- Use **qdrant** MCP to inspect `commentary_chunks` collection directly — verify embedding counts, search quality, collection metadata
- Use **redis** MCP to inspect Celery task state — check queue depth, worker status, failed tasks

**Development (opt-in — add to `.mcp.json`):**
- **playwright** MCP for browser checks against FastAPI
- **github** MCP for PR/issue workflows (needs PAT + Docker)

## Claude Code GitHub Actions

`.github/workflows/claude.yml` integrates Claude Code into GitHub CI.

| Job | Trigger | Behavior |
|-----|---------|----------|
| `claude-on-mention` | `@claude` in any PR/issue comment | Claude responds to the mention with tool access |
| `claude-pr-review` | PR opened or `synchronize` | Claude auto-reviews the diff against CLAUDE.md rules |

**Setup:** Add `ANTHROPIC_API_KEY` as a GitHub Actions secret in the repo settings. The PAT from the MCP server is unrelated — Actions use the `GITHUB_TOKEN` granted by GitHub automatically.

---

## Adding a New MCP Server

1. Create a launcher script in `scripts/mcp/` (see existing scripts for pattern)
2. Add the server entry to `.mcp.json`
3. Add to `enabledMcpjsonServers` in `.claude/settings.local.json`
4. Restart Claude Code
5. Update this doc
