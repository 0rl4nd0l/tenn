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

---

## L016 — Model switching in cockpit stalled silently because llama-server crashes were undetected

**Date:** 2026-03-25
**Subsystem:** `cockpit/integrations/llamacpp_manager.py`, `cockpit/ui/preboot.py`
**Symptom:** Selecting a different model in the cockpit pre-boot screen caused the UI to freeze for up to 10 minutes with no feedback, then either launch with a dead backend or time out.
**Root cause:** Two bugs: (1) `subprocess.Popen` launched the new llama-server with `stderr=DEVNULL` — if the server crashed on startup (OOM, bad args, missing file), there was no error output to report. (2) The polling loop never called `proc.poll()` to check if the process was still alive — it blindly sent HTTP requests to a dead port for 600 seconds.
**Fix:** (1) Changed `stderr=DEVNULL` to `stderr=PIPE` and read the last line on crash for diagnostics. (2) Added `proc.poll()` check each polling iteration — if the process died, report the exit code and stderr immediately instead of waiting for timeout.
**Follow-up:** Discovered that llama.cpp build 8233 supports **router mode** (`--models-dir` + `--models-max 1`) which eliminates the kill/restart cycle entirely. Implemented router mode as the default — model switching now uses `POST /models/load` API with zero server downtime. Warm-cache switches complete in 1-3 seconds.
**Rule:** Never launch a subprocess with both stdout and stderr suppressed (`DEVNULL`) when you need to detect failures. Always store the `Popen` handle and check `.poll()` in any polling loop — a dead process should be detected within one poll interval, not at timeout. For long-running services, prefer API-based control (load/unload) over process lifecycle management (kill/restart) when the runtime supports it.

## L017 — Textual Select widget: use Select.BLANK not "" for blank-allowed initial value

**Date:** 2026-03-25
**Subsystem:** `cockpit/ui/preboot.py`
**Symptom:** `textual serve` reported "Application failed to start" for CockpitWebApp. No traceback visible at serve level. Running the app directly in a terminal worked fine.
**Root cause:** The Orchestrator and Sub-agent `Select` widgets in `PreBootScreen` were initialised with `value=""`. Textual's `Select._validate_value()` raises `InvalidSelectValueError` for any value not in the options list, including empty string — even when `allow_blank=True`. The blank-selection sentinel is `Select.BLANK` (a special object), not `""`.
**Fix:** Replace `value=""` with `value=Select.BLANK` for any `Select` with `allow_blank=True`.
**Secondary finding:** `textual_dev` CLI (cli.py:285) hardcodes `python` in the shell command it passes to `textual_serve`. On systems where only `python3` is in PATH this causes `/bin/sh: python: not found` at WebSocket connect time, which is also reported as "Application failed to start". Workaround: use `textual serve --command ".venv/bin/python script.py"` to provide the full interpreter path.
**Rule:** When using Textual `Select` with `allow_blank=True`, always pass `value=Select.BLANK` (not `""` or `None`) as the initial value when no option should be pre-selected. When using `textual serve` on systems without a bare `python` in PATH, always use the `--command` flag with the full venv interpreter path.

---

## L018 — Never accept a regressed eval baseline without architectural justification

**Date:** 2026-03-26
**Subsystem:** `backend/tests/test_extraction_eval.py`, eval infrastructure
**Symptom:** Commit `322f0d66` locked the extraction baseline at 88.42% — a 10-point drop from the 98.3% baseline at `483ce6d2`. The lowered score was partially explained by fixture set expansion (6→9), but no analysis confirmed whether the original 6 fixtures also regressed. Subsequent commits optimised against the 88.42% floor, potentially accepting structural regressions in the original fixture set as normal.
**Root cause:** No policy required justification for moving the eval floor downward. The commit message documented the score but not the decision rationale or which regressions were considered acceptable.
**Fix:** Policy rule (this lesson).
**Rule:** Never commit a milestone that accepts a regressed eval score as a new baseline without explicit architectural justification. If the eval floor must move, the commit message must document: (1) why the regression is acceptable, (2) which specific fixtures/metrics regressed and why, (3) whether the original fixture set also regressed or only new fixtures lowered the average. Update `docs/claude/STATE.md` with the new floor and rationale. Do not silently lower the threshold.

