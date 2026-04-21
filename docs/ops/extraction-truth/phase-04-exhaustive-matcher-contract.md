# Phase 04 — Exhaustive Real-Gold Matcher Contract

**Status:** DESIGN — pending owner approval. No implementation yet.
**Lane:** Evaluation (primary), Provenance contract (secondary).
**Goal:** Define the matcher so the exhaustive gold layer becomes a parallel diagnostic scorecard without replacing the canonical release gate.
**Non-goal:** Porting generators, extending extractors, touching runtime/UI.

Confidence markers: **Confirmed** = verified from source; **Inferred** = pattern-derived; **Speculative** = design judgment.

---

## 1. Audit Summary

### 1.1 Canonical real-gold path (release gate) — **Confirmed**
- Entrypoint: `financial-engine_v2/backend/app/main.py` → `POST /api/extraction-eval/real-gold` (`_run_real_gold_eval_sync`).
- Scoring: `financial-engine_v2/backend/app/services/extraction_gold_eval.py` → `evaluate_real_gold_fixture()`, `MetricEvaluation` (status ∈ {correct, wrong, missing, abstain, quarantine}).
- Fixtures: `financial-engine_v2/data/extraction_gold_real/*.json` (~12 docs, curated metric-period-value tuples).
- Metric universe: 10 canonical fields in `multipass_extraction.py:METRIC_FIELDS` + aliases in `_REAL_GOLD_METRIC_ALIASES`.
- Output artifacts: `reports/extraction_real_eval_results.json`, `extraction_real_eval_summary.json`.

### 1.2 Exhaustive layer (currently shelfware) — **Confirmed**
- Location: `docs/extraction_gold_real_exhaustive_run/`.
- Form: **numeric inventory**, not labelled gold. Per-datapoint row schema:
  `document_id, page, block_index, value_ordinal, column_hint, raw_value, value_status, parsed_numeric, normalized_value, row_label, context_text, unit_type, currency, raw_scale, datapoint_id`.
- Volume: 18,652 datapoints across 10 documents; 33,737 quantitative lines.
- No existing consumer; `exhaustive_extraction_run.py` is generator-side.
- Key property: `datapoint_id` is stable and positional (`doc__pXXX__bYYY__row_label__col__ord`).

### 1.3 Ontology / normalization — **Confirmed**
- Canonical metric registry: `METRIC_FIELDS` (10 families).
- Alias maps: `scripts/metric_ontology_mapper.py` (~33 aliases); `_REAL_GOLD_METRIC_ALIASES` in eval module.
- Period normalization: `scripts/period_ontology_mapper.py`.
- **Gap identified**: no existing mapper from exhaustive `row_label`/`context_text` free-text → canonical metric family. This is the precondition the matcher depends on.

### 1.4 Collision assessment
- Risk level: **LOW** for design-only work.
- Risk level: **MEDIUM** for future implementation — the matcher will need to read canonical ontology surfaces (read-only).
- Safe-to-reference: all files listed above, plus `docs/ops/extraction-truth/phase-03-contract-map.md`.
- Blocked/contested: none at design phase.

### 1.5 Critical framing (must read before design)
The canonical gold and exhaustive gold **do not operate on the same unit**. Canonical = (document, metric-family, period, value) with explicit labels. Exhaustive = (document, page, block, row_label-text, numeric) with implicit labels. The matcher cannot treat them symmetrically. Anything that conflates the two creates a second truth system — which is exactly what the non-negotiables forbid.

---

## 2. Matcher Design Decisions

### 2.A Unit of Matching
**Decision:** Two-tier matching unit.

1. **Anchored tuple (primary):** `(document_id, canonical_metric_family, period_end, period_type, normalized_value)`.
2. **Positional tuple (secondary, for FP analysis):** `(document_id, datapoint_id, normalized_value)`.

Rationale: canonical scoring already operates on metric-period-value; for the matcher to be a coherent overlay it must project exhaustive datapoints up to that unit via an ontology bridge (see §2.D). The positional tuple is kept so unmatched extracted values can still be traced to their nearest numeric twin in the document.

### 2.B Context Rules
Two-phase matching. All comparisons case-normalized and whitespace-collapsed.

Phase 1 — **hard context gate** (must all match exactly or be explicitly allowed):
- `document_id`: exact.
- `period_end`: exact ISO date.
- `period_type`: exact (annual/half/quarter).
- `currency`: exact ISO code.
- `scale`: normalized (millions/thousands/raw) to a single integer multiplier; match on normalized integer, not string.

