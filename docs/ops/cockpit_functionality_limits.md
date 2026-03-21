# Cockpit Functionality Limits and Breakpoints

This note lists Cockpit flags, config settings, and environment variables that can disable features, degrade behavior, or hard-fail startup/runtime.

## Runtime flags that hard-limit behavior

| Control | Where set | Impact when enabled/mis-set | Source |
|---|---|---|---|
| `--read-only` | Cockpit launch arg | Blocks all mutating actions unless dry-run; action execution returns early with `read-only mode: mutating action blocked`. | `financial-engine_v2/cockpit/main.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `--no-web` | Cockpit launch arg | Hard-disables web usage for the session; `/web on` cannot override it. | `financial-engine_v2/cockpit/main.py`, `financial-engine_v2/cockpit/ui/app.py` |

## Cockpit env vars that can break or constrain functionality

| Variable | Effect | Risk profile | Source |
|---|---|---|---|
| `COCKPIT_BACKEND_API_URL` | Overrides backend API base URL used by Cockpit. | Wrong URL removes backend-assisted features (price calls, backend RAG readers, model status checks). | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `COCKPIT_OLLAMA_URL` / `OLLAMA_URL` | Overrides LLM endpoint for cockpit chat/model checks. | Bad endpoint causes slow/failing chat and failed model health checks. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/actions.py` |
| `COCKPIT_LLM_MODEL` | Overrides cockpit chat model. | Missing/unavailable model causes runtime failures or poor quality. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/actions.py` |
| `EXTRACT_MODEL`, `EMBED_MODEL` | Included in Cockpit doctor preflight required model checks. | Doctor reports missing model(s) and preflight fails if model not installed in Ollama. | `financial-engine_v2/cockpit/core/actions.py` |
| `DATABASE_URL` | Overrides cockpit DB target. | Wrong DB path/schema yields missing-table errors in context gathering and doctor checks. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/actions.py` |
| `COCKPIT_NEWS_TICKER_MATCH_MODE` | Overrides news ticker matching mode. | Any value other than `soft` or `strict` raises `ValueError` and can fail startup/config load. | `financial-engine_v2/cockpit/core/config.py` |
| `COCKPIT_NEWS_CORPUS_FILTER` | Overrides corpus filtering for news context. | Overly narrow or wrong corpus filter can zero out news retrieval. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/tools.py` |
| `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS` | Timeout for local context collection. | Low values trigger frequent `context_gather_timeout` fallback responses (thin/no evidence). | `financial-engine_v2/cockpit/core/chat.py` |
| `COCKPIT_CONTEXT_PROFILE` | Sets default session context profile (`balanced` or `max-depth`). | `max-depth` increases context depth and prompt size (better depth, higher latency/noise risk). | `financial-engine_v2/cockpit/ui/app.py`, `financial-engine_v2/cockpit/core/chat.py` |
| `COCKPIT_MAX_USER_MESSAGE_CHARS` | Max input message length before truncation. | Small values silently truncate user requests, reducing analysis quality and intent capture. | `financial-engine_v2/cockpit/core/chat.py` |
| `COCKPIT_FORCE_LOCAL_OPERATIONAL_BRIEF` | Forces local deterministic brief path in operational mode. | Bypasses normal LLM-based operational response path; can reduce flexibility/depth. | `financial-engine_v2/cockpit/core/chat.py` |
| `COCKPIT_NPX_PATH` | Command for candlestick CLI launcher. | Wrong binary/path breaks chart action execution. | `financial-engine_v2/cockpit/core/actions.py` |

## Cockpit config defaults that intentionally limit capability

| Config key | Default in repo | Limiting behavior | Source |
|---|---|---|---|
| `web.enabled_default` | `false` | Web enrichment starts disabled until explicitly enabled in-session. | `financial-engine_v2/config/cockpit.yaml` |
| `db.diagnostic_query_enabled` | `false` | `/sql` is blocked until `/dbdiag on` is set for session. | `financial-engine_v2/config/cockpit.yaml`, `financial-engine_v2/cockpit/ui/app.py` |
| `rag.qualitative_context.enabled` | `false` (base config) | Company qualitative context is off unless local override enables it. | `financial-engine_v2/config/cockpit.yaml` |
| `rag.news_context.enabled` | `false` (base config) | News qualitative context is off unless local override enables it. | `financial-engine_v2/config/cockpit.yaml` |
| `backend.api_key` | `""` (empty) | When set, Cockpit sends `X-API-Key: <value>` on all `BackendApiClient.rag_query()` calls. Required when `local_api_key` is configured in the backend — omitting it causes 403 on `/api/rag/query`. | `financial-engine_v2/cockpit/integrations/backend_api.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `backend.auto_start` | `true` | If set `false` and backend is down, cockpit will not attempt to self-recover by launching backend. | `financial-engine_v2/config/cockpit.yaml`, `financial-engine_v2/cockpit/ui/app.py` |
| `backend.startup_timeout_seconds` | `25` | Low values produce false negative "health check timed out" startup states for slow hosts. | `financial-engine_v2/config/cockpit.yaml`, `financial-engine_v2/cockpit/ui/app.py` |

## Current local override posture

Observed in `financial-engine_v2/config/cockpit.local.yaml`:

- `llm.timeout_seconds` lowered to `90` (faster fail, but more timeout risk on slow model runs).
- `rag.news_context.enabled` set to `true` locally (good for news retrieval).
- `rag.qualitative_context.enabled` still `false` in local override (company qual context remains off).

## Recommended safe baseline

- Keep `--read-only` off for normal operations; use action confirmation as guardrails.
- Keep `--no-web` off unless intentionally air-gapped.
- Set `COCKPIT_BACKEND_API_URL` to a verified healthy backend endpoint.
- Set `COCKPIT_OLLAMA_URL` explicitly on host runs (avoid Docker-only hostname leakage).
- Keep `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS` high enough for your DB size and IO latency.
- Ensure `COCKPIT_NEWS_TICKER_MATCH_MODE` is only `soft` or `strict`.
