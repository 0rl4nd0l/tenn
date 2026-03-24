# docs/claude/lessons.md — Regression Lessons

Lessons learned from bugs found and fixed in this codebase.
Each entry captures: the symptom, root cause, fix, and the rule that prevents recurrence.

---

## L001 — Margin formula: _pct_change is not _ratio

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/analysis/financial_metrics.py`
**Symptom:** NAB FY2024 `ebit_margin` stored as −0.628 instead of +0.372. Profitable companies appeared loss-making in the analysis layer and health scores.
**Root cause:** `_pct_change(ebit, revenue)` was used to compute margins. `_pct_change` computes `(new − old) / old` — a year-over-year percentage change formula. Applied to (ebit, revenue) it produces `(ebit − revenue) / revenue`, not `ebit / revenue`.
**Fix:** Added `_ratio(numerator, denominator)` helper that returns `numerator / denominator`. Replaced all three margin callers: `ebit_margin`, `np_margin`, `fcf_margin`.
**Rule:** Any calculation labeled `*_margin` must use `_ratio`, not `_pct_change`. `_pct_change` is for temporal deltas only (old → new). Regression guard: `test_nab_ebit_margin_is_positive` and `test_nab_ebit_margin_value`.

---

## L002 — Missing temperature=0 on Anthropic SDK extraction path

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** Extractions using the Anthropic SDK path were non-deterministic — identical PDFs could produce slightly different structured JSON outputs across runs, making regression testing unreliable.
**Root cause:** `messages.create()` was called without `temperature=0`. The Anthropic API defaults to a non-zero temperature, allowing sampling variance.
**Fix:** Added `temperature=0` to the `messages.create()` call.
**Rule:** All LLM calls in the extraction pipeline must specify `temperature=0` explicitly. Do not rely on API defaults. Applies to both the Ollama/llama.cpp path (`options={"temperature": 0}`) and the Anthropic SDK path (`temperature=0`).

---

## L003 — Hardcoded prompt_hash="v1" breaks audit trail

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/pipeline.py`, `worker/app/tasks.py`
**Symptom:** All `ExtractionRun` rows had `prompt_hash="v1"` regardless of which prompt templates were actually used. This made it impossible to detect when prompt changes caused extraction drift, and invalidated the deduplication skip logic (same version + same hash → skip re-extraction).
**Root cause:** `prompt_hash="v1"` was hardcoded as a literal string in two separate call sites. No mechanism existed to auto-update it when prompts changed.
**Fix:** Computed `PROMPT_HASH = sha256(pass1 + pass3a + pass3b)[:16]` at module import time in `multipass_extraction.py`. Both `pipeline.py` and `tasks.py` now import and use this constant.
**Rule:** `prompt_hash` must always come from `PROMPT_HASH` imported from `multipass_extraction`. Never hardcode a literal string. Regression guard: `test_pipeline_does_not_use_hardcoded_v1` and `test_pipeline_imports_prompt_hash`.

---

---

## L004 — News chunks stored without text field, silently returning empty context

**Date:** 2026-03-24
**Subsystem:** `scripts/load_news_to_qdrant.py`, `backend/app/services/tenn_chat.py`
**Symptom:** `/chat` would "find" news chunks via Qdrant retrieval but the LLM context rows had empty `text` fields. Answers would appear to use sources but were actually context-less.
**Root cause:** `_build_chunk_payload()` stored only metadata (title, url, provider, etc.) but not the actual chunk text. `HybridRetriever._normalize_chunk_payload()` reads `text` from the payload — if absent, returns empty string.
**Fix:** Added `"text": chunk_text` and `"source_type": "news_article"` to `_build_chunk_payload()` and re-ran the loader to update all 2,725 Qdrant points.
**Rule:** When ingesting text into Qdrant for retrieval, the chunk text MUST be stored in the Qdrant point payload alongside the vector. The vector is for similarity search; the payload text is for returning to the caller. Verify by checking `_normalize_chunk_payload()` in `hybrid_retriever.py` against the payload schema of each collection.

---

## L005 — Primary ticker was alphabetical-first, not relevance-ordered

