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
| `EXTRACT_MODEL` | `qwen2.5-14b-instruct` | Model name for extraction workloads. Should be an instruct-tuned model (not a coder model) for reliable structured JSON output from financial documents. |
| `LLM_API_KEY` | `local-openai-key` | Used for local OpenAI-compatible auth. |
| `LLAMA_SERVER_ROUTER_MODE` | `1` | Enable router mode for zero-downtime model switching (`~/.config/tenn/llama-server.env`). Set to `0` for single-model legacy mode. |
| `LLAMA_SERVER_MODELS_DIR` | `$ROOT/models` | Directory of `.gguf` files for router mode model discovery (`~/.config/tenn/llama-server.env`). |
| `EMBEDDING_BATCH_SIZE` | `32` | Default embedding batch size. |
| `ROUTER_FEEDBACK_ENABLED` | `true` | Enables analyzer feedback in routing. |
| `ANALYZER_MAX_AGE_SECONDS` | `600` | Analyzer report freshness window. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Canonical Redis connection. |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Broker URL for Celery mode. |
| `CELERY_RESULT_BACKEND` | `redis://127.0.0.1:6379/1` | Result backend for Celery mode. |
| `ENABLE_SESSION_MEMORY` | `true` | Enable OpenViking session memory for `/api/chat`. Set to `false` to disable. |
| `HYBRID_ROUTER_POLICY` | `local_only` | Cockpit HybridRouter routing policy. Options: `local_only` (default), `local_preferred`, `api_preferred`, `api_only`. The router never calls a cloud API unless an `api_client` is explicitly configured **and** the policy is `api_preferred` or `api_only`. |
| `OPENVIKING_CONFIG_FILE` | _(injected by launcher)_ | Absolute path to domain-specific `ov.conf`. Backend defaults to `~/.openviking/backend.ov.conf`; cockpit defaults to `~/.openviking/cockpit.ov.conf`. Override to point at a different workspace. |
| `ANTHROPIC_API_KEY` | _(unset)_ | Anthropic API key for the cockpit `AnthropicClient`. Required only when `HYBRID_ROUTER_POLICY` is `api_preferred` or `api_only`. The router never calls the Anthropic API unless this is set **and** the policy allows it. |
| `BRAVE_SEARCH_API_KEY` | _(unset)_ | Brave Search API key for the cockpit `search_web` tool. When set, the cockpit uses Brave for web search (higher quality, structured results). When absent, falls back to DuckDuckGo via `WebFetcher`. Free tier: 2,000 queries/month at [brave.com/search/api](https://brave.com/search/api/). |

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

Separate extraction from chat (recommended for production):

```dotenv
# Chat/coding server — loads qwen2.5-coder-14b or similar
LLAMACPP_URL=http://127.0.0.1:8001

# Extraction server — loads qwen2.5-14b-instruct for PDF metric extraction
EXTRACTION_LLAMACPP_URL=http://127.0.0.1:8002
EXTRACT_MODEL=qwen2.5-14b-instruct
```

When `EXTRACTION_LLAMACPP_URL` is not set, extraction uses `LLAMACPP_URL` (single-server mode).

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
