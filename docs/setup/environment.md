# Environment Setup

The active runtime is `financial-engine_v2`. The canonical env file lives at `financial-engine_v2/.env`.

## Canonical env spec

| Variable | Default | Notes |
| --- | --- | --- |
| `DATA_ROOT` | `./data` | Root for runtime data, reports, and derived paths. |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant vector store endpoint. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL. |
| `LLAMACPP_URL` | `http://127.0.0.1:8001` | llama.cpp endpoint for chat, coding, and routing. |
| `EXTRACTION_BACKEND` | `pymupdf` | PDF structure extraction backend. `pymupdf` (default): fast PyMuPDF `find_tables()`, ~1-25s, no ML models. `docling`: IBM docling with TableFormer, 120s+, for complex/scanned PDFs. |
| `EXTRACTION_LLAMACPP_URL` | _(falls back to `LLAMACPP_URL`)_ | Dedicated llama.cpp endpoint for PDF extraction. When set, multipass extraction and commentary extraction use this instead of `LLAMACPP_URL`. Allows running an instruct model for extraction on a separate GPU/instance from the chat/coding server. |
| `EXTRACT_MODEL` | `qwen2.5-14b-instruct` | Model name for extraction workloads. In router mode, extraction requests this model by name and the server loads it on demand. Should be an instruct-tuned model for reliable structured JSON output from financial documents. |
| `LLM_API_KEY` | `local-openai-key` | Used for local OpenAI-compatible auth. |
| `LLAMA_SERVER_ROUTER_MODE` | `1` | Enable router mode for zero-downtime model switching (`~/.config/tenn/llama-server.env`). Set to `0` for single-model legacy mode. |
| `LLAMA_SERVER_MODELS_DIR` | `/mnt/nvme/tenn/models` | Directory of `.gguf` files for router mode model discovery (`~/.config/tenn/llama-server.env`). The launcher now fails instead of silently falling back to a repo-local models directory. |
| `LLAMA_SERVER_MMAP` | `1` | Set to `0` so `scripts/run_llama_server.sh` and `scripts/run_extraction_server.sh` pass `--no-mmap` when mmap-based load stalls on Tesla M40 (see `docs/ops/09_llama_server_m40_model_load_runbook.md`). |
| `EMBEDDING_BATCH_SIZE` | `32` | Default embedding batch size. |
| `ROUTER_FEEDBACK_ENABLED` | `true` | Enables analyzer feedback in routing. |
| `ANALYZER_MAX_AGE_SECONDS` | `600` | Analyzer report freshness window. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Canonical Redis connection. |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Broker URL for Celery mode. |
| `CELERY_RESULT_BACKEND` | `redis://127.0.0.1:6379/1` | Result backend for Celery mode. |
| `ENABLE_SESSION_MEMORY` | `true` | Enable OpenViking session memory for `/api/chat`. Set to `false` to disable. |
| `COCKPIT_LLM_PROFILE` | `ops` | Cockpit high-level preset when `HYBRID_ROUTER_POLICY` is unset: `ops` (local-first when local + Anthropic are available), `advisor` (API-first when a key is present), or `balanced` (same mapping as `advisor`). Optional per-message override: prefix chat with `/advisor` or `/local`. |
| `COCKPIT_TOOL_DEBUG` | _(unset)_ | In-chat lines after each agent reply for tool calls: default / `failures` shows only failed tools with a short hint; `1` / `all` / `full` logs every tool call and timing; `off` disables chat lines (failures still log at WARNING). |
| `HYBRID_ROUTER_POLICY` | _(unset)_ | When set, overrides `COCKPIT_LLM_PROFILE`. Cockpit HybridRouter policy: `local_only`, `local_preferred`, `api_preferred`, `api_only`. The router never calls a cloud API unless an `api_client` is explicitly configured **and** the policy is `api_preferred` or `api_only`. |
| `OPENVIKING_CONFIG_FILE` | _(injected by launcher)_ | Absolute path to domain-specific `ov.conf`. Backend defaults to `~/.openviking/backend.ov.conf`; cockpit defaults to `~/.openviking/cockpit.ov.conf`. Override to point at a different workspace. |
| `ANTHROPIC_API_KEY` | _(unset)_ | Anthropic API key for the cockpit `AnthropicClient`. Required only when `HYBRID_ROUTER_POLICY` is `api_preferred` or `api_only`. The router never calls the Anthropic API unless this is set **and** the policy allows it. |
| `BRAVE_SEARCH_API_KEY` | _(unset)_ | Brave Search API key for the cockpit `search_web` tool. When set, the cockpit uses Brave for web search (higher quality, structured results). When absent, falls back to DuckDuckGo via `WebFetcher`. Free tier: 2,000 queries/month at [brave.com/search/api](https://brave.com/search/api/). |

## .env loading

Both the **backend** (via pydantic-settings) and the **cockpit** (via `cockpit/main.py`) load `financial-engine_v2/.env` at startup. Shell environment variables take precedence — `.env` only fills in keys not already set.

The cockpit loads `.env` from its own repo root (`financial-engine_v2/.env`) before any config or TUI initialization. This is the canonical place to set `ANTHROPIC_API_KEY`, `BRAVE_SEARCH_API_KEY`, `LLM_API_KEY`, and other secrets that both the backend and cockpit need.

## Copy the template

```bash
cp financial-engine_v2/.env.example financial-engine_v2/.env
```

## Override examples

Use a different data root:

```dotenv
DATA_ROOT=/srv/tenn-data
```

Point the LLM endpoint to a different host:

```dotenv
LLAMACPP_URL=http://192.168.1.50:8001
```

Single-instance router mode (default — recommended):

```dotenv
# Single llama-server in router mode on 8001.
# All models served from NVMe; clients select per-request via "model" field.
# Chat default: qwen3-30b-a3b-instruct (llmfit score 94.0)
# Extraction: qwen2.5-14b-instruct (requested by model name, loaded on demand)
LLAMACPP_URL=http://127.0.0.1:8001
EXTRACT_MODEL=qwen2.5-14b-instruct
```

Legacy dual-server mode (set `EXTRACTION_LLAMACPP_URL` to enable):

```dotenv
LLAMACPP_URL=http://127.0.0.1:8001
EXTRACTION_LLAMACPP_URL=http://127.0.0.1:8002
EXTRACT_MODEL=qwen2.5-14b-instruct
```

When `EXTRACTION_LLAMACPP_URL` is not set, extraction uses `LLAMACPP_URL` (single-server router mode).

Switch Redis/Qdrant to Docker service names:

```dotenv
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

## Session memory setup (OpenViking)

Session memory is enabled by default but requires a local config file to activate. Launchers inject a domain-specific default path; copy the example and edit endpoints:

```bash
mkdir -p ~/.openviking
cp financial-engine_v2/config/openviking/backend.ov.conf.example ~/.openviking/backend.ov.conf
cp financial-engine_v2/config/openviking/cockpit.ov.conf.example ~/.openviking/cockpit.ov.conf
# For Claude Code dev sessions:
cp financial-engine_v2/config/openviking/claude-code.ov.conf.example ~/.openviking/claude-code.ov.conf
source scripts/openviking/export-claude-code-memory-env.sh  # before launching claude
```

Each config points at `llama.cpp` (port 8001) for VLM and `Ollama` (port 11434, `nomic-embed-text`) for embeddings. Workspaces are isolated: `~/.openviking/workspaces/{backend,cockpit,claude-code}`.

Validate a config:
```bash
scripts/openviking/check-local-memory.sh ~/.openviking/backend.ov.conf
```

If no config file exists the system degrades gracefully (stateless) with a single WARNING on startup.

## Validation

Run:

```bash
python scripts/check_environment.py
```

The checker validates resolved env values, key ports, and whether `DATA_ROOT` is writable.
