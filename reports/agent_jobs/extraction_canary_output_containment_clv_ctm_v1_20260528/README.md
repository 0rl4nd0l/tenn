# #96 CLV/CTM Canary Output Containment

Date: 2026-05-28
Job: `extraction_canary_output_containment_clv_ctm_v1_20260528`
Lane: Financial Truth
Supporting lanes: Provenance, Evaluation, Query Orchestration
Mode: controlled containment / minimal mutation

## Verdict

Containment completed.

The two unsafe #96 canary financial rows were deleted by exact ticker,
period, period type, and source document identity. The matching `asx_docs`
Qdrant points were deleted by explicit pre-inventory point ids. Post-checks
show the rows and matching document points no longer surface through the
financial-truth API paths, legacy financials route, direct Qdrant document
scroll, point-id retrieval, or the query-orchestrator financial-truth provider.

No canary, extraction, or backfill was run.

## Scope

Contained targets:

| Ticker | Source document id | Row identity | Issue | Qdrant points |
| --- | --- | --- | --- | ---: |
| CLV | `da9f9ea5-6596-464f-af14-5acf12f9b050` | `(CLV, 2026-01-31, H)` | million figures persisted as over-scaled raw values; EBITDA mapped into EBIT | 5 |
| CTM | `035c6758-7aed-41a6-9e84-ad154125d431` | `(CTM, 2025-12-31, H)` | `period_type=H` conflicted with annual report source | 91 |

## Pre-Mutation Inventory

The pre-mutation inventory is in
`pre_mutation_inventory.json`. It includes the full financial-row payloads,
related document and extraction-run records, risk-note records, API exposure
summary, and full Qdrant point backups with payloads and vectors for
reversibility.

Prechecks found:

- Exact target financial rows: 2.
- Same ticker/period/period-type row inventory: 2.
- CLV Qdrant points in `asx_docs`: 5.
- CTM Qdrant points in `asx_docs`: 91.
- `asx_periodic_financials` quarantine/review/suppression columns: none.
- Qdrant containment marker payload keys: none.

Because no supported quarantine or suppression state exists, exact deletion was
the smallest available containment path.

## Mutation Performed

Database:

- Deleted exactly 2 rows from `asx_periodic_financials`.
- Predicate used exact `ticker`, `period_end`, `period_type`, and
  `source_document_id` matching only the two target identities.
- Post-delete exact target row count: 0.

Qdrant:

- Deleted exactly 96 explicit point ids from `asx_docs`.
- CLV document points requested for deletion: 5.
- CTM document points requested for deletion: 91.
- Post-delete document scroll counts: CLV 0, CTM 0.

The mutation ledger is in `containment_ledger.json`.

## Preserved State

These were intentionally not mutated:

- `documents` records for both source documents.
- `extraction_runs` records for both canary runs.
- `asx_risk_notes` records.
- Source PDFs and source asset paths.
- Gold labels, prompts, parser routing, runtime/model/GPU config, schemas, news,
  and memory stores.
- Backend, worker, Qdrant, and Postgres service processes.

## Post-Containment Verification

The post-verification artifact is in `post_containment_verification.json`.

Results:

| Surface | CLV target rows | CTM target rows | Status |
| --- | ---: | ---: | --- |
| Postgres exact target rows | 0 | 0 | clear |
| Postgres same ticker/period/period-type rows | 0 | 0 | clear |
| `/api/context/ticker` | 0 | 0 | clear |
| `/api/context/company_dump` | 0 | 0 | clear |
| `/api/financials` | 0 | 0 | clear |
| Query-orchestrator financial-truth provider | 0 | 0 | clear |
| Qdrant document-id scroll | 0 | 0 | clear |
| Qdrant deleted point-id retrieve | 0 total | 0 total | clear |

Provider probe results:

- CLV: `financials_count=0`, `items_count=0`,
  `latest_snapshot_present=false`, `target_rows=[]`.
- CTM: `financials_count=0`, `items_count=0`,
  `latest_snapshot_present=false`, `target_rows=[]`.

The provider still sees document and announcement context for both tickers
because source documents were intentionally preserved. The unsafe financial
rows and matching Qdrant chunks no longer appear.

## Architecture Review

Architecture-check was invoked because this task touched vector-store/RAG
state. The `.cursor/rules/` files were absent in this checkout, so exact
rule-file validation is `DATA_MISSING`.

The actual containment did not change embedding models, vector dimensions,
distance metric, vector id derivation, document-id format, backend code, or
RAG orchestration code. It deleted only explicit, already-persisted bad
document points and exact bad financial rows.

## Remaining DATA_MISSING

- No semantic chat/RAG generation prompt was run. This was intentionally
  avoided to prevent extra model work and because direct Qdrant document-id
  scroll plus point-id retrieval proves the matching document points are absent
  from `asx_docs`.
- `.cursor/rules/` files were not present for exact architecture-rule quotes.
- Historical generated analysis artifacts on disk were not rewritten or purged;
  they should be treated as potentially stale if they were generated before
  this containment.

## Follow-Up Recommendations

- Add a supported review/quarantine state for financial rows and document
  chunks so future containment can avoid deletion.
- Add a pre-canary gate for source scale, EBIT versus EBITDA label mismatch,
  period-source consistency, and post-canary exposure checks.
- Treat this containment as a Project Memory candidate because it records the
  exact safe deletion pattern for unsafe #96 canary outputs.