**Date:** 2026-03-24
**Subsystem:** `scripts/load_news_to_qdrant.py`
**Symptom:** For multi-ticker articles (e.g. a BHP/RIO article), the Qdrant `ticker` payload field reflected whichever ticker came first alphabetically (e.g. BHP before RIO), not the ticker that entity linking scored as most relevant.
**Root cause:** `_iter_chunks()` called `sorted(set(linked_tickers))` for dedup, then `_build_chunk_payload` took `tickers[0]` — the alphabetical first. The `article_relevance` table (which stores `is_primary`, `relevance_score`) was never read.
**Fix:** Added a join to `article_relevance` in `_iter_chunks()` ordered by `is_primary DESC, relevance_score DESC`. The `primary_ticker` field is populated per article. `_build_chunk_payload` uses `primary_ticker` if set; falls back to single-ticker shortcut; otherwise empty string (ambiguous).
**Rule:** Primary ticker selection for Qdrant must always derive from `article_relevance.is_primary` or `relevance_score`. Never use `sorted()[0]` on a set of tickers — alphabetical order is meaningless for relevance. The fallback for ambiguous multi-ticker articles is an empty string, not an arbitrary selection.

---

## L006 — Ticker filter for news_chunks collection was never applied

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/hybrid_retriever.py`, `backend/app/services/tenn_chat.py`
**Symptom:** `/chat` queries with a known ticker (e.g. "What did BHP announce?") retrieved news articles for all companies, not just BHP. Ticker-aware filtering worked for ASX documents but was silently skipped for news.
**Root cause:** `_build_ticker_filter()` only activated when `collection_name == "asx_docs"`. The `news_chunks` collection was not in the allowed set. Additionally, `chat_with_tenn()` did not accept or propagate a `ticker` parameter.
**Fix:** Added `NEWS_CHUNKS_COLLECTION_NAME` and `_TICKER_FILTER_COLLECTIONS` frozenset. Extended `_build_ticker_filter` to check the frozenset instead of a single string. Added `ticker: str | None = None` to `chat_with_tenn()` and `ChatRequest`, wired through the route.
**Rule:** When adding a new Qdrant collection that stores ticker-scoped content, add it to `_TICKER_FILTER_COLLECTIONS` explicitly. Never assume a collection inherits filtering behavior from an existing collection. Verify with a `TestNewsTickerFilter` style test.

---

## L007 — Retrieval exceptions were silently swallowed in tenn_chat

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/tenn_chat.py`
**Symptom:** When Qdrant was unreachable or returned an error during news or commentary retrieval, the system degraded to `news_chunks = []` with no log output. Debugging retrieval failures required guessing whether the issue was the query, the collection, or connectivity.
**Root cause:** Both retrieval `except Exception` blocks had no logging — bare `except Exception: chunks = []`.
**Fix:** Added `logger.warning("news_retrieval_failed", extra={...})` and `logger.warning("commentary_retrieval_failed", extra={...})` with `component`, `collection`, `operation`, `error`, and `detail` fields.
**Rule:** Any `except` block that catches a broad `Exception` and continues silently MUST emit at least a WARNING log with enough structured context to identify the component and failure mode. Silent degradation is acceptable for user-facing response; silent degradation in logs is not.

---