Phase 2 — **soft provenance signals** (scored, not gating):
- `method/provider` (extractor lineage): informational.
- `page` proximity: when multiple exhaustive candidates, prefer the one closest in page to the evidence span already on the extracted fact.
- `row_label`/`context_text` match confidence from the ontology bridge.

Any Phase 1 mismatch → `context_mismatch` bucket (not `wrong_value`). This preserves canonical's distinction between "number on wrong period" and "wrong number on right period".

### 2.C Value Match Rules
- **Numeric equality:** post-`scale` normalization, absolute tolerance OR relative tolerance (whichever is looser), mirroring canonical `tolerances` on each fixture.
- **Default tolerance:** `max(abs_tol_per_metric, rel_tol × |expected|)`; `rel_tol` default **0.01** (1%) — **Inferred** matches canonical practice; confirm with owner.
- **Sign:** must match exactly; sign flips → `signed_mismatch` (separate bucket; common for net_debt, investing_cf).
- **Percentages:** compared in decimal form (42% → 0.42). Percentages that appear in exhaustive as raw `42` are normalized by the ontology bridge's `unit_type=percentage` flag.
- **Per-share metrics:** treated as numeric with tighter default tolerance (`rel_tol=0.005`, 0.5%) because rounding bites harder — **Speculative**, owner to confirm.
- **Nulls / missing / abstain:** mirror canonical statuses. Exhaustive inherits canonical's abstain behavior — if canonical abstained on the fixture, exhaustive must not count recall against it.
- **Derived vs explicit:** if the extracted value was computed (e.g., `net_debt = borrowings − cash`), exhaustive should record this as `derived_match` when the exhaustive datapoint is one of the inputs, not the output. Prevents double-counting.
- **Duplicate equivalent rows:** when multiple exhaustive datapoints share `(canonical_metric_family, period, normalized_value)`, match against the one with highest ontology-bridge confidence; others emit a `redundant_gold` note (not a mismatch).
- **Multiple candidates at different values:** → `ambiguous_gold`; do not pick one silently.

### 2.D Ontology / Normalization Rules
This is the **critical precondition** without which the matcher cannot run.

**New artifact required (later, not now):** `metric_ontology_bridge` — a deterministic function:
```
bridge(row_label, context_text, column_hint, unit_type) →
  { family: canonical_metric_family | "supplemental" | "unsupported",
    confidence: float ∈ [0, 1],
    rationale: str }
```

Rules:
- One-to-one labels (e.g., "Revenue" → `revenue`) resolve deterministically via the existing alias map.
- One-to-many (e.g., "Operating cash flow" in quarterly 5B can mean receipts-minus-payments or net operating cash) → `ambiguous_family`; matcher treats as `supplemental`, never forces a canonical match.
- Many-to-one (e.g., "Net debt", "Net (debt)/cash" → `net_debt`) consolidated via the alias map.
- **Never collapse automatically:** EBIT vs EBITDA, underlying vs statutory, consolidated vs parent-only, continuing vs total — all must remain distinct families even if the extractor only targets one. The bridge marks the non-target variant as `supplemental`.
- **Narrative numbers** (from `all_quantitative_lines.jsonl`) excluded from P1 match attempts; consumed by `narrative_cross_check` analysis only.

**Bridge output is advisory, not canonical.** Canonical scoring never reads the bridge. This is the firewall.

### 2.E Score Semantics (parallel scorecard)
Per-document, per-metric-family, and corpus-aggregate dimensions.

Classifications (mutually exclusive):
- `matched_exact` — value and context match within tolerance.
- `matched_signed` — matches after sign flip (separate reporting).
- `wrong_value` — context matches, value outside tolerance.
- `context_mismatch` — value matches somewhere, but not in the expected period/currency/scale.
- `missing_from_extraction` — exhaustive has it, canonical target, extraction did not emit → **recall FN**.
- `unsupported_but_present` — extraction emitted, exhaustive has the number but bridge maps the row_label to `supplemental` (not a canonical target) — diagnostic only; **not** a canonical FP.
- `hallucinated` — extraction emitted, no corresponding datapoint in exhaustive within tolerance → **hard FP**.
- `ambiguous` — multiple candidate datapoints at different values.
- `abstained` — canonical abstained on the fixture; pass-through.
- `quarantined` — canonical quarantined (context failure); pass-through, do not score.

