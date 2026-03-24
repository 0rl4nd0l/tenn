# Environment Setup

The active runtime is `financial-engine_v2`. The canonical env file lives at `financial-engine_v2/.env`.

## Canonical env spec

| Variable | Default | Notes |
| --- | --- | --- |
| `DATA_ROOT` | `./data` | Root for runtime data, reports, and derived paths. |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant vector store endpoint. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL. |
| `LLAMACPP_URL` | `http://127.0.0.1:8001` | llama.cpp OpenAI-compatible endpoint. |
| `LLM_API_KEY` | `local-openai-key` | Used for local OpenAI-compatible auth. |
| `EMBEDDING_BATCH_SIZE` | `32` | Default embedding batch size. |
| `ROUTER_FEEDBACK_ENABLED` | `true` | Enables analyzer feedback in routing. |
| `ANALYZER_MAX_AGE_SECONDS` | `600` | Analyzer report freshness window. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Canonical Redis connection. |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Broker URL for Celery mode. |
| `CELERY_RESULT_BACKEND` | `redis://127.0.0.1:6379/1` | Result backend for Celery mode. |
| `ENABLE_SESSION_MEMORY` | `true` | Enable OpenViking session memory for `/api/chat`. Set to `false` to disable. |
| `OPENVIKING_CONFIG_FILE` | _(injected by launcher)_ | Absolute path to domain-specific `ov.conf`. Backend defaults to `~/.openviking/backend.ov.conf`; cockpit defaults to `~/.openviking/cockpit.ov.conf`. Override to point at a different workspace. |

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