---

## L019 — Eval baseline protection must cover all files that affect extraction output

**Date:** 2026-03-27
**Subsystem:** `backend/app/services/docling_extract.py`, eval infrastructure
**Symptom:** Commit `877a8203` changed `EXTRACTION_BACKEND` default from `"pymupdf"` to `"docling"` in `docling_extract.py` (line 231). This changed which PDF parser runs for every document, but did not trigger the eval baseline protection rule because the rule only monitored `multipass_extraction.py`. The eval was not re-run before merging, and the overall score dropped from 88.42% to 77.89% (AZJ fixture at 0.0% due to garbled CID fonts).
**Root cause:** The eval baseline protection file list was too narrow — it covered `multipass_extraction.py` but not `docling_extract.py`, even though changes to the PDF extraction backend directly affect what data reaches the LLM extraction passes.
**Fix:** Policy rule (this lesson). The protected file list must include `docling_extract.py`, `extraction.py`, and any file that controls which PDF parser runs or how text/tables reach the extraction pipeline.
**Rule:** Any change to extraction backend defaults, PDF parsing libraries, or `docling_extract.py` requires running the eval baseline before committing — not just changes to `multipass_extraction.py`. The protected file list in the eval baseline protection rule must include all files that affect what data reaches the LLM extraction passes.

---

## L020 — Cockpit→LLM calls violate service role invariant regardless of "separate context" intent

**Date:** 2026-03-27
**Subsystem:** `cockpit/core/research/deep_research.py`, `cockpit/core/tool_executor.py`
**Symptom:** `DeepResearchRunner` called `HybridRouter.complete()` directly from the cockpit layer to run synthesis with a "separate LLM context." This bypassed the backend HTTP API, violating the service role invariant (SYSTEM_CONTRACT §3).
**Root cause:** The meta-tool pattern was implemented by passing `HybridRouter` into the cockpit and calling it directly. The intent (separate context window) was valid, but the execution path (cockpit→LLM without going through the backend API) was not.
**Fix:** Commit `c8b47f61` moved synthesis to `POST /research/synthesize` on the backend. `DeepResearchRunner` now calls `BackendAPIClient.synthesize_research()` instead of `HybridRouter.complete()` directly.
**Rule:** Parallel LLM call paths inside the cockpit layer — including "separate context" runners calling HybridRouter directly — violate the service role invariant regardless of intent. All cockpit LLM calls must route through the backend HTTP API.

---

## L021 — Vendor routing with fallback prevents hard dependencies on external APIs

**Date:** 2026-03-27
**Subsystem:** `cockpit/integrations/brave_search.py`, `cockpit/core/research/situation_memory.py`
**Symptom:** External API dependencies (Brave Search, rank-bm25) would break the cockpit if unavailable.
**Root cause:** N/A — designed correctly from the start.
**Fix:** Every external dependency has a fallback: `BraveSearchClient` falls back to `WebFetcher` (DuckDuckGo) when `BRAVE_SEARCH_API_KEY` is absent. `SituationMemory` falls back to simple keyword matching when `rank-bm25` is not installed. The cockpit works at full functionality when all dependencies are present, and at reduced functionality when they're absent — never crashes.
**Pattern source:** TradingAgents `route_to_vendor()` — tries primary vendor, falls back on rate limit or error.
**Rule:** Any new external integration (API client, ML library) must have a fallback that preserves core functionality. The fallback should be logged at INFO level on init so operators know which path is active. Never make the cockpit crash because an optional API key is missing.

---

## L022 — Rogue llama-server instances accumulate on GPU, causing VRAM contention and eval timeouts

**Date:** 2026-03-27
**Subsystem:** `scripts/`, `llamacpp_manager.py`, `SYSTEM_CONTRACT.md`
**Symptom:** Extraction eval takes 15-22 min due to GPU contention; Bash tool 10-min cap kills it every run. Root cause: no invariant prevents ad-hoc llama-server processes from being spawned on arbitrary ports. Rogue instances linger after debug/autodev sessions, sharing VRAM with canonical servers.
**Root cause:** No enforcement mechanism checks for existing healthy instances before spawning new ones. Debug sessions and agent runs spawn llama-server on ad-hoc ports (e.g., :38255) without cleanup hooks. Three instances on a 24GB M40 leaves ~3GB free, degrading inference 3-5×.
**Fix:** Policy rule (this lesson). Systemic fix planned in `[SESSION: gpu-process-management-rails]`.
**Rule:** Only ports 8001 (chat/router) and 8002 (extraction) are authorised llama-server instances. Any process on a third port must be treated as rogue. Before starting any llama-server process, check if the target port is already healthy — if yes, reuse it. Never spawn without a VRAM budget check. Regression guard: `gpu_process_guard.sh` (planned).