Metrics emitted:
- `precision_strict` = `matched_exact / (matched_exact + wrong_value + hallucinated)`.
- `recall_family` = `matched_exact / (matched_exact + missing_from_extraction)` — per canonical family only.
- `coverage_density` = `matched_exact / total_exhaustive_datapoints_with_bridge_family` — **diagnostic only**, expected to be very small and must be labelled as such.
- `context_mismatch_rate`, `signed_mismatch_rate`, `ambiguity_rate` — separate diagnostic series.

`coverage_density` is the metric most likely to be misread; the scorecard must prominently state it is not a recall score.

### 2.F Coexistence With Canonical
**Firewall rules:**
1. Canonical scorecard path does not import from the matcher. The matcher imports from canonical (read-only: ontology, fixture loader, status enum).
2. Matcher runs **after** canonical completes and consumes canonical's `MetricEvaluation` output as an input. It does not re-evaluate correct/wrong/missing — it reuses canonical's verdicts and adds exhaustive dimensions.
3. Matcher outputs to a distinct artifact path: `reports/exhaustive_eval/<run_id>/` — never overwrites canonical reports.
4. CI release gate checks canonical only. Exhaustive outputs are attached as diagnostic artifacts but do not block merge.
5. **Disagreement interpretation:**
   - Canonical `correct` + matcher `hallucinated` → exhaustive coverage gap (exhaustive gold incomplete), not an extractor defect. Logs a `gold_coverage_gap` note.
   - Canonical `wrong` + matcher `matched_exact` in same doc at different context → likely period/scale context bug in extraction. Logs `context_bug_candidate`.
   - Canonical `missing` + matcher finds `missing_from_extraction` in exhaustive at a clean context → high-signal extractor miss.
   - Canonical `abstain` + matcher `matched_exact` → extractor was overly cautious; diagnostic only.

### 2.G Review / Analysis Outputs (emit contract, no implementation)
Artifacts per run, all JSONL unless noted:
- `summary.json` — corpus and per-document aggregate scorecard.
- `per_document.jsonl` — one record per (document, metric_family) with classification.
- `unmatched_extracted.jsonl` — extracted facts with no exhaustive twin; one row per fact.
- `unmatched_gold.jsonl` — exhaustive datapoints mapped to a canonical family the extractor should have emitted; one row per datapoint.
- `ambiguity_buckets.jsonl` — multi-candidate cases with all candidates retained.
- `bridge_coverage.jsonl` — per-document row_label inventory with bridge verdicts (used to monitor ontology drift).
- `disagreements.jsonl` — canonical-vs-matcher disagreement records per §2.F rule 5.

All records carry: `run_id`, `document_id`, `canonical_metric_family` (nullable), `datapoint_id` (nullable), `extraction_fact_id` (nullable), `classification`, `evidence_refs`, `bridge_confidence`, `rationale`.

---

## 3. Failure-Mode Taxonomy

| Code | Definition | Canonical label | Matcher label |
|---|---|---|---|
| F1 | Extraction omitted supported fact | `missing` | `missing_from_extraction` |
| F2 | Extractor emitted unsupported fact | `wrong` or `correct` | `hallucinated` OR `unsupported_but_present` |
| F3 | Wrong value on correct metric | `wrong` | `wrong_value` |
| F4 | Correct value on wrong metric family | typically `wrong` | `family_mismatch` (new bucket, confirms canonical verdict from exhaustive side) |
| F5 | Correct metric/value but wrong context | `quarantine`/`wrong` | `context_mismatch` |
| F6 | Duplicate / competing fact emission | rarely caught | `redundant_extraction` |
| F7 | Provenance too weak to classify | `abstain` | `provenance_weak` (pass-through of canonical abstain) |
| F8 | Gold ambiguity / gold drift | opaque to canonical | `ambiguous_gold` or `gold_coverage_gap` |

F4, F6, and F8 are classes canonical cannot surface on its own; these are the diagnostic value of the exhaustive layer.

---

## 4. Minimal Later Implementation Plan

Four steps. Each bounded, reversible, and safe to defer.

### Step 1 — Ontology bridge (**precondition**, highest risk item)
- Lane: Evaluation (read) + Provenance contract (new).
- Collision risk: **MEDIUM** — introduces a new artifact the matcher depends on.
- Files likely touched: new `financial-engine_v2/backend/app/services/metric_ontology_bridge.py`; no modifications to existing eval code.
- Safe: pure function, deterministic, unit-testable against a gold label set. Does not touch canonical scoring.
- Deferrable parts: narrative-text family inference; percentage-unit normalization beyond simple cases.
- Gate to proceed: owner approval of bridge-output schema + a labelled set of ~200 row_labels across the 10 docs to validate against.

