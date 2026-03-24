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
| `LOCAL_BACKEND_PROFILE=full` | Full local mode. SQLite in `/tmp`, local Qdrant on `127.0.0.1:6333`, local llama.cpp on `127.0.0.1:8001/v1`. `/chat` returns grounded answers when `commentary_chunks` has data. |

---

## Env Precedence (local launcher)

1. `.env` (repo template / defaults)
2. `.env.local` (local overrides; .gitignored, wins over `.env`)
3. Explicit shell env (wins over both)

Special: local launcher forces `DATA_ROOT` to repo `data/` unless `DATA_ROOT` is explicitly set in shell.

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

## Current Branch Context

Branch: `cloud/session-20260319`
Last milestone commit: `e642de16` (docs: L005-L007 primary ticker alphabetical, news ticker filter, silent retrieval swallow)

Uncommitted (working tree):
- `.claude/commands/save.md` — unrelated tooling change
- `scripts/save-chat.py` — unrelated tooling change

Untracked (not for staging): `.claude/monitors/`, `.claude/scheduled_tasks.lock`, `financial-engine_v2/everything-claude-code/`

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
| Qdrant news loader | **Last run** | 404 articles / 2725 chunks / 2725 upserted. Needs re-run after committing primary ticker fix. |

article_relevance schema (Confirmed from `scripts/news_pipeline/db.py`):
```
article_relevance(article_id, ticker, lane, relevance_score, relation_type,
                  is_primary, confidence, evidence_json)
PRIMARY KEY(article_id, ticker, lane)
```
Primary ticker selection: `ORDER BY is_primary DESC, relevance_score DESC`, first result per article_id.

Fallback when article_relevance has no rows: single-ticker articles use that ticker; multi-ticker articles use `""` (ambiguous, not filtered).

---

## MCP Servers (2026-03-20)

| Server | Status | Notes |
|--------|--------|-------|
| **qdrant** | Ready | Image built; connects to `127.0.0.1:6333` |
| **redis** | Ready | Image present; connects to `127.0.0.1:6379` |
| **playwright** | Ready | Image present; auto-pulls |
| **github** | Not ready | Needs `GITHUB_PERSONAL_ACCESS_TOKEN` exported |
| **tenn** | Not ready | Needs `.venv-autodev` with `openclaw` installed |

Config: `.mcp.json` (repo root). Full docs: [mcp-servers.md](mcp-servers.md).

---

## Operational Notes

- `/chat` now retrieves from both `commentary_chunks` and `news_chunks`. Ticker-scoped queries apply Qdrant payload filter to `news_chunks` when `ticker` param is provided.
- `commentary_chunks_v2` is optional fallback for commentary. `asx_docs` is NOT the commentary chat collection.
- Model router active weights: `latency=0.4`, `throughput=0.3`, `error=0.2`, `queue=0.1`, `gpu=0.1`.
- Checked-in local profile uses `llama3.1:8b` for generation, `nomic-embed-text` for embeddings (Inferred from `docs/architecture/01_system_overview.md`).
- OpenClaw config source of truth: `~/.openclaw/openclaw.json` (host-local, not in repo).
- After committing `scripts/load_news_to_qdrant.py`, re-run the loader to refresh Qdrant with relevance-ordered primary tickers: `python scripts/load_news_to_qdrant.py`.
