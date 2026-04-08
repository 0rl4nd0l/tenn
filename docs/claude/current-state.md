# Current State

## Source Trace
- `docs/current_system.md` (Confirmed)
- `financial-engine_v2/README.md` (Confirmed)
- `docs/validation_baseline.md` (Confirmed)
- `docs/environment_audit.md` (Confirmed)

---

## Active Runtime

**Active engine:** `financial-engine_v2/`
**Canonical entrypoint:** `financial-engine_v2/scripts/run_local_backend.sh`
**Health endpoint:** `http://127.0.0.1:8000/api/health`

Legacy root launcher scripts are archived under `scripts/archive/legacy_root_20260218/`.

---

## Local Backend Profiles

| Profile | Behavior |
|---------|----------|
| `LOCAL_BACKEND_PROFILE=isolated` (default) | Safe smoke mode. Embeddings/Qdrant/extraction disabled. `/chat` degrades gracefully instead of 500. |
| `LOCAL_BACKEND_PROFILE=full` | Full local mode. Uses configured runtime DB/data roots, local Qdrant on `127.0.0.1:6333`, local llama.cpp on `127.0.0.1:8001/v1`. `/chat` returns grounded answers when `commentary_chunks` has data. |

Cockpit web defaults:
- Browser UI: `127.0.0.1:8081`
- llama.cpp health probe: `COCKPIT_LLAMACPP_URL` → `LLAMACPP_URL` → `http://localhost:8001` (canonical)

---

## Env Precedence (local launcher)

1. `.env` (repo template / defaults)
2. `.env.local` (local overrides; .gitignored, wins over `.env`)
3. Explicit shell env (wins over both)

Special: the launcher reads `.env` first, then `.env.local`, and explicit shell env still wins over both. On this host, the active `.env.local` override points runtime data at `/mnt/nvme/tenn/runtime-data`.

Current host-local overrides (2026-04-07):

- `financial-engine_v2/.env.local` points Tenn runtime data to `/mnt/nvme/tenn/runtime-data`
- local docs root is `/mnt/nvme/tenn/runtime-data/asx/docs`
- llama.cpp router models live at `/mnt/nvme/tenn/models`
- root Ollama keep-set is `qwen2.5:32b` plus `gpt-oss:20b-cloud`
- inactive root Ollama models are archived at `/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07`
- isolated-profile validation may still use `/tmp/financial-engine_v2-fe_local_runtime.db` for a writable runtime DB fallback

---

## Validated Baseline (2026-03-24)

The following command sequence is the current stable gate:

```bash
bash scripts/start_system.sh
bash scripts/validate_system.sh
python -m ruff check autodev financial-engine_v2/backend scripts
pytest autodev/tests
pytest financial-engine_v2/backend/tests
pytest scripts
bash scripts/run_canonical_dataset_checks.sh
python scripts/check_canonical_regression.py \
  --baseline reports/baselines/canonical_eval_baseline_latest.json \
  --news-report reports/news_eval_report.json \
  --company-report reports/company_eval_report_v2.json \
  --reference-report reports/eval_queries_report.json
python scripts/validate_financial_metrics_gates.py \
  reports/financial_metrics.json \
  --out-json reports/financial_metrics.gates.json
python scripts/validate_financial_coverage_gates.py \
  reports/financial_metrics.json \
  --out-json reports/financial_metrics.coverage_gates.json
```

**Currently passing:** ruff, pytest (backend: 200 passed, including 24-test news retrieval eval harness), canonical dataset eval, canonical regression baseline, financial metrics gates, financial coverage gates.

**Environment notes:**
- `SKIP due restricted environment` from health/smoke checks is non-fatal.
- CPU fallback is default (`REQUIRE_CUDA=0`); set `REQUIRE_CUDA=1` only when CUDA is required.

---

## System Tools Inventory (Confirmed)

- Python 3.12.3
- Poppler (PDF rendering)
- Tesseract (OCR)
- Java (Docling/tabula dependency)
- Docker (required for full Compose mode)
- Ruff (linter, pinned in `financial-engine_v2/backend/requirements.txt`)

