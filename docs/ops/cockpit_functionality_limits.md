# Cockpit Functionality Limits and Breakpoints

This note lists Cockpit flags, config settings, and environment variables that can disable features, degrade behavior, or hard-fail startup/runtime.

## Runtime flags that hard-limit behavior

| Control | Where set | Impact when enabled/mis-set | Source |
|---|---|---|---|
| `--read-only` | Cockpit launch arg | Blocks all mutating actions unless dry-run; action execution returns early with `read-only mode: mutating action blocked`. | `financial-engine_v2/cockpit/main.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `--no-web` | Cockpit launch arg | Hard-disables web usage for the session; `/web on` cannot override it. | `financial-engine_v2/cockpit/main.py`, `financial-engine_v2/cockpit/ui/app.py` |

## Cockpit env vars that can break or constrain functionality

`financial-engine_v2/config/cockpit_llm.yaml` is the authoritative Cockpit LLM source by default. `COCKPIT_LLM_PROVIDER`, `COCKPIT_LLM_MODEL`, `COCKPIT_LLAMACPP_URL`, `COCKPIT_OLLAMA_URL`, and related `COCKPIT_*` LLM env vars only override the merged Cockpit LLM config when `allow_env_override: true` is set in that YAML file.

| Variable | Effect | Risk profile | Source |
|---|---|---|---|
| `COCKPIT_BACKEND_API_URL` | Overrides backend API base URL used by Cockpit. | Wrong URL removes backend-assisted features (price calls, backend RAG readers, model status checks). | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `COCKPIT_OLLAMA_URL` / `OLLAMA_URL` | Overrides the Cockpit/Ollama URL only when `allow_env_override: true`; otherwise the value from `config/cockpit_llm.yaml` remains authoritative for Cockpit LLM config. | Bad endpoint causes slow/failing chat and failed model health checks when env overrides are enabled. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/actions.py` |
| `COCKPIT_LLM_MODEL` | Overrides the cockpit chat model only when `allow_env_override: true`; otherwise `config/cockpit_llm.yaml` remains authoritative. | Missing/unavailable model causes runtime failures or poor quality when env overrides are enabled. | `financial-engine_v2/cockpit/core/config.py`, `financial-engine_v2/cockpit/core/actions.py` |
| `COCKPIT_LLM_PROVIDER` | Overrides the cockpit chat provider only when `allow_env_override: true`; otherwise `config/cockpit_llm.yaml` remains authoritative. | Unsupported or mismatched provider can fail startup/config load when env overrides are enabled. | `financial-engine_v2/cockpit/core/config.py` |
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
| `backend.api_key` | `""` (empty) | When set, Cockpit sends `X-API-Key: <value>` on all `BackendApiClient.rag_query()` calls. Required when `local_api_key` is configured in the backend — omitting it causes 403 on `/rag/query`. | `financial-engine_v2/cockpit/integrations/backend_api.py`, `financial-engine_v2/cockpit/ui/app.py` |
| `backend.auto_start` | `true` | If set `false` and backend is down, cockpit will not attempt to self-recover by launching backend. | `financial-engine_v2/config/cockpit.yaml`, `financial-engine_v2/cockpit/ui/app.py` |
| `backend.startup_timeout_seconds` | `25` | Low values produce false negative "health check timed out" startup states for slow hosts. | `financial-engine_v2/config/cockpit.yaml`, `financial-engine_v2/cockpit/ui/app.py` |

## Backend-controlled access state limitations

- Slash commands `/web on|off`, `/rag on|off`, and `/dbdiag on|off` apply backend proposals through `/api/system/proposals/apply`, then sync the local session from backend access state.
- `/request-access ...` stages a backend proposal first; the state change lands only after `/confirm`.
- The Settings screen switches currently call `CockpitApp._set_access_scope()` directly and can mutate local session state without writing the backend authority file. A later backend sync can therefore overwrite what the screen shows.
- Backend capability snapshots may advertise remediation proposals that are informational only. Today the apply endpoint executes `start_extraction_runtime` plus access toggles, not the full proposal list exposed by `/api/system/capabilities`.

## Current local override posture

Observed in `financial-engine_v2/config/cockpit.local.yaml`:

- `llm.timeout_seconds` lowered to `90` (faster fail, but more timeout risk on slow model runs).
- `rag.news_context.enabled` set to `true` locally (good for news retrieval).
- `rag.qualitative_context.enabled` still `false` in local override (company qual context remains off).
- Cockpit chat provider/model still come from `financial-engine_v2/config/cockpit_llm.yaml` unless that file opts into env overrides.

## Pre-boot routing behavior

- Pre-boot recomputes and displays the effective Cockpit LLM config from `config/cockpit_llm.yaml` plus host env/defaults.
- Pre-boot no longer exports direct `COCKPIT_LLM_PROVIDER` or `COCKPIT_LLM_MODEL` selections at launch time.
- Pre-boot still exports profile/runtime flags such as `COCKPIT_PREBOOT_PROFILE`, `COCKPIT_PREBOOT_READ_ONLY`, and `COCKPIT_PREBOOT_NO_WEB`.

## Recommended safe baseline

- Keep `--read-only` off for normal operations; use action confirmation as guardrails.
- Keep `--no-web` off unless intentionally air-gapped.
- Set `COCKPIT_BACKEND_API_URL` to a verified healthy backend endpoint.
- Prefer editing `financial-engine_v2/config/cockpit_llm.yaml` for Cockpit LLM changes; only rely on `COCKPIT_*` LLM env vars when `allow_env_override: true` is intentional.
- Keep `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS` high enough for your DB size and IO latency.
- Ensure `COCKPIT_NEWS_TICKER_MATCH_MODE` is only `soft` or `strict`.