## L008 — period_start schema column added but never populated by extraction pipeline

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`, `backend/app/models/asx_financials.py`
**Symptom:** Migration 0004 added `asx_periodic_financials.period_start` (nullable Date) to allow unambiguous reconstruction of the reporting window. All records had NULL `period_start` despite the column existing. The pipeline read `structured.get("period_start")` from the extraction payload but the payload never contained that key.
**Root cause:** The schema extension and the pipeline storage call were added in the same commit, but the extraction function (`run_multipass_extraction`) was not updated to compute and include `period_start` in the returned payload. The `pipeline.py` call `parse_period_end(structured.get("period_start"))` silently returned None when the key was missing.
**Fix:** Added `_derive_period_start(period_end, period_type) -> date | None` to `multipass_extraction.py`. Called after Pass 4 reconciliation; sets `payload["period_start"]` deterministically (period_end − {12,6,3} months + 1 day for A/H/Q). Added 5 regression tests covering all period types, edge cases, and None inputs.
**Rule:** When adding a nullable schema column that is meant to be populated at extraction time, immediately update the extraction payload to include that key. Do not rely on the pipeline storage call gracefully handling a missing key — it will store NULL silently. Verify with a direct unit test on `_derive_period_start` and an integration assertion that the payload key is present after `run_multipass_extraction`.

---

## L009 — Two-step DB commit creates orphaned ExtractionRun rows

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/pipeline.py`
**Symptom:** If `_upsert_financial_rows` raised after `ExtractionRun` was committed, the DB would contain an `ExtractionRun` with `status="ok"` but zero associated `ASXPeriodicFinancial` rows. Queries that join on the run would silently return empty metric sets despite the run showing success.
**Root cause:** `process_document` committed `ExtractionRun` first (`db.commit()` at line 1025), then called `_upsert_financial_rows` which committed a second time (line 847). Any exception between the two commits left the run in a falsely-succeeded state with no metrics.
**Fix:** Removed `db.commit()` from `_upsert_financial_rows`. In `process_document`, moved `_upsert_financial_rows` call before the single `db.commit()`, so both the run and the financial rows commit atomically. SQLAlchemy auto-rolls back on `db.close()` if the commit is never reached.
**Rule:** Functions that write to the DB must never call `db.commit()` internally — commit ownership belongs exclusively to the outermost orchestrator (e.g., `process_document`). Tests for such functions must call `session.flush()` (not rely on commit) to verify pending state within the same session. Regression guard: `test_upsert_financial_rows_smoke`.

---

## L010 — scale and currency never propagated from Pass 1 into validation payload

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** `_validate_gate` received a payload dict that never contained `scale` or `currency`. The `scale="unknown"` hard block and non-AUD currency downgrade silently never fired. Additionally, `_upsert_financial_rows` stored `NULL` for `currency` on every row regardless of what the document reported.
**Root cause:** `_run_pass4_reconciler` only returns period/metrics/narrative fields from `pass1_result`; `scale` and `currency` are not forwarded. `run_multipass_extraction` built the payload from the reconciler output without explicitly adding these Pass 1 fields before calling `_validate_gate`.
**Fix:** Added `payload["scale"] = pass1.get("scale", "unknown") or "unknown"` and `payload["currency"] = pass1.get("currency", "AUD") or "AUD"` in `run_multipass_extraction` immediately before the `_validate_gate` call.
**Rule:** Any gate or storage function that inspects `scale` or `currency` must receive them explicitly in the payload. Do not assume Pass 1 fields are present in the reconciler output — `_run_pass4_reconciler` is intentionally narrow. When adding a new gate check, verify `payload.get(field)` will not silently return `None` in production.

---

## L011 — scale='unknown' stored silently as 1× multiplier, producing wrong monetary values

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** When the LLM could not determine the reporting scale (e.g., thousands vs. millions), `SCALE_MULTIPLIERS["unknown"] = 1` silently applied a 1× multiplier. A value of 100 (thousands) would be stored as 100 instead of 100,000 — a 1,000× error with no warning.
**Root cause:** `SCALE_MULTIPLIERS` treated `"unknown"` as a safe fallback (1×) rather than an error condition. `_validate_gate` had no check for it.
**Fix:** Added `if payload.get("scale") == "unknown": return "failed", "validation_gate:scale_unknown"` in `_validate_gate`. Requires L010 fix (scale propagated into payload) to take effect.
**Rule:** `scale="unknown"` is a hard validation failure. A document with unknown scale must not have its metrics stored — the values are meaningless. Regression guard: `test_validate_gate_scale_unknown_hard_blocked`.

---

## L012 — Non-AUD currency stored without FX conversion, treated as AUD-comparable by callers

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** USD-denominated documents (e.g., BHP) had their metrics extracted, scaled, and stored as-is alongside AUD metrics. No flag in the extraction result signalled that these values cannot be directly compared with AUD peers. Downstream health scores would compare USD and AUD figures on the same scale.
**Root cause:** No FX conversion policy exists in the architecture (confirmed: `docs/architecture/14_roadmap_and_modules.md` has no FX section). The extraction pipeline stored `currency` from the DB model but `_validate_gate` had no currency-aware downgrade.
**Fix:** Added non-AUD check in `_validate_gate`: if `currency != "AUD"`, emit a warning log and return `("ok_low_confidence", None)`. Requires L010 fix (currency in payload). The `ok_low_confidence` status ensures callers know values require interpretation.
**Rule:** Until an FX conversion policy is defined and implemented, any extraction result with `currency != "AUD"` must be treated as `ok_low_confidence`, not `ok`. Do not promote non-AUD results to `ok` status without an explicit conversion step. Regression guard: `test_validate_gate_non_aud_returns_ok_low_confidence`.