---

## Session Memory (OpenViking) — 2026-03-24

| Component | Status | Notes |
|-----------|--------|-------|
| Backend `/api/chat` session memory | **Shipped** | `backend/app/services/session_memory.py` + `tenn_chat.py` + `routes/chat.py`. `session_id` from body or `X-Session-ID` header. Prior turns injected into LLM prompt. |
| Cockpit chat session memory | **Shipped** | `cockpit/core/session_memory.py` + `chat.py`. Per-`ChatController` UUID session. Prior turns injected before history block. |
| Domain isolation | **Shipped** | Separate workspaces: `~/.openviking/workspaces/{backend,cockpit,claude-code}`. Launchers inject domain-specific `OPENVIKING_CONFIG_FILE` when not pre-set. |
| Local-only provider config | **Shipped** | `config/openviking/*.ov.conf.example` — llama.cpp VLM (`provider=openai`, port 8001) + Ollama embeddings (`provider=ollama`, nomic-embed-text, 768-dim, port 11434). No hosted APIs. |
| Claude Code dev-session memory | **Scaffolded** | Config example + `scripts/openviking/export-claude-code-memory-env.sh`. Source before `claude`. Automated turn recording: DATA_MISSING (no PostTurnUse hook in Claude Code). |
| Feature flag | `ENABLE_SESSION_MEMORY=true` | Default on. Disable per domain: set `ENABLE_SESSION_MEMORY=false` in `.env`. |
| Fail-open | **Yes** | Missing/unreachable OV emits one WARNING on startup; all chat paths continue stateless. |

Setup: see `docs/setup/environment.md` → Session memory setup section.

---

## Current Branch Context

Branch: `cloud/session-20260319`
Last milestone commits: `19495865` (session_memory domain isolation), `aed254f0` (OpenViking Phase 1-3)

> This state snapshot reflects 2026-03-24. Re-verify with `git status` before acting.

---

## News Pipeline (2026-03-24)

Confirmed working on `cloud/session-20260319`:

| Component | Status | Evidence |
|-----------|--------|---------|
| Primary ticker in Qdrant payload | **Fixed** | `_iter_chunks()` joins `article_relevance` (is_primary DESC, relevance_score DESC); `_build_chunk_payload()` uses `primary_ticker`. Committed at `d8ab0cfd`. |
| `article_relevance` backfill | **Done** | `scripts/backfill_article_relevance.py` created; run against live DB: 353 articles → 1,665 relevance rows. |
| Ticker filter for `news_chunks` | **Fixed** | `hybrid_retriever.py` `_TICKER_FILTER_COLLECTIONS` frozenset includes `news_chunks`. `tenn_chat.py`/`ChatRequest` accept `ticker`. Committed at `d8ab0cfd`. |
| `_build_prompt()` temporal guidance | **Fixed** | Prompt includes `published_at`, conflict/contradict, staleness, sparse/overclaim, confidence 0.2 example. Committed at `d8ab0cfd`. |
| Retrieval failure logging | **Fixed** | `commentary_retrieval_failed` and `news_retrieval_failed` warnings emitted on exception. Committed at `d8ab0cfd`. |
| Evaluation harness | **Present** | `financial-engine_v2/backend/tests/test_news_retrieval_eval.py` — 24 tests, 4 failure classes (A–D). |
| RSS as default provider | **Fixed** | `fetch_daily_news.py` enables RSS by default. Committed at d95ec433. |
| Quality score filter | **Fixed** | `quality_score >= 0.3` in `_iter_chunks()` SQL; blocks paywall stubs. Committed at d95ec433. |
| Entity linker stopwords | **Fixed** | CORE, GOLD, GOOD, EDU added to `STRICT_TICKER_STOPWORDS`. Committed at d95ec433. |
| Qdrant news loader | **Re-synced** | 375 articles / 2696 chunks / 2696 upserted (2026-03-24). Re-run with `EMBED_MODEL=nomic-embed-text OLLAMA_URL=http://localhost:11434` env override (`.env.local` sets wrong 384-dim model). |