---

## L023 — Never commit wiring without the wired subsystem

**Date:** 2026-03-27
**Subsystem:** `cockpit/core/chat.py`, `cockpit/core/tool_executor.py`, `cockpit/core/tool_definitions.py`
**Symptom:** Research system wiring (imports, constructor params, tool schemas) was committed into chat.py/tool_executor.py/tool_definitions.py while the actual implementation files (`cockpit/core/research/`, `cockpit/integrations/brave_search.py`, `cockpit/integrations/hn_search.py`) remained uncommitted and untested. This created a state where the committed code imported modules that didn't exist in the repo, making the commit non-functional in isolation.
**Root cause:** Wiring code was treated as part of the "integration" step and committed alongside other changes, without verifying that the subsystem it depended on was also committed and passing its own tests.
**Fix:** Policy rule (this lesson).
**Rule:** Never commit wiring/integration code for a subsystem while the subsystem's implementation files remain uncommitted and untested. Either commit the full subsystem atomically (implementation + wiring + tests), or keep wiring out of the commit until implementation passes its own test suite. A commit must be self-consistent — every import it adds must resolve within the committed tree.

---

## L024 — Calibrate per-fixture eval tolerances to actual extraction variance

**Date:** 2026-03-27
**Subsystem:** `backend/tests/eval_fixtures/`, eval infrastructure
**Symptom:** CSL revenue tolerance was set to 0.5% but actual extraction variance for split-row tables is ~2.3%. This caused phantom gate failures on the revenue >= 90% per-metric threshold — the LLM was extracting a reasonable value but the tolerance rejected it.
**Root cause:** Fixture tolerances were copy-pasted from other fixtures without verifying against the specific document's extraction characteristics.
**Fix:** Widened CSL revenue tolerance from 0.5% to 3% (commit 89997fe3).
**Rule:** When adding new fixtures to the eval harness, verify that per-metric tolerances in the fixture JSON are calibrated to the actual extraction variance for that document — not copy-pasted from other fixtures. Run the extraction at least twice to confirm the tolerance accommodates LLM variance. A fixture tolerance tighter than real extraction variance creates phantom gate failures that mask whether the regression is in code or in the fixture definition.

---

## L025 — Banking EBIT: "Profit before credit impairment and income tax" is not EBIT

**Date:** 2026-03-27
**Subsystem:** `backend/app/services/multipass_extraction.py`, Pass 3a EBIT prompt
**Symptom:** ANZ EBIT extracted as 5,365M ("Profit before credit impairment and income tax") instead of 5,222M ("Profit before income tax"). The LLM consistently picked the pre-impairment line because the prompt listed "Operating profit" and "Profit from operations" as EBIT labels, and the pre-impairment line is semantically closer to "operating profit".
**Root cause:** The EBIT prompt did not explicitly exclude "Profit before credit impairment and income tax" or include "Profit before income tax" as valid EBIT labels. For banks, credit impairment is an operating cost, so EBIT must be after credit impairments.
**Fix:** Updated Pass 3a prompt to: (1) add "Profit before income tax" and "Cash profit before tax" to the accepted EBIT labels, (2) add a CRITICAL instruction that if both lines exist, use the post-impairment line, (3) explicitly state "Profit before credit impairment and income tax" is NOT ebit.
**Rule:** When adding extraction support for a new sector (banking, insurance, etc.), audit every metric's prompt guidance against the actual row labels in that sector's financial statements. Sector-specific row labels that look similar to standard labels but carry different semantics must be explicitly addressed in the prompt — the LLM will default to the closest semantic match without explicit guidance.

---

## L027 — Cockpit never loaded .env; all API keys silently missing

