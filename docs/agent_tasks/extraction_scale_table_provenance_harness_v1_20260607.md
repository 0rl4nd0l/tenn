---
job_id: extraction_scale_table_provenance_harness_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_scale_table_provenance_harness_v1_20260607.md
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/README.md
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/status.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/harness_manifest.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/evidence_table.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/root_cause_grouping.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/repair_decision.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/validation.json
  - reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/diff-check.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Scale-Table Provenance Harness

## Objective

Build a fixed regression/provenance harness for scale-table source binding from
current count-24 failures and prior diagnostics, then identify the next safe
repair path without rerunning count-24, count-32, random samples, broad
extraction, or backfill.

## Scope

Primary lane: Financial Truth.

Supporting lanes: Evaluation, Provenance, Query Orchestration.

Mode: HARNESS BUILD / AUDIT FIRST / SAFE EXTENSION ONLY IF PROVEN.

Risk: HIGH for financial truth.

Canonical base:
`07bdfe6d84eeba41c357eaf5893420ef77189625`, PR #319 merge commit.

Worktree:
`/home/l4nd0/tenn-scale-table-provenance-harness-v1-20260607`.

Branch:
`safe/extraction-scale-table-provenance-harness-v1-20260607`.

## Input Evidence

- `reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_v1_20260607/`
- `reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/`
- PR #319 result: AZJ and EDU still fail
  `validation_gate:scale_unknown`; same root cause was not proven.

## Required Harness Cases

Include at minimum AZJ, EDU, WHC, NIC, DXC, HUB, LBL, CTN, one clean
scale-known control, and one clean noncandidate control.

For each case define expected document class, expected status or fail-closed
gate, source path, selected table/page if known, table-local scale evidence,
same-page scale evidence, document-level scale evidence, row/cell provenance
fields required, forbidden outputs, and whether current behavior is expected or
a bug.

## Hard Stops

- Do not rerun count-24.
- Do not run count-32.
- Do not run random samples, broad extraction/backfill, or full
  ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime/model/GPU/service config, schema, or production data.
- Do not loosen truth gates, add broad scale inference, make a nearest-$100k
  policy change without an explicit source-bound contract, or expand canonical
  metric coverage.
- Do not merge dirty parent-batch work.

## Safe Extension Boundary

Implement at most one narrow change only if the harness proves a repeated root
cause across at least two cases. Allowed changes are limited to report-only
harness/diagnostics, selected-table scale binding when explicit table-local
evidence exists, a fail-closed guard when selected surfaces are mixed, or
additional provenance capture in report artifacts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_scale_table_provenance_harness_v1_20260607.md`
- Registry `list-active --read-only` or `DATA_MISSING`.
- JSON validation for report artifacts.
- Focused pytest if code/tests are touched.
- `py_compile` if code is touched.
- `ruff` if available.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_scale_table_provenance_harness_v1_20260607.md --repo-root .`
- Verify no source PDFs are staged.

## Final Report Requirements

Report the harness manifest, evidence table by case, root-cause grouping, any
fix made, whether count-24 rerun is justified, whether count-32 remains
blocked, `DATA_MISSING`, and the exact next prompt.
