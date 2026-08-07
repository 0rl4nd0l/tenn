# Environment Setup

The active runtime is `financial-engine_v2`. The canonical env file lives at `financial-engine_v2/.env`.

Freshness note: during the 2026-06-23 docs audit, checked-in launcher and
verifier evidence pointed runtime data and models at `/mnt/tenn-nvme2/tenn/...`.
Older `/mnt/nvme/tenn/...` examples below are retained as historical or
alternate-host examples until refreshed by a runtime/topology task. This docs
audit did not prove backend, Qdrant, Postgres, or Cockpit functionality.

## Canonical env spec

| Variable | Default | Notes |
| --- | --- | --- |
| `DATA_ROOT` | `./data` template default; launcher default if unset is currently `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` | Root for runtime data, reports, and derived paths. Host overrides are environment-specific and must be rechecked before runtime work. |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant vector store endpoint. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL. |
| `LLAMACPP_URL` | `http://127.0.0.1:8001` | llama.cpp endpoint for chat, coding, and routing. |
| `EXTRACTION_BACKEND` | `docling` | PDF structure extraction backend. `docling` (default): higher-fidelity table extraction for the multipass pipeline. `pymupdf`: fast fallback/override via `EXTRACTION_BACKEND=pymupdf` when speed is preferred. |
| `EXTRACTION_LLAMACPP_URL` | _(falls back to `LLAMACPP_URL`)_ | Dedicated llama.cpp endpoint for PDF extraction. When set, multipass extraction and commentary extraction use this instead of `LLAMACPP_URL`. Allows running an instruct model for extraction on a separate GPU/instance from the chat/coding server. |
| `EXTRACT_MODEL` | `qwen2.5-14b-instruct` | Model name for extraction workloads. In router mode, extraction requests this model by name and the server loads it on demand. Should be an instruct-tuned model for reliable structured JSON output from financial documents. |
| `LLM_API_KEY` | `local-openai-key` | Used for local OpenAI-compatible auth. |
| `LLAMA_SERVER_ROUTER_MODE` | `1` | Enable router mode for zero-downtime model switching (`~/.config/tenn/llama-server.env`). When set to `1`, capability inspection or missing `--models-dir` support is fatal rather than silently selecting another model; set to `0` explicitly for single-model legacy mode. |
| `LLAMA_SERVER_MODELS_DIR` | `/mnt/tenn-nvme2/tenn/models` on the 2026-06-23 checked launcher/verifier path | Directory of `.gguf` files for router mode model discovery (`~/.config/tenn/llama-server.env`). The launcher now fails instead of silently falling back to a repo-local models directory. |
| `LLAMA_SERVER_PARALLEL` | `1` | llama.cpp request slots. Keep `1` on Tesla M40 unless a benchmark validates more; match with `TENN_LLM_GPU_WORKER_CONCURRENCY`. |
| `LLAMA_SERVER_MMAP` | `1` | Set to `0` so `scripts/run_llama_server.sh` and `scripts/run_extraction_server.sh` pass `--no-mmap` when mmap-based load stalls on Tesla M40 (see `docs/ops/09_llama_server_m40_model_load_runbook.md`). |
| `LLAMA_SERVER_CACHE_TYPE_K` | _(unset)_ | Optional KV-cache override passed to `llama-server` as `--cache-type-k`. Leave unset on Tesla M40 unless you have verified the target model/runtime supports the requested cache type. |
| `LLAMA_SERVER_CACHE_TYPE_V` | _(unset)_ | Optional KV-cache override passed to `llama-server` as `--cache-type-v`. On Tesla M40, forcing quantized V cache can fail during model load when Flash Attention is unavailable. |
| `EMBEDDING_BATCH_SIZE` | `32` | Default embedding batch size. |
| `ROUTER_FEEDBACK_ENABLED` | `true` | Enables analyzer feedback in routing. |
| `ANALYZER_MAX_AGE_SECONDS` | `600` | Analyzer report freshness window. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Canonical Redis connection. |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Broker URL for Celery mode. |
| `CELERY_RESULT_BACKEND` | `redis://127.0.0.1:6379/1` | Result backend for Celery mode. |
| `TENN_LLM_GPU_WORKER_CONCURRENCY` | `1` | Compose GPU worker concurrency for the `llm_gpu` queue. Keep aligned with validated llama.cpp slots. |
| `TENN_RESEARCH_MEMORY_ROOT` | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory` when the NVMe data root exists; otherwise checkout-local fallback | Durable root for news memo JSONL outputs and skip ledgers. Nightly news uses this root for memo diagnostics and queued memo payload paths. |
| `NEWS_MEMO_MAX_ARTICLE_CHARS` | `5000` | Maximum article characters sent to each news memo extraction task. |
| `NEWS_MEMO_LLM_URL` | `LLAMACPP_URL`, then `http://127.0.0.1:8001` | OpenAI-compatible llama.cpp URL embedded into nightly/backfill memo task payloads. |
| `NEWS_MEMO_LLM_MODEL` | `LLAMACPP_MODEL`, then `model:qwen2.5-14b-instruct` | Model name embedded into nightly/backfill memo task payloads. |
| `NEWS_WAIT_FOR_MEMOS` | `0` | Nightly news waits for memo tasks only when set to `1`; default keeps ingest success independent from background enrichment. |
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