---

## L014 — Cockpit web hardcoded llama.cpp port drift caused false connection-refused errors

**Date:** 2026-03-24
**Subsystem:** `financial-engine_v2/cockpit`
**Symptom:** Cockpit pre-boot reported llama.cpp as down with connection-refused errors even when the runtime was healthy on the configured port. Separately, Cockpit web defaulted to `8080`, colliding with the documented direct llama.cpp port.
**Root cause:** Pre-boot health probes and provider labels hardcoded `localhost:8001` instead of using the effective `COCKPIT_LLAMACPP_URL` / `LLAMACPP_URL`. The `scripts/cockpit` web launcher reused `8080` for the browser UI.
**Fix:** Derived pre-boot llama.cpp health probes from the effective runtime URL, updated the provider label to reflect the resolved host/port, and moved Cockpit web's default port to `8081`.
**Rule:** UI health checks must consume the same endpoint config path as the runtime client. Never assign a browser UI default to a reserved service port.

---

## L015 — Canonical LLM port is 8001; do not reintroduce 8080

**Date:** 2026-03-24
**Subsystem:** `financial-engine_v2/cockpit`, `scripts/`
**Symptom:** Cockpit pre-boot screen showed `[!!] llama.cpp <urlopen error [Errno 111] Connection refused>` on every cold start, even when all other services were healthy.
**Root cause:** `DEFAULT_LLAMACPP_URL` in `cockpit/core/config.py`, three default params in `cockpit/ui/preboot.py`, and the `scripts/cockpit` shell fallback all hardcoded `localhost:8080`. The canonical LLM port — established in `backend/app/core/config.py` and the financial engine docs — is `8001`. Nothing runs on 8080 by default.
**Fix:** Changed all five hardcoded `8080` → `8001` across `cockpit/core/config.py`, `cockpit/ui/preboot.py`, and `scripts/cockpit`. Updated `scripts/run_llama_server.sh` default PORT to match. Removed 8080 from all port tables and docs across the repo.
**Rule:** **8001 is the one canonical LLM endpoint port.** `backend/app/core/config.py:236` is the single source of truth (`llamacpp_url: str = "http://127.0.0.1:8001"`). Any new cockpit, script, or doc that references a llama.cpp URL must use 8001 or read from `LLAMACPP_URL`/`COCKPIT_LLAMACPP_URL`. Never introduce 8080 as a default — it is not reserved and collides with nothing, but it is wrong.

---

## L013 — Page number lost between Pass 2 table selection and Pass 4 provenance

**Date:** 2026-03-24
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** Provenance strings stored in `asx_periodic_financials.provenance` had the form `"{source}:{row_ref}"` (e.g., `"cashflow_statement:Net cash from operations"`). There was no way to locate the source table in the original PDF for manual verification or audit.
**Root cause:** `DoclingTable.page_number` was available at the end of Pass 2 (used in table scoring at line 266) but was never captured into the Pass 3a output dict. Pass 4 built provenance from `_source` and `row_refs` only.
**Fix:** Added `"_page_number": getattr(table, "page_number", None)` to Pass 3a's `out` dict. In Pass 4, extracted `page_tag = f"page_{page}"` from `_page_number` and built provenance as `f"{source}:{page_tag}:{row_ref}"`.
**Rule:** Any metadata available on `DoclingTable` at table-selection time must be threaded through to provenance if it aids traceability. Use `_`-prefixed keys (e.g., `_page_number`, `_source`) in inter-pass dicts to distinguish metadata from extracted metrics. Regression guard: `test_pass3a_page_number_in_output`, `test_pass4_provenance_includes_page_number`.