**Date:** 2026-03-28
**Subsystem:** `cockpit/main.py`, cockpit startup path
**Symptom:** Cockpit chat routing always fell back to local llama.cpp despite `ANTHROPIC_API_KEY` being set in `.env`. Brave Search returned auth errors. LLM calls to `172.18.0.1:8001` (Docker bridge) failed with 401 because `LLM_API_KEY` was not in the environment. Extraction actions failed with "Connection refused" because `LLAMACPP_URL` defaulted to `localhost:8001` instead of the configured Docker bridge IP.
**Root cause:** The cockpit entrypoint (`cockpit/main.py`) had no `load_dotenv()` or `.env` parsing. The `.env` file at `financial-engine_v2/.env` was only loaded by the backend (pydantic-settings) and Docker Compose. The cockpit process inherited only shell-exported env vars, which typically included none of the keys in `.env`.
**Fix:** Added `_load_env()` to `cockpit/main.py` — loads `financial-engine_v2/.env` at startup using `python-dotenv` if available, with a stdlib fallback parser. Shell env vars take precedence (override=False).
**Rule:** Any new entrypoint (CLI script, TUI, worker) that reads env vars must explicitly load `.env` at startup. Do not assume the parent shell has sourced it. Add a `load_dotenv()` or equivalent as the first action in `main()`.

---

## L028 — Chat routing metadata silently discarded; no per-response backend visibility

**Date:** 2026-03-28
**Subsystem:** `cockpit/core/agent_loop.py`, `cockpit/core/chat.py`, `cockpit/ui/app.py`
**Symptom:** The user had no way to tell whether Claude API or local llama.cpp answered a cockpit chat message. The HybridRouter tracked source, model, latency, and cost, but `AgentLoop._call_llm()` returned only the text string — all routing metadata was discarded.
**Root cause:** `HybridRouter.chat()` collapses `RouterResponse` to a plain `str` for interface compatibility with `AgentLoop`. The rich response data existed in `HybridRouter.cost_log()` but no code read it after agent loop completion.
**Fix:** Added `routing_metadata` field to `AgentResult` and `ChatResponse`. After `AgentLoop.run()` completes, `ChatController` reads the last `cost_log()` entry from the stored `_hybrid_router` reference and attaches it. The UI displays a routing footer and includes the metadata in export payloads.
**Rule:** When adding a new metadata source to the LLM call path, ensure it propagates all the way to the UI layer. Use post-hoc log reading (like `cost_log()`) rather than refactoring return types when the metadata producer is already accumulating the data.

---

## L026 — Shared httpx.Client across threads wedges llama-server sockets; gpu guard must parse VRAM as digits

**Date:** 2026-03-28
**Subsystem:** `cockpit/integrations/llamacpp_client.py`, `cockpit/integrations/ollama_client.py`, `scripts/gpu_process_guard.sh`
**Symptom:** `llama-server` accepted TCP on `:8001` but HTTP hung (0-byte responses); dozens of server-side `CLOSE_WAIT` sockets. Separately, `gpu_process_guard.sh` exited with `line 67: NVIDIA: unbound variable` under `set -u`.
**Root cause:** (1) `httpx.Client` is not thread-safe. Cockpit called `LlamaCppClient.health()` from `asyncio.to_thread` every ~15s while `chat()` ran on the Textual thread — concurrent use of one client corrupts the connection pool and can leave the peer in bad TCP states. (2) `_gpu_memory_used_mb` fed arithmetic with non-numeric `nvidia-smi` output, triggering unbound-variable errors in bash arithmetic under `set -u`.
**Fix:** One `httpx.Client` per OS thread via `threading.local()` in `LlamaCppClient` and `OllamaClient`; explicit `httpx.Timeout` and `httpx.Limits(max_connections=6, max_keepalive_connections=3)`. Strip `memory.used` to digits only before `VRAM_TOTAL_MB - used` in `gpu_process_guard.sh`.
**Rule:** Do not share a single `httpx.Client` instance across threads (including `asyncio.to_thread` workers). Use thread-local clients, or a lock around all client use (avoid holding the lock across long streaming reads). When parsing `nvidia-smi` CSV in bash with `set -u`, normalize to digits before arithmetic.

---

## L029 — Ticker fast-path false positives: stopwords incomplete and _FOLLOW_UP_RE too broad

