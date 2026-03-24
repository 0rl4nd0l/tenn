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