Local host override note:

- `financial-engine_v2/scripts/run_local_backend.sh` defaulted `DATA_ROOT` to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` when checked on 2026-06-23.
- `scripts/verify_nvme_runtime_endpoints.sh` expected `/mnt/tenn-nvme2/tenn/financial-engine_v2/{data,reports}` and `/mnt/tenn-nvme2/tenn/models` when checked on 2026-06-23.
- llama.cpp launcher defaults no longer force KV-cache quantization; enable `LLAMA_SERVER_CACHE_TYPE_K` / `LLAMA_SERVER_CACHE_TYPE_V` explicitly if you want non-default cache types
- the legacy root Ollama store at `/usr/share/ollama/.ollama/models` has been pruned to keep only `qwen2.5:32b` and `gpt-oss:20b-cloud`
- inactive root Ollama models are archived at `/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07`

## Copy the template

```bash
cp financial-engine_v2/.env.example financial-engine_v2/.env
```

## Override examples

Use a different data root:

```dotenv
DATA_ROOT=/srv/tenn-data
```

Historical or alternate host-local runtime-data override example:

```dotenv
DATA_ROOT=/mnt/nvme/tenn/runtime-data
DATABASE_URL=sqlite:////mnt/nvme/tenn/runtime-data/fe_local.db
DOCS_ROOT=/mnt/nvme/tenn/runtime-data/asx/docs
IMPORTANCE_OUTPUT_ROOT=/mnt/nvme/tenn/runtime-data/asx/importance
MARKETINDEX_ANNOUNCEMENTS_FILE=/mnt/nvme/tenn/runtime-data/raw/marketindex_announcements.json
```

Point the LLM endpoint to a different host:

```dotenv
LLAMACPP_URL=http://192.168.1.50:8001
```

Launcher note: `financial-engine_v2/scripts/run_local_backend.sh` loads `.env` and then `.env.local`. For secret-bearing keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LLM_API_KEY`, `EMBEDDING_API_KEY`), a blank value in `.env.local` no longer clears a non-empty value already loaded from `.env`.

Single-instance router mode (default — recommended):

```dotenv
# Single llama-server in router mode on 8001.
# All models served from NVMe; clients select per-request via "model" field.
# Chat default in checked config on 2026-06-23: Qwen3-30B-A3B-Instruct-2507-Q3_K_M
# Extraction: qwen2.5-14b-instruct (requested by model name, loaded on demand)
# Chat/extraction mutex: while extraction is active on the shared router,
# cockpit chat must route to the configured API backend instead of local llama.cpp.
LLAMACPP_URL=http://127.0.0.1:8001
EXTRACT_MODEL=qwen2.5-14b-instruct
TENN_RESEARCH_MEMORY_ROOT=/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory
NEWS_MEMO_LLM_URL=http://127.0.0.1:8001
NEWS_MEMO_LLM_MODEL=model:qwen2.5-14b-instruct
```

Legacy dual-server mode (set `EXTRACTION_LLAMACPP_URL` to enable):

```dotenv
LLAMACPP_URL=http://127.0.0.1:8001
EXTRACTION_LLAMACPP_URL=http://127.0.0.1:8002
EXTRACT_MODEL=qwen2.5-14b-instruct
```

When `EXTRACTION_LLAMACPP_URL` is not set, extraction uses `LLAMACPP_URL` (single-server router mode). In that mode, extraction activity blocks local chat on the shared router and forces cockpit chat to the configured API backend until extraction completes.

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

Host-local storage helpers:

- `scripts/migrate_runtime_to_nvme.sh` — migrate runtime data and repo GGUFs into `/mnt/nvme/tenn`
- `scripts/archive_prune_root_ollama_store.py` — archive inactive root Ollama models to HDD and prune the root store to the active keep-set