**Date:** 2026-03-29
**Subsystem:** `cockpit/core/chat.py`
**Symptom:** Conversational messages like "sure", "okay", "why did ingestion fail", "hi how are you" triggered ticker lookups (SURE, OKAY, WHY, ARE), returning "No data found" errors. The user saw every free-text message misrouted as a stock query.
**Root cause:** Two independent issues: (1) `TICKER_STOPWORDS` was missing common English words (WHY, ARE, FAIL, RIGHT, WAS, HAS, GOT, GET, etc.) so `_detect_ticker` treated them as valid ASX tickers. (2) `_FOLLOW_UP_RE` matched discourse markers ("sure", "okay", "yes", "go ahead", "also", "continue", "right") in addition to financial terms, causing prior-ticker reattachment for any message containing conversational fillers.
**Fix:** Expanded `TICKER_STOPWORDS` with ~20 missing common English words. Rewrote `_FOLLOW_UP_RE` to match only topic-referential phrases (financial terms like "financials", "earnings", "revenue"; entity pronouns like "their", "its"; explicit continuation like "tell me more") — removed all discourse markers. Added 9 regression tests covering stopwords, follow-up matching, compound messages, and cued tickers.
**Rule:** When adding a fast-path that fires before intent classification, the deny-list must be exhaustive for false positives. Conversational fillers (discourse markers) are never entity-referential — do not treat them as follow-up signals for ticker context.

---

## L030 — Extraction prompts must include sector-specific guidance for non-industrial companies

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/multipass_extraction.py`, Pass 3a prompt
**Symptom:** ANZ extraction accuracy at 81.82% (target 88%+). EBIT failing (72.73%) because LLM inconsistently chose "Profit before credit impairment" over "Profit before income tax". Shares outstanding failing (50%) because count is in narrative Note 13, not a structured table. Net debt being extracted when it should be null (banks don't have traditional debt). Capex at 77.78% because "Net investments in other assets" wasn't reinforced as the banking capex label.
**Root cause:** The extraction prompt was designed for mining/industrial companies. Banking financial statements use fundamentally different concepts: credit impairment is an operating cost (not exceptional), revenue is "Operating income" (not "Revenue"), balance sheets have deposits (not debt), and share counts appear in notes rather than formal tables. The prior L025 fix added the CRITICAL EBIT instruction but lacked a holistic banking context that helps the LLM understand *why* these distinctions matter.
**Fix:** Added a consolidated "BANKING / FINANCIAL INSTITUTION GUIDANCE" section to the Pass 3a prompt covering all 5 affected metrics. Added banking-specific keywords to row filters (credit impairment, net interest, deposits, net investments) so critical bank rows survive the >20-row filter. Added narrative fallback instruction for shares_outstanding. Added bank-specific total_debt/net_debt null rules.
**Rule:** When adding extraction support for a new sector, audit ALL metrics against that sector's actual financial statement structure — not just the one that failed. Sector differences are systemic, not isolated. A single-metric fix (L025) will leave adjacent metrics broken because they share the same structural assumptions.

---

## L031 — Sector-relative scoring transforms absolute metrics into actionable signals

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/analysis/sector_comparison.py`, `cockpit/core/research/signal_engine.py`
**Symptom:** `score_ticker("BHP")` returned a composite score of 72/100 but this was meaningless without context — is 72 good or bad for a Materials company? PE of 12 looks cheap in absolute terms but might be expensive for mining.
**Root cause:** All scoring used absolute thresholds (PE < 15 = "cheap") rather than sector-relative percentiles.
**Fix:** Created `sector_comparison.py` with 10 GICS sector mappings and 150+ ASX tickers. `compare_to_sector()` computes percentile rank for PE, FCF yield, revenue growth, EBIT margin against sector medians. `signal_engine.py` now blends 40% absolute + 60% sector-relative for valuation scoring. Sector stats cached for 24 hours.
**Rule:** Any financial metric used for scoring or screening MUST be evaluated relative to sector peers, not just against absolute thresholds. Absolute thresholds are only valid as a baseline when sector data is unavailable. The `sector_comparison` module is the canonical source for peer-relative metrics.

---

## L032 — Thesis auto-invalidation prevents stale bullish views from persisting after negative evidence

