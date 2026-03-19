# Known-Good Baseline Profiles

Use this as a practical reference for stable local runs. These profiles are intentionally conservative and aligned with current code paths.

Local preference note:
- For OpenClaw and general coding workflows, prefer the repo llama.cpp service and `llamacpp/qwen2.5-coder-14b`.
- The profiles below remain focused on `financial-engine_v2`, Cockpit, and other paths that still use Ollama today.

## 1) Host profile (backend/scripts run directly on host)

Use when running scripts like `full_history_ticker_sync.py`, `run_news_pipeline.py`, or backend from your local shell/venv.

```env
# Core DB + paths (host-writable)
DATABASE_URL=postgresql+psycopg://fe:fe@localhost:5432/fe
DOCS_ROOT=/home/<you>/tenn/financial-engine_v2/data/asx/docs
IMPORTANCE_OUTPUT_ROOT=/home/<you>/tenn/financial-engine_v2/data/asx/importance

# Model endpoints/models
OLLAMA_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text
EXTRACT_MODEL=llama3.1:8b

# Runtime controls
TASK_MODE=sync
BACKFILL_CONCURRENCY=2
EMBEDDING_BATCH_SIZE=32
ENABLE_EMBEDDINGS=true
ENABLE_QDRANT=true
ENABLE_EXTRACTION=true
ENABLE_MARKETINDEX_FALLBACK=false

# Market data
MARKET_DATA_MODE=yahoo
MARKET_DATA_BASE_URL=https://query1.finance.yahoo.com
MARKET_DATA_TIMEOUT_SECONDS=20.0
```

Why this is safe:
- Uses local host endpoints (`localhost`) instead of container hostnames.
- Keeps processing features on, but moderate concurrency to avoid overload.
- Uses direct sync mode for predictable behavior when not running worker stack.

## 2) Docker profile (compose stack)

Use with `docker compose` backend + worker + qdrant + postgres.

```env
APP_ENV=dev
POSTGRES_USER=fe
POSTGRES_PASSWORD=fe
POSTGRES_DB=fe
DATABASE_URL=postgresql+psycopg://fe:fe@postgres:5432/fe
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=asx_docs

DOCS_ROOT=/data/asx/docs
IMPORTANCE_OUTPUT_ROOT=/data/asx/importance

OLLAMA_URL=http://host.docker.internal:11434
EMBED_MODEL=nomic-embed-text
EXTRACT_MODEL=llama3.1:8b

TASK_MODE=celery
BACKFILL_CONCURRENCY=1
EMBEDDING_BATCH_SIZE=32
ENABLE_EMBEDDINGS=true
ENABLE_QDRANT=true
ENABLE_EXTRACTION=true

MARKET_DATA_MODE=yahoo
OPENBB_SIDECAR_BASE_URL=http://openbb_sidecar:8081
OPENBB_SIDECAR_TIMEOUT_SECONDS=20.0
OPENBB_SIDECAR_ENABLE_STAGING_WRITES=false
```

Why this is safe:
- Uses service DNS names (`postgres`, `qdrant`, `openbb_sidecar`) valid in compose network.
- Uses celery mode with broker/result backend configured.
- Avoids sidecar write side effects by default.

## 3) Cockpit baseline profile

Use for interactive TUI stability.

### Cockpit YAML baseline

```yaml
llm:
  provider: ollama
  ollama_url: http://localhost:11434
  model: qwen2.5-coder:14b
  timeout_seconds: 120

backend:
  api_base_url: http://localhost:8000
  auto_start: true
  start_command:
    - ./scripts/run_local_backend.sh
  startup_timeout_seconds: 40

web:
  enabled_default: false

db:
  diagnostic_query_enabled: false

rag:
  enabled: true
  qualitative_context:
    enabled: true
  news_context:
    enabled: true
    db_path: reports/qual_context/news.sqlite
    corpus_filter: news
    ticker_match_mode: soft
```

### Cockpit env overrides baseline

```env
COCKPIT_OLLAMA_URL=http://localhost:11434
COCKPIT_BACKEND_API_URL=http://localhost:8000
COCKPIT_LLM_MODEL=qwen2.5-coder:14b
COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS=90
COCKPIT_MAX_USER_MESSAGE_CHARS=8000
# Optional; only if non-standard npx path is needed:
# COCKPIT_NPX_PATH=npx
```

Run cockpit without hard-disable flags for normal operation:

```bash
python3 financial-engine_v2/scripts/cockpit_tui.py --no-boot -- --config config/cockpit.local.yaml
```

Do not use for normal runs unless intentional:
- `--read-only`
- `--no-web`

## 4) News pipeline baseline (high-yield local)

This section is for the standalone `scripts/run_news_pipeline.py` research workflow. It is separate from the backend runtime RAG path documented in `docs/architecture/06_embeddings_and_vector_store.md`.

```bash
python3 scripts/run_news_pipeline.py \
  --providers eodhd,gdelt,worldmonitor \
  --since-hours 48 \
  --row-batch-size 128 \
  --progress-every 500 \
  --embed-backend sentence-transformers \
  --verify
```

If EODHD captures are missing:
- Set `EODHD_API_KEY=...`.
- Live fallback is enabled automatically when captures are missing and the key is present.
- Optional overrides:
  - `--allow-missing-eodhd-captures` forces explicit live mode.
  - `--auto-live-when-capture-missing` remains available for compatibility.

Stale-run auto-heal defaults:
- `fetch_daily_news.py` and `backfill_news.py` auto-mark stale `provider_runs` stuck in `running` as `failed` (default threshold: 2 hours).
- Override with `--sweep-stale-runs-hours N` or disable with `--no-sweep-stale-runs`.

## 5) Fast sanity checklist

- Backend health responds at `http://localhost:8000/api/health`.
- Ollama health/models reachable at configured URL.
- Qdrant reachable at configured URL and collection valid.
- `DATABASE_URL` points to intended DB (host vs container context).
- `DOCS_ROOT` and `IMPORTANCE_OUTPUT_ROOT` are writable for current runtime.
- Quarantine files (`ticker_quarantine.json`, `document_quarantine_rules.json`) reviewed before assuming missing data is a bug.