### Step 2 — Matcher core
- Lane: Evaluation only.
- Collision risk: **LOW** — reads canonical output, writes to a new reports directory.
- Files likely touched: new `financial-engine_v2/backend/app/services/exhaustive_matcher.py`; new `scripts/run_exhaustive_matcher.py` CLI.
- Safe: post-hoc, deterministic, no DB writes, no LLM calls.
- Deferrable: CI wiring, parallel execution.

### Step 3 — Analysis helpers
- Lane: Evaluation.
- Collision risk: **LOW**.
- Files likely touched: new `scripts/analyze_exhaustive_disagreements.py` producing the `disagreements.jsonl` views; CSV/markdown summary emitters.
- Deferrable: aggregation across multiple runs (trend lines).

### Step 4 — Cockpit / review UI integration
- Lane: Reporting/UI — **currently blocked** per lane rules.
- Collision risk: **MEDIUM-HIGH** at time of execution — touches blocked lanes.
- Files likely touched: cockpit review tabs, backend API for exhaustive summaries.
- Safe only after Steps 1–3 have produced stable artifacts for ≥ 2 runs without schema changes.
- **Should remain deferred** until exhaustive scoring has demonstrated diagnostic value against real extractor misses, not just corpus drift.

---

## 5. Risks / Open Questions

1. **Ontology bridge quality is the whole system.** If the bridge labels `row_label`s poorly, the matcher will produce high-noise outputs and burn owner trust in the lane. Require a labelled validation set before shipping Step 1.
2. **Exhaustive corpus drift.** The exhaustive artifacts are dated 2026-04-11. If the extractor or PDFs change, exhaustive must be regenerated; the matcher must refuse to run against stale corpora (version check via audit summary timestamp).
3. **Percentage / ratio handling.** `42% → 42000000` in the current CSV suggests the generator is treating every numeric block as currency. The bridge must distinguish `unit_type=percentage` and re-normalize. **Confirm with owner** before Step 1.
4. **Coverage_density misread risk.** Any scorecard that reports `matched / 18652` will look catastrophic. Must be gated behind explicit "diagnostic only" framing or omitted entirely until the bridge is tuned.
5. **Canonical fixtures (12) ≠ exhaustive docs (10).** Two canonical fixtures have no exhaustive counterpart. Matcher must handle this by emitting `no_exhaustive_pair` rather than silently dropping the canonical result.
6. **Gold drift feedback loop.** If the matcher surfaces `gold_coverage_gap`, that is a signal to extend canonical gold — **never** a signal to relax canonical scoring. Process rule, not code rule.
7. **Tolerance inheritance.** Should exhaustive scoring use canonical's per-fixture tolerances or a stricter uniform policy? Default to canonical inheritance; owner to confirm.

---

## 6. Exact Recommendation

**Resolve X blocker first.**

Do not implement the matcher next. The blocker is §2.D — the metric ontology bridge. Without a deterministic `row_label → canonical_family` projection, the matcher has nothing to match against. Shipping the matcher first would either:
- produce a corpus-wide coverage_density figure near zero that will be misread as an extractor regression, or
- rely on ad-hoc string matching that hardens into a shadow ontology — a second truth system, the exact outcome the contract forbids.

**Proposed smallest safe next step:**
1. Owner approves the contract in this doc (Sections 2.A–2.G, 3, 4).
2. Owner (or the Evaluation lane) produces a ~200-row labelled validation set mapping `row_label + context_text` → canonical family or `supplemental/unsupported`.
3. Step 1 (ontology bridge) is implemented against that validation set as a pure function, with unit tests, in a single PR.
4. Only after Step 1 ships green, Step 2 (matcher core) is scoped.

Canonical scoring remains the release gate throughout. Exhaustive work stays additive.

---

## 7. Compliance Statement

- **SYSTEM_CONTRACT.md invariants preserved:** no fallbacks, no substitutions, no parallel truth system. Canonical pipeline and release gate unchanged.
- **Layer boundaries:** canonical financial truth ↔ evaluation ↔ provenance ↔ reporting remain strictly separated. The matcher lives entirely inside evaluation and imports canonical read-only.
- **Lane discipline:** all proposed work in Evaluation (Step 1–3) with UI work (Step 4) explicitly deferred.
- **No implementation performed.** This document is audit + design only.