**Date:** 2026-03-31
**Subsystem:** `cockpit/core/research/thesis.py`
**Symptom:** A BUY thesis could accumulate 5 pieces of disconfirming evidence with 0 supporting, yet remain "active" indefinitely because invalidation was manual.
**Root cause:** The thesis lifecycle had no automatic feedback loop from evidence to status.
**Fix:** `add_evidence()` now calls `auto_evaluate()` after adding disconfirming evidence. Auto-invalidation triggers when disconfirming >= 2x supporting OR disconfirming >= 3 with 0 supporting. `expire_stale(90d)` runs in the watchlist scanner to catch forgotten theses.
**Rule:** Any persistent decision (thesis, signal, allocation) must have an automatic invalidation mechanism that triggers when evidence changes. Manual review alone is insufficient — the system must protect against stale views.

---

## L033 — Tool routing guidance in the system prompt dramatically improves tool selection accuracy

**Date:** 2026-03-31
**Subsystem:** `cockpit/core/chat.py`
**Symptom:** With 38 tools, the LLM sometimes chose `search_news` when `deep_research` was more appropriate, or looped `score_ticker` instead of using `screen_tickers`.
**Root cause:** Tool descriptions alone don't convey when to use one tool vs another. The LLM needs explicit routing guidance for overlapping tools.
**Fix:** Added `## Tool Selection Guide` to the system prompt with 5 categories (quick lookups, analysis, strategy, monitoring, research) and dependency hints ("score before creating thesis", "screen_tickers uses watchlist if empty").
**Rule:** When the cockpit has >25 tools, the system prompt MUST include a tool routing guide. Update the guide whenever tools are added or renamed. The guide is not documentation — it's an active part of the LLM's decision-making context.

---

## L034 — GPU topology guards must account for router-owned child workers

**Date:** 2026-03-31
**Subsystem:** `scripts/gpu_process_guard.sh`, `cockpit/integrations/llamacpp_manager.py`
**Symptom:** `scripts/cockpit` refused to start with `ERROR: GPU process guard failed` even though only the canonical router on `:8001` was running. The guard reported the router's per-model child worker on an ephemeral localhost port as a rogue `llama-server`.
**Root cause:** The guard logic classified every `llama-server` process by its own `--port` only. In router mode, llama.cpp loads models as child worker processes on dynamic localhost ports behind the authorised router, so port-only classification contradicted the actual runtime shape.
**Fix:** Topology checks now walk the process ancestry and treat ephemeral `llama-server` workers as authorised when they descend from an authorised router-mode parent (`--models-dir` on `:8001`/`:8002`). Updated the contract wording to distinguish independent rogue instances from router-owned child workers.
**Rule:** Do not enforce the canonical-port rule with port-only process inspection when router mode is enabled. Classify `llama-server` processes by ownership: independently spawned instances on non-canonical ports are rogue; router-owned child workers are part of the canonical runtime.

---

## L035 — `/chat` fallback rows must match the normal context row schema

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/tenn_chat.py`
**Symptom:** Cockpit Next.js showed `Failed to proxy http://localhost:8000/chat` with `ECONNRESET` even while `/api/health` stayed green. The chat request reached retrieval, but the backend dropped the connection before returning a JSON response.
**Root cause:** `chat_with_tenn()` has two context row paths: `_context_rows()` for ranked commentary/news chunks and an inline fallback path for raw RAG evidence. The fallback rows omitted `url`, but the later `sources` payload indexed `row["url"]` unconditionally outside the guarded retrieval block. When the chat flow fell back to raw evidence, the backend raised `KeyError: 'url'` and surfaced a 500/reset instead of a degraded answer.
**Fix:** Added `_evidence_context_rows()` so fallback evidence rows use the same schema as `_context_rows()`, including `url`. Hardened `sources` assembly to use `.get()` defaults instead of direct indexing. Added regression tests for fallback row normalization.
**Rule:** Any alternate payload path that feeds a shared response formatter must produce the same field set as the primary path. In `tenn_chat`, every `context_rows` item must include the full `_context_rows()` schema before answer/sources assembly runs.

---

