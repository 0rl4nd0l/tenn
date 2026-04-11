# Supplemental Metric Normalization Report

**Date:** 2026-04-11
**Status:** SPEC ONLY - no runtime behavior change
**Execution mode:** EXTEND existing `docs/extraction/` artifacts only

## 1. LANE CLASSIFICATION

**CONFIRMED**

| Lane | Classification | Notes |
|------|----------------|-------|
| Evaluation | PRIMARY | This registry/report exists to guide evaluator-oriented normalization only. |
| Provenance | SECONDARY | Used only to preserve raw-metric traceability back to curated source labels. |
| Financial Truth runtime | EXCLUDED | No runtime schema or truth-lane changes. |
| Query Orchestration | EXCLUDED | No query-path changes. |
| Memory | EXCLUDED | No memory/orchestrator changes. |
| Reporting runtime | EXCLUDED | No production reporting changes. |
| Extraction runtime hardening | EXCLUDED | No extractor logic changes. |
| Evaluator runtime expansion | EXCLUDED | No scoring/runtime changes in this task. |

## 2. COLLISION ASSESSMENT

**CONFIRMED**

- Risk level: **MEDIUM**.
- Existing target artifacts already exist locally at `docs/extraction/supplemental_metric_normalization_registry.yaml` and `docs/extraction/supplemental_metric_normalization_report.md`.
- Those artifacts are not present in local git history, so prior authorship/status is **DATA_MISSING**.
- No in-flight ontology refactor was found in Claude memory, sprint docs, or nearby specs.
- Broad unrelated runtime work is in flight elsewhere in the worktree, so this update stays doc-only and in-place.

**Distinct surfaces audited**

| Surface | What it is | Why it is not this registry |
|---------|------------|-----------------------------|
| `scripts/metric_ontology_mapper.py` | Runtime alias resolver | Lightweight canonicalization helper for extractor-facing names, not evaluator-scoped normalization planning. |
| `financial-engine_v2/backend/app/services/multipass_extraction.py::METRIC_FIELDS` | Extraction metric contract | Authoritative runtime extraction field list; unchanged. |
| `financial-engine_v2/backend/tests/eval_config.json` and `financial-engine_v2/data/extraction_gold_real/README.md` | Evaluator metric set and tolerances | Defines current live eval lane only; unchanged. |
| `docs/extraction/*normalization*` | Spec artifacts | Offline normalization ontology/reporting lane updated here. |

## 3. EXECUTION MODE

**CONFIRMED**

- Extend the two existing `docs/extraction/` artifacts only.
- No runtime files, tests, schema, or production paths changed.

## 4. AUDIT FINDINGS

**CONFIRMED**

- `docs/extraction_gold_real_statement_pass_full.zip` preserves the canonical evaluator lane and adds a much larger curated `supplemental_metrics` layer.
- `docs/extraction_gold_real_enriched.zip` is the earlier smaller supplemental baseline.
- `docs/extraction_gold_real_exhaustive_run/` is materially noisier and is suitable only as a discovery/filter surface.
- Schema compatibility is preserved: canonical `metrics`, `metric_evidence`, `expected_trust`, and conservative explicit-only labeling remain intact.

**DATA_MISSING**

- No committed git history exists for the prior normalization registry/report in this worktree.

## 5. CORPUS-V2 INVENTORY SUMMARY

**CONFIRMED**

| Layer | Authority | Unique names/labels | Datapoints | Notes |
|------|-----------|---------------------|------------|-------|
| Curated canonical lane | Authoritative for current evaluator expectations | 3 metric names | 22 | `revenue` 7, `operating_cash_flow` 10, `net_debt` 5 |
| Curated supplemental lane baseline | Earlier smaller inventory | 85 raw metric names | 136 | `docs/extraction_gold_real_enriched.zip` |
| Curated supplemental lane corpus-v2 | **Primary normalization source** | 337 raw metric names | 539 | `docs/extraction_gold_real_statement_pass_full.zip` |
| Exhaustive raw extraction surface | **Discovery/filtering only** | 2,999 raw row labels | 18,652 | `docs/extraction_gold_real_exhaustive_run/` |

