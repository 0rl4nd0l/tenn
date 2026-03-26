# HANDOFF — MCP Orchestrator Endpoints

**Implemented:** 2026-03-26 (branch `cloud/session-20260319`)
**Commit:** `c3812666` — milestone(mcp): tenn orchestrator endpoints

---

## What Was Implemented

### Backend (1 new endpoint)

| Endpoint | Auth | Source |
|----------|------|--------|
| `GET /api/queue/status` | `X-API-Key` | `financial-engine_v2/backend/app/main.py` |

Returns Celery queue depths via Redis LLEN on the 5 specialized queues (ingest, embed, score, llm_gpu, llm_cpu).

### MCP Server (5 new tools)

All in `openclaw/tenn_mcp_server.py`. Read-only, 3s timeouts, graceful `unreachable` responses.

| Tool | Calls | What It Returns |
|------|-------|-----------------|
| `tenn_health` | `/api/health` + `/api/system/status` + Ollama + llama.cpp | Aggregate service health (healthy/degraded/unhealthy) |
| `tenn_eval_baseline` | Disk read only | Latest extraction eval score, staleness flag |
| `tenn_queue_status` | `/api/queue/status` | Per-queue message depths |
| `tenn_collections` | `/api/system/status` | Qdrant collection list + document count |
| `tenn_pipeline_status` | `/api/system/status` | Last ingestion timestamp + document count |

### Design Decisions

- **Injectable `http_requester`**: Same pattern as `command_runner` — tests inject stubs, no mocking needed.
- **stdlib only**: `urllib.request` with `ProxyHandler({})` — no new dependencies.
- **API key**: `TENN_BACKEND_API_KEY` env var, read at call time. Empty = no header sent (backend treats empty key as no-op).
- **Eval staleness**: `age_seconds` + `stale` boolean (threshold: 24h). Timestamp parsed from filename, not mtime.
- **`openWorldHint: True`**: Set on all network-calling tools per MCP spec.

---

## Services Required for Live Validation

| Service | Port | Required By |
|---------|------|-------------|
| Backend API | 8000 | tenn_health, tenn_queue_status, tenn_collections, tenn_pipeline_status |
| Redis | 6379 | tenn_queue_status (via backend) |
| Qdrant | 6333 | tenn_collections (via backend) |
| Ollama | 11434 | tenn_health |
| llama.cpp | 8001 | tenn_health |

Start the backend:
```bash
cd financial-engine_v2
LOCAL_BACKEND_PROFILE=full ./scripts/run_local_backend.sh
```

---

## Manual Verification Commands

```bash
# Backend health (no auth)
curl -sS http://127.0.0.1:8000/api/health | python3 -m json.tool

# System status (requires API key if configured)
curl -sS -H "X-API-Key: ${TENN_BACKEND_API_KEY}" http://127.0.0.1:8000/api/system/status | python3 -m json.tool

# Queue status
curl -sS -H "X-API-Key: ${TENN_BACKEND_API_KEY}" http://127.0.0.1:8000/api/queue/status | python3 -m json.tool

# MCP tool invocation (via Claude Code / MCP client)
# Each tool is invocable as: tenn_health, tenn_eval_baseline, tenn_queue_status, tenn_collections, tenn_pipeline_status
# All take no arguments: {"name": "tenn_health", "arguments": {}}
```

---

## Configuration

### Environment Variables (MCP server process)

| Variable | Default | Purpose |
|----------|---------|---------|
| `TENN_BACKEND_URL` | `http://127.0.0.1:8000` | Backend API base URL |
| `TENN_BACKEND_API_KEY` | (empty) | API key for authenticated endpoints |
| `TENN_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama health probe target |
| `TENN_LLAMACPP_URL` | `http://127.0.0.1:8001` | llama.cpp health probe target |

### `.mcp.json`

No changes needed — the Tenn MCP server is already configured at `./scripts/mcp/tenn.sh`. The new tools are automatically available when the server starts.

---

## Follow-Up Items

1. **Live smoke test**: Start all services and invoke each tool via an MCP client. Verify responses match expected schema.
2. **Claude.ai orchestrator integration**: Configure the orchestrator project to call these tools for health/status checks.
3. **Queue depth enrichment**: Consider adding `active_workers` count if Celery workers are running (requires `celery inspect active`, currently not implemented).
4. **Collection vector counts**: The backend `/api/system/status` returns collection names but not per-collection vector counts. A follow-up could add `get_qdrant_collection_vector_config()` calls for richer data.