## L036 — `/chat` must sanitize model JSON before formatting the response

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/tenn_chat.py`
**Symptom:** Even after retrieval succeeded, the Next.js cockpit UI could still see `/chat` resets if the model returned malformed-but-parseable JSON, such as non-numeric `confidence` or non-list `insights` / `supporting_evidence`.
**Root cause:** `chat_with_tenn()` trusted the model payload shape after `generate_json()` and performed strict Python coercions outside the guarded retrieval/LLM try block. A bad `confidence` value like `"high"` could raise during response formatting and turn a recoverable model-output issue into a backend 500.
**Fix:** Added explicit payload normalizers for `confidence`, `insights`, and `supporting_evidence`, and wrapped post-LLM response formatting in a degraded fallback path instead of letting shape errors propagate.
**Rule:** Model JSON is untrusted input even after successful parsing. Any backend response formatter consuming LLM output must coerce and validate fields before building the HTTP response, and degrade on schema drift instead of throwing.

---

## L037 — `/chat` source scores must reject NaN and infinity before JSON serialization

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/tenn_chat.py`
**Symptom:** Cockpit Next.js could still report `ECONNRESET` on `/chat` even after schema fixes, because the backend could assemble a Python dict successfully but fail only when FastAPI serialized the response body.
**Root cause:** Source score fields like `relevance_score`, `recency_decay`, and `final_score` were converted with bare `float(...)`. If retrieval or weighting produced `nan` or `inf`, the response object remained in-memory but JSON serialization could reject those non-finite floats and terminate the request with a 500/reset.
**Fix:** Added `_safe_float()` and routed all `/chat` source score fields through it for primary context rows, fallback evidence rows, and final `sources` formatting. Added a regression test covering non-finite values.
**Rule:** Any float included in an HTTP JSON response must be normalized to a finite value before serialization. Do not pass raw model/retrieval scores through `float(...)` and assume the response encoder will tolerate them.

---

## L038 — `/chat` must recursively sanitize `supporting_evidence` before returning JSON

**Date:** 2026-03-31
**Subsystem:** `backend/app/services/tenn_chat.py`
**Symptom:** Cockpit Next.js could still see `socket hang up` / `ECONNRESET` on `/chat` even after `confidence`, `insights`, and `sources` were normalized, because the response could still contain invalid nested values inside `supporting_evidence`.
**Root cause:** `_normalize_supporting_evidence()` only checked that the top-level value was a list. It passed nested dicts/lists through unchanged, so model JSON containing `NaN`, `Infinity`, or other non-JSON-safe values inside evidence items could still break FastAPI response serialization.
**Fix:** Added recursive JSON-safe normalization for `supporting_evidence`, converting non-finite floats to `null` and coercing unsupported leaf values to strings. Added a regression test covering nested non-finite evidence values.
**Rule:** Top-level schema validation is not sufficient for backend JSON responses. Any LLM-provided nested structure that is echoed back to clients must be recursively sanitized to JSON-safe primitives before returning it.

---

## L039 — `/chat` route must degrade analysis failures instead of emitting HTTP 500

**Date:** 2026-03-31
**Subsystem:** `backend/app/routes/chat.py`
**Symptom:** The Next.js cockpit UI continued to show `[SYSTEM] ERROR: API 500 Internal Server Error` and proxy `ECONNRESET` whenever any unhandled analysis-mode exception escaped the service layer, even after multiple payload-shape fixes.
**Root cause:** The `/chat` route wrapped `chat_with_tenn()` in a generic `except Exception` that converted all remaining analysis failures into HTTP 500 responses. That meant any new runtime edge case in analysis mode still propagated as a hard backend error instead of a degraded chat payload the client could render safely.
**Fix:** Added a dedicated `_analysis_response()` boundary in the route. It now sanitizes the full analysis payload recursively and degrades to a normal analysis response envelope with `system_status=degraded` if `chat_with_tenn()` or route-level payload handling throws. Added route-level regression tests for both exception and non-finite payload cases.
**Rule:** Client-facing analysis endpoints must fail soft at the route boundary. If analysis content cannot be produced safely, return a degraded analysis payload in-band rather than surfacing HTTP 500 for recoverable runtime issues.

## L040 — Prose fallback for metrics missing from structured tables