article_relevance schema (Confirmed from `scripts/news_pipeline/db.py`):
```
article_relevance(article_id, ticker, lane, relevance_score, relation_type,
                  is_primary, confidence, evidence_json)
PRIMARY KEY(article_id, ticker, lane)
```
Primary ticker selection: `ORDER BY is_primary DESC, relevance_score DESC`, first result per article_id.

Fallback when article_relevance has no rows: single-ticker articles use that ticker; multi-ticker articles use `""` (ambiguous, not filtered).

---

## MCP Servers (2026-04-03)

| Server | Status | Notes |
|--------|--------|-------|
| **qdrant** | Ready | Image built; connects to `127.0.0.1:6333` |
| **redis** | Ready | Image present; connects to `127.0.0.1:6379` |
| **tenn** | Not ready | Needs `.venv-autodev` with `openclaw` installed |
| **playwright** | Opt-in | Add to `.mcp.json`; Docker image auto-pulls |
| **github** | Opt-in | Add to `.mcp.json`; needs `GITHUB_PERSONAL_ACCESS_TOKEN` |
| **screenpipe** | Opt-in | Mac Screenpipe + tunnel; see [mcp-servers.md](mcp-servers.md) |

Default `.mcp.json` enables **qdrant**, **redis**, and **tenn** only (minimal tool-schema footprint). **github**, **playwright**, **screenpipe**, and generic `npx` demo servers are documented as optional in [mcp-servers.md](mcp-servers.md).

Config: `.mcp.json` (repo root). Full docs: [mcp-servers.md](mcp-servers.md).

---

## Operational Notes

- `/chat` now retrieves from both `commentary_chunks` and `news_chunks`. Ticker-scoped queries apply Qdrant payload filter to `news_chunks` when `ticker` param is provided.
- `commentary_chunks_v2` is optional fallback for commentary. `asx_docs` is NOT the commentary chat collection.
- Model router active weights: `latency=0.4`, `throughput=0.3`, `error=0.2`, `queue=0.1`, `gpu=0.1`.
- Current host llama.cpp default model is `qwen3-30b-a3b-instruct`; extraction requests `qwen2.5-14b-instruct` by model name. Local Ollama keep-set is `qwen2.5:32b` plus `gpt-oss:20b-cloud`.
- Live router user service is `llama-cpp-router.service`; legacy `llama-cpp-qwen25.service` should remain disabled on hosts where it still exists.
- 2026-04-08 cleanup: removed the stale `/tmp/llama-server-8001.log` orphan log and pruned disposable npm/OpenCode/Cursor caches; `/` now has roughly `53G` free.
- OpenClaw config source of truth: `~/.openclaw/openclaw.json` (host-local, not in repo).
- After committing `scripts/load_news_to_qdrant.py`, re-run the loader to refresh Qdrant with relevance-ordered primary tickers: `python scripts/load_news_to_qdrant.py`.
- Cockpit web SSE chat now emits explicit staged status events from request admission through reasoning/tool/synthesis phases (not a single placeholder string).
- Cockpit web action confirmations execute through backend route `POST /api/cockpit/action/execute` using normalized `action_id` payloads.
- Cockpit sidebar health polling is adaptive: every 3s while a chat completion is active, every 15s when idle.
- If `news_chunks` is missing in Qdrant, `search_news` may return no hits and should trigger a corpus population flow (`run_news_ingest` then `load_news_to_qdrant`).

## Storage Migration Status (2026-04-07)

- Tenn runtime data migrated successfully to `/mnt/nvme/tenn/runtime-data`
- GGUF router models migrated successfully to `/mnt/nvme/tenn/models`
- short-term IO pressure during a docs-heavy local validation workload stayed low (`/proc/pressure/io avg10` near zero to low single digits; `vmstat wa` ~1% after warm-up)
- root Ollama store pruned to keep only `qwen2.5:32b` and `gpt-oss:20b-cloud`
- archived inactive root Ollama models preserved at `/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07`
- host free space after cleanup: roughly `53G` on `/` after stale llama temp log and local cache pruning
