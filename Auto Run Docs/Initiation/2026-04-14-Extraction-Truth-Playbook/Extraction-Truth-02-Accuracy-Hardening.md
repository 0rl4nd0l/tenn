# Phase 02: Extraction Accuracy Hardening

This phase improves the actual quality of extracted financial truth after the prototype loop exists. The focus stays inside the backend extraction path: identify the worst current failures from the gold corpus and review queue, fix the reusable extraction logic instead of patching outputs, reduce known residual metric gaps, and keep non-AUD documents truthful by explicit quarantine or downgrade rather than fabricated conversion.

## Tasks

- [x] Build a failure-ranked accuracy backlog from real evidence before editing extraction logic:
  - Reuse the outputs from Phase 01 plus current fixture and gold-eval tooling to identify the highest-impact failure patterns by metric, document type, parser path, and trust outcome.
  - Search existing implementation and tests first: `multipass_extraction.py`, `docling_extract.py`, `test_multipass_extraction.py`, `test_extraction_eval.py`, `test_extraction_gold_eval.py`, and `reports/extraction_real_eval_*`.
  - Write `docs/ops/extraction-truth/phase-02-backlog.md` with YAML front matter (`type: analysis`, `tags: [extraction, eval, backlog]`) listing confirmed failures, suspected root causes, and the order in which they should be attacked.
  - 2026-04-15: Added `docs/ops/extraction-truth/phase-02-backlog.md` from current synthetic eval, current real-gold runtime-hardened artifacts, prior Phase 01 proof outputs, and the existing backend extractor/eval tests. Top-ranked items are BHP FY25 annual revenue/net-debt fallback failures, then the broader live/synthetic `net_debt`, `shares_outstanding`, current-period selection, and quarterly validation-gate classes.

- [x] Fix the highest-value residual extraction gaps in reusable backend code:
  - Prioritize issues that are already called out by current repo state and likely to affect downstream analysis: `shares_outstanding`, current-period column selection, explicit versus derived `net_debt`, quarterly cash-flow layouts, and parser/table-selection edge cases from live documents.
  - Reuse existing deterministic helpers and provenance structures before adding new heuristics; if a heuristic is required, make it source-grounded and document its failure mode.
  - Do not “fix” bad outputs by post-hoc manual overrides, Cockpit-side adjustments, silent fallbacks, or any derivation that violates explicit-value extraction rules.
  - 2026-04-15: Four hardening fixes landed across `multipass_extraction.py` and tests (111 pass, 0 fail):
    1. **Net debt derived-row rejection** (`_DERIVED_NET_DEBT_ROW_FRAGMENTS` + updated `_is_explicit_net_debt_evidence`): rejects movement, ratio, and opening/closing net debt rows from explicit candidate selection — prevents fabricated point-in-time net debt from summary tables.
    2. **shares_outstanding evidence scan extended to all body-row cells** (first 3 rows): SEG-style “No. '000s” column label appears in `row[1]` not `row[0]`; the previous row[0]-only scan missed it, causing valid share counts to be nulled. Fixed by including all cells from the first 3 body rows in `share_surfaces`.
    3. **Absolute share count bypass**: LLM-returned values ≥ 1M are inherently self-evident (the extraction prompt requires absolute counts); these are no longer nulled by the weak-evidence guard — only small values that could be unscaled row numbers still require explicit marker evidence.
    4. **Quarterly validation gate** (`min_metrics = 1 if period_type == “Q” else 3`): Appendix 5B filings are structurally cash-flow-only; a single non-null CF metric is sufficient to pass the gate, while annual and half-year documents still require ≥ 3.
    5. **Docling timeout test alignment**: `DOCLING_TIMEOUT_SECONDS_PER_PAGE` was previously raised from 4→6 and `DOCLING_TIMEOUT_MAX` from 300→600; two stale tests updated to match actual constants (111 tests now all pass).
    - All Phase 02 hardening test classes (`TestIsExplicitNetDebtEvidence`, `TestSharesOutstandingMarkers`, `TestValidateGateQuarterlyThreshold`) confirmed passing.

- [x] Tighten non-AUD handling without implementing FX conversion:
  - Keep the system truthful for non-AUD documents by preserving native currency, confidence, and trust outcome behavior through the extraction and eval path.
  - Reuse the existing currency context and `ok_low_confidence` or quarantine machinery where possible; improve detection, labeling, and operator visibility if they are inconsistent.
  - Do not convert values into AUD or cross-company-normalize anything unless a separate approved FX source and policy already exist in code and documentation.
  - 2026-04-15: Three hardening fixes landed in `multipass_extraction.py` (120 tests, 0 fail):
    1. **Extended `_CURRENCY_PATTERNS`** to cover 5 additional ASX-relevant currencies (GBP, EUR, CAD, NZD, CNY/CNH/RMB) using `(?<!\w)` lookahead for symbol-ending alternatives (e.g. `NZ$'000`, `£'000`) so `\b` word-boundary failures on `$`/`£`-followed-by-apostrophe are avoided.
    2. **Fixed string-`"null"` currency normalisation** at the early detection/warning site: the LLM occasionally returns `"null"` as a JSON string rather than `null`; previously this caused a false non-AUD warning for AUD documents. The normalisation (already present in `_validate_gate`) is now also applied at Pass 1 currency propagation so no false positives reach the logger.
    3. **Surfaced non-AUD currency in `payload["_structured_extraction"]["warnings"]`**: a `non_aud_currency:<CODE>` entry is now appended when currency is not AUD, giving operator tooling a structured signal without requiring log-scraping. No FX conversion is performed.
    - New test classes `TestNonAUDCurrencyDetection` (5 tests) and `TestNonAUDCurrencyNormalisation` (4 tests) confirm all behaviours.

- [ ] Promote real failures into durable regression fixtures:
  - Add or upgrade synthetic fixtures, real-gold corpus entries, and targeted unit cases only from hand-verified PDF evidence.
  - Expand coverage across diverse ASX formats instead of overfitting to one company pattern; include at least one new case if Phase 01 exposed a repeated failure not already represented.
  - When creating structured notes about new fixtures, store them in `docs/ops/extraction-truth/fixtures/` with YAML front matter and wiki-links back to `[[phase-02-backlog]]`.

- [ ] Add or refine the test and eval gates for the hardened behavior:
  - Keep unit tests, synthetic eval, and real-gold eval as separate lanes; do not collapse them into a single score.
  - Update backend tests for the exact logic changed in this phase, then update scorecard or threshold assertions only when the new values are justified by verified corpus evidence.
  - Search for existing patterns in `financial-engine_v2/backend/tests/test_prose_shares_extraction.py`, `test_extraction_llm_separation.py`, `test_extraction_eval_harness.py`, and the scorecard scripts before adding new harness code.

- [ ] Run before-and-after validation and record the measurable delta:
  - Run the targeted backend tests, the synthetic extraction eval lane, and a limited real-gold comparison using the same commands and dataset locations used in Phase 01.
  - Write `docs/ops/extraction-truth/phase-02-accuracy-report.md` with YAML front matter (`type: report`, `related: ['[[phase-02-backlog]]', '[[phase-01-prototype-report]]']`) capturing which failures moved, which remain, and which were deliberately quarantined rather than “solved” unsafely.
  - If the phase reaches a working milestone, create the required milestone commit with explicit tested evidence.