**Date:** 2026-04-01
**Subsystem:** `backend/app/services/multipass_extraction.py`
**Symptom:** ANZ shares_outstanding extracted as null despite the value appearing clearly in the PDF. Banking filings report share counts in narrative Note 13/14 rather than structured tables.
**Root cause:** Pass 3a only extracts from table markdown. Pass 3b extracts narrative (risk/guidance) but not financial metrics. No mechanism existed to extract metrics from prose sections.
**Fix:** Added `_extract_shares_from_prose()` with 4 regex patterns covering ASX prose conventions. Called in Pass 4 reconciler as a fallback only when table extraction yields null. Sanity gate rejects values < 1M or > 100B.
**Rule:** When adding a new financial metric or fixing extraction for a sector, check whether the metric appears in prose notes rather than tables. Deterministic regex is preferred over an LLM call for metrics with predictable prose patterns. Always prefer table-extracted values; prose is a fallback.

## L041 — Analysis modules must declare RAG queries, not fetch their own

**Date:** 2026-04-01
**Subsystem:** `backend/app/modules/sentiment.py`, `orchestrator.py`
**Symptom:** Sentiment module had no access to news or commentary data despite those Qdrant collections being fully populated.
**Root cause:** `_merge_context_requests()` collected `requires` (financials, risk_notes, etc.) but not RAG queries. No module had a way to declare what RAG data it needed.
**Fix:** Added `rag_queries` property to `ModuleHelpers` (empty default). `_merge_context_requests()` now collects and deduplicates module RAG queries. `analysis_rag_adapter.py` bridges modules to Qdrant. API endpoint passes `rag_fn` to the loader.
**Rule:** Analysis modules must never do I/O. They declare data needs (via `requires` and `rag_queries`), the orchestrator merges declarations, and the loader pre-fetches everything into the frozen TickerContext. This pattern keeps modules stateless and testable.

## L042 — Native CLI chat must be run/stream based, not blocking request/response

**Date:** 2026-04-08
**Subsystem:** `agent-orchestrator`
**Symptom:** The standalone orchestrator chat looked broken and unnatural because `/api/chat` blocked on a one-shot native CLI call, then returned late or hung while the UI sat waiting with no live state.
**Root cause:** I wired the native CLI like a synchronous HTTP helper instead of like a managed run with streamed events. That shape hides runtime progress, makes reconnect/replay impossible, and turns CLI quirks like open stdin or delayed output into a frozen chat UX.
**Fix:** Replaced the blocking reply path with a run-start endpoint plus SSE stream, server-owned run ids, in-memory event replay, and UI-side optimistic chat state. Codex now streams as a managed run and delegated-task creation is surfaced as an event instead of being implied by a late HTTP response.
**Rule:** When embedding a native coding CLI in an app, never model chat as `POST -> wait -> return text`. Use backend-managed runs plus streamed events so the UI can render progress, recover on reconnect, and surface delegation as part of the conversation flow.

## L043 — “Full functionality” restart must free Ollama resources before embedding startup probes

**Date:** 2026-04-08
**Subsystem:** `scripts/start_full_stack.sh`, `backend/app/services/embeddings.py`, `scripts/cockpit`
**Symptom:** `cockpit restart backend` enabled embeddings/RAG/extraction by default but the backend still died on startup validation because Ollama returned `500` for `nomic-embed-text`, and the local llama.cpp server could disappear after the wrapper exited.
**Root cause:** Two separate operator assumptions were wrong. First, the embedding path was still treating the Ollama-backed role like a llama.cpp `/v1/embeddings` server, while the intended default was Ollama `nomic-embed-text`. Second, Ollama could already have a large GPU model loaded (`qwen2.5:32b`), leaving no room for the embedding model. Third, the cockpit wrapper backgrounded llama.cpp with a shell job pattern that was not fully detached.
**Fix:** Wired the active embedding path to the existing Ollama embed client when the embedding role targets Ollama, enforced `nomic-embed-text` into the compose env on restart, stopped non-embedding Ollama runners before backend startup so the embedding probe can succeed, and switched cockpit llama launches to `setsid -f` so `llama-server` persists after `cockpit restart backend` returns.
**Rule:** When a restart command promises “full functionality,” validate the whole dependency chain, not just the feature flags. Startup wrappers must set the correct provider contract, free any competing GPU-held runtimes needed by startup probes, and detach long-lived local runtimes in a way that survives shell exit.