**CONFIRMED**

- corpus-v2 adds **252** curated supplemental raw names and **403** curated datapoints over the earlier enriched bundle.
- The curated supplemental layer, not the exhaustive surface, is authoritative for evaluator-oriented normalization.
- Exhaustive discovery remains secondary and is used here only to define ignore filters and collision guards.

## 6. KEEP / HOLD / IGNORE POLICY APPLIED

**CONFIRMED**

| Bucket | Count | Interpretation |
|--------|-------|----------------|
| KEEP | 14 curated families | Reusable normalized families suitable for evaluator planning now. |
| SUPPORT_ONLY | 11 curated families | High-value diagnostic/support families, not prioritized evaluator targets yet. |
| HOLD | 151 curated families | Supplemental only; form-specific, ambiguous, or stability-blocked. |
| IGNORE | 4 discovery filter groups | Exhaustive raw noise/residue explicitly excluded from registry promotion. |

**Representative KEEP families**

- `underlying_ebitda`, `net_assets`, `free_cash_flow`, `profit_before_taxation`
- `basic_earnings_per_share`, `diluted_earnings_per_share`
- `finance_income`, `finance_costs`, `net_finance_costs`
- `interest_received_statement`, `interest_paid_statement`, `income_tax_expense`, `depreciation_and_amortisation`, `other_income`

**Representative SUPPORT_ONLY families**

- `total_assets`, `total_equity`, `total_liabilities`
- `borrowings_current`, `borrowings_non_current`, `cash_and_cash_equivalents_balance_sheet`
- `total_current_assets`, `total_non_current_assets`, `property_plant_and_equipment`, `trade_and_other_payables_current`, `inventories_current`

**Representative HOLD families**

- `profit_after_tax_family`
- `capital_expenditure_and_investment_activity`
- `operating_profit_ebit_family`
- `financing_facilities_and_liquidity`
- `cash_rollforward_and_cash_position_variants`
- `operating_receipts_and_outgoings_5b`
- `insurance_service_result` and related insurance/reinsurance families

**Representative IGNORE groups from exhaustive discovery**

- `discovery_noise_layout_residue` -> 741 datapoints
- `discovery_noise_table_subtotals` -> 1,747 datapoints
- `discovery_noise_boilerplate_headers` -> 358 datapoints
- `discovery_noise_date_fragments` -> 407 datapoints

## 7. UPDATED NORMALIZATION MODEL

**CONFIRMED**

Each registry entry now carries the required fields:

- `raw_metric_name`
- `normalized_metric_type`
- `source_layer`
- `inclusion_decision`
- `statement_family`
- `form_type`
- `period_scope`
- `unit`
- `underlying_flag`
- `evaluator_ready_status`
- `coverage_doc_count`
- `coverage_datapoint_count`
- `ambiguity_notes`
- `holdout_reason`

**Model rules applied**

- Collapse by economic concept where semantics are clean.
- Keep balance-sheet support lines distinct when economically distinct.
- Keep 5B quarterly funding/runway/admin families supplemental-only.
- Keep net-debt-adjacent variants blocked until base `net_debt` extraction stabilizes.
- Do not let exhaustive raw row labels become evaluator candidates.

## 8. UPDATED REGISTRY OUTPUT

**CONFIRMED**

Updated machine-readable artifact:
- `docs/extraction/supplemental_metric_normalization_registry.yaml`

Registry highlights:
- canonical lane preserved unchanged
- corpus-v2 curated supplemental inventory fully re-based onto statement-pass-full
- exhaustive discovery represented only through explicit IGNORE filter groups
- ranked Tier 1 / Tier 2 shortlist included in the registry metadata

## 9. UPDATED EXPANSION SHORTLIST

**CONFIRMED**

### Tier 1 - best next normalized families after the current canonical lane

