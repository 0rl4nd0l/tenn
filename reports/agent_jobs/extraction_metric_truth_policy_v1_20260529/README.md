# Extraction Metric Truth Policy V1

Date: 2026-05-29
Job: `extraction_metric_truth_policy_v1_20260529`
Lane: Financial Truth
Mode: SAFE EXTENSION

## Verdict

Implemented and validated a bounded metric-truth policy slice before any third
#96 canary batch.

No canary, extraction batch, broad backfill, DB write, direct SQL mutation,
Qdrant/news/memory mutation, source PDF edit/copy/delete/commit, parser routing
change, extraction prompt change, production gold-label mutation, runtime/model
config change, service restart, schema migration, or Cockpit UI work was
performed.

## Implemented

- Source-document classification now exposes deterministic policy output:
  `financial_report`, `advisory_only_document`, and `unknown_document`.
- Advisory-only records still fail before metric extraction and are now
  represented in candidate-manifest exclusions with the same classification
  payload.
- Scale Policy V1 now treats explicit scaled table units as authoritative and
  maps plain dollar table columns such as `2025 $` to `units`.
- Unknown scale remains a persistence blocker, and explicit source-unit
  mismatch gates remain in place.
- Period context checks now include `period_type` in both synthetic/real eval
  semantics and payload-scorecard period failure classification.
- Metric contract parity output now includes `metric_ontology_v1`.
- CLV/CTM canary-regression fixtures were added to the test-only real-gold
  fixture set after local PDF text extraction and rendered-page inspection.

## Canary Failure Mapping

- CLV: locks that `$44.1 million` revenue must not score as `$44.1 billion`,
  that `$4.2 million` NPAT must not score as `$4.2 billion`, and that EBITDA
  evidence must not satisfy canonical `ebit`.
- CTM: locks that the source is annual (`period_type=A`) and that the `2025 $`
  cash-flow table is raw dollar `units`; the prior half-year `millions` payload
  is quarantined.

## Source Verification

Local PDFs inspected:

- `/data/asx/docs/CLV/financial_performance/2026-03-24_clover-1h-fy26-results-announcement_da9f9ea5-6596-464f-af14-5acf12f9b050.pdf`
- `/data/asx/docs/CTM/financial_performance/2026-03-30_financial-report-31-december-2025_035c6758-7aed-41a6-9e84-ad154125d431.pdf`

Verification used `pdftotext`, `pdfinfo`, `pdftoppm`, and rendered PNG
inspection under `tmp/pdfs/`. The source PDFs themselves were not modified,
copied, staged, or committed.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_metric_truth_policy_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_metric_truth_policy_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_metric_truth_policy_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_metric_truth_policy_v1_20260529.md --repo-root .`
- `python3 -m py_compile` for touched service/test files
- `python3 -m json.tool` for new fixture/report JSON
- `uv run --no-project --python 3.10 --with ruff ruff check ...`
- Focused pytest:
  - `15 passed, 210 deselected`
- Scoped touched-suite pytest excluding one unrelated local asset-path check:
  - `224 passed, 1 deselected`

Known validation gap:

- Full touched-suite pytest failed one pre-existing environment/source-asset
  assertion:
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
  expects the 10X canonical corpus source PDF under the repo-relative
  `financial-engine_v2/data/asx/docs/...` path. The same file exists under
  `/data/asx/docs/...`, but source-PDF copying/committing was forbidden and was
  not performed.

## Files Intentionally Not Touched

- DB, Qdrant, news, memory, and canonical financial truth stores.
- Source PDFs.
- Parser routing.
- Extraction prompts.
- Existing production real-gold corpus labels.
- Runtime/model/GPU config.
- Persisted schemas and Alembic migrations.
- Cockpit UI.

## Remaining Blockers

- Third #96 canary still requires explicit operator approval.
- Non-AUD/Rp trillion policy remains conservative and unresolved.
- Global `ok_low_confidence` surfacing policy remains report-only.
- Full graduation to accurate extraction still requires an approved third
  canary and broader accuracy evidence after this policy slice.
