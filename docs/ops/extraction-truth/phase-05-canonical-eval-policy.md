# Extraction Truth Phase 05 — Canonical Eval Policy

Date: 2026-04-20  
Status: active  
Scope: evaluation discipline only (no extractor-rule expansion in this phase)

## 1) Canonical vs non-canonical policy

Canonical KPI runs are defined by a fixed tuple:

- dataset: `financial-engine_v2/data/extraction_gold_real`
- method: `docling`
- strict_method: `true`
- limit: `0`
- tolerance: `0.01`
- prompt_variant_id: `null`
- model_override: `null`

All other runs are `non_canonical` and are excluded from canonical KPI rollups.

## 2) Drift cleanup plan

1. Pin and persist fixture identity in every run using:
   - fixture content hash
   - fixture git commit (when available)
   - fixture dirty flag
2. Mark historical mixed-mode outputs as legacy/non-comparable in reporting.
3. Fail KPI ingestion if `kpi_eligible != true`.

## 3) Targeted fixture expansion plan (next corpus step)

Add a small, bounded expansion focused on priority investigation cases:

- BHP annual revenue period/table ambiguity variants
- TLS currency/context mismatch variant
- MIN/TLS shares_outstanding format variants

Goal: improve evidence quality before any broad extractor redesign proposal.

## 4) Failure certainty classification

| Case | Certainty |
| --- | --- |
| Mixed parser/flag runs create non-comparable KPI outputs | confirmed |
| Fixture expectation drift exists across artifacts | confirmed |
| BHP miss pattern is period/table-selection related | inferred |
| TLS miss pattern is currency/context-routing related | inferred |
| Current misses define the long-term dominant failure classes | speculative |

## 5) Safe hardening boundary vs redesign-required

Safe hardening (allowed now):

- canonical run enforcement and KPI exclusion
- evidence completeness gating and explicit abstain/quarantine triggers
- targeted fixture expansion for investigation quality

Needs redesign (defer until post-expansion evidence):

- repeated cross-table/current-period resolution failures that remain after safe hardening
- persistent parser-dependent semantic divergence on key metrics

Data-bound classes:

- `DATA_AMBIGUITY`: document contains multiple plausible values with insufficient disambiguation signal
- `DATA_MISSING`: required metric is absent from document surface