| Rank | Family | Docs | Datapoints | Why |
|------|--------|------|------------|-----|
| 1 | `underlying_ebitda` | 5 | 5 | Benchmark-aligned EBITDA family; clear semantics and good cross-document reuse. |
| 2 | `net_assets` | 5 | 5 | Clean balance-sheet family with low ambiguity. |
| 3 | `free_cash_flow` | 4 | 4 | Reusable cash-generation family from result documents. |
| 4 | `profit_before_taxation` | 7 | 7 | Broad cross-document coverage and good economic comparability. |
| 5 | `basic_earnings_per_share` | 5 | 5 | Strong coverage, but evaluator logic must remain currency-aware. |
| 6 | `diluted_earnings_per_share` | 7 | 7 | Same readiness profile as basic EPS. |
| 7 | `finance_income` | 6 | 6 | Clear reusable statement family. |
| 8 | `finance_costs` | 6 | 6 | Clear reusable statement family. |
| 9 | `net_finance_costs` | 3 | 3 | Lower coverage but clean semantics. |

### Tier 2 - high-value support families

| Rank | Family | Docs | Datapoints | Why |
|------|--------|------|------------|-----|
| 1 | `total_assets` | 4 | 4 | Benchmark guidance explicitly calls this a sensible next candidate family. |
| 2 | `total_equity` | 3 | 4 | Benchmark guidance explicitly calls this a sensible next candidate family. |
| 3 | `total_liabilities` | 4 | 4 | Core balance-sheet support family. |
| 4 | `cash_and_cash_equivalents_balance_sheet` | 7 | 7 | Important for residual net-debt diagnosis; kept separate from 5B cash labels. |
| 5 | `borrowings_current` | 6 | 6 | High-value debt-structure support family. |
| 6 | `borrowings_non_current` | 6 | 6 | High-value debt-structure support family. |
| 7 | `total_current_assets` | 4 | 4 | Useful for working-capital structure review. |
| 8 | `total_non_current_assets` | 4 | 4 | Useful for asset-base structure review. |
| 9 | `property_plant_and_equipment` | 4 | 4 | Support-only due overlap with capex and investment activity. |
| 10 | `trade_and_other_payables_current` | 4 | 4 | Working-capital support family. |
| 11 | `inventories_current` | 3 | 3 | Working-capital support family. |

### Hold

- 5B funding/runway/admin lines, financing facilities, quarterly cash receipts/outgoings, and end-of-period cash roll-forwards
- profit-after-tax parent/group variants and EBIT-like operating-profit variants
- capital expenditure and investment activity variants where definition drift is still material
- insurance and reinsurance sector-specific lines
- net-debt-adjacent ratios and gross-debt variants until base `net_debt` extraction stabilizes

### Ignore

- layout residue tokens such as `unlabelled_row`, `Total`, `Other`, `to`
- subtotal/unit fragments such as `ppmMo subtotal`, `g/tAu subtotal`, `% subtotal`
- boilerplate headings and geography headers such as `Australia` and filing title lines
- date/axis fragments such as `FY2024`, `8 Nov 24`, `Aug 26`

## 10. OPEN RISKS

**CONFIRMED**

- EPS families mix US-cent and local-cent raw labels; any future evaluator promotion must stay currency-aware.
- `profit_after_tax_family` still mixes parent/group/minority-interest semantics.
- corpus-v2 materially increases 5B density; HOLD lines can dominate counts if not separated from evaluator-ready families.
- exhaustive discovery is PyMuPDF-derived and extremely noisy; it must remain filter-only.
- benchmark guidance still blocks net-debt-adjacent expansion until base `net_debt` extraction is fixed.

## 11. EXACT FILES CREATED / CHANGED

**CONFIRMED**

| File | Action |
|------|--------|
| `docs/extraction/supplemental_metric_normalization_registry.yaml` | UPDATED in place |
| `docs/extraction/supplemental_metric_normalization_report.md` | UPDATED in place |

No runtime files changed.

## 12. RECOMMENDED NEXT STEP

**CONFIRMED**

- Review the Tier 1 ready families for ontology acceptance only.
- If accepted, treat `underlying_ebitda`, `net_assets`, `free_cash_flow`, `profit_before_taxation`, and EPS families as the next evaluator-planning shortlist.
- Keep Tier 2 families support-only until the ready lane is settled.
- Do not promote net-debt-adjacent or 5B-specific families until extraction stability and evaluator scope are revisited in a separate runtime-approved workstream.
