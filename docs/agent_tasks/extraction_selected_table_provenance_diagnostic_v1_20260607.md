---
job_id: extraction_selected_table_provenance_diagnostic_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_selected_table_provenance_diagnostic_v1_20260607.md
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/README.md
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_runner.py
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_results.json
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/provenance_summary.json
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/repair_decision.json
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/nic_optional_task_prompt.md
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/status.json
  - reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/validation.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
---

# Selected Table Provenance Diagnostic After Count-24

## Objective

Build a fixed, report-local selected-table provenance diagnostic for WHC, AZJ,
and EDU only. For each document, capture the runtime-selected table/page, table
header, row refs where available, per-metric source scale, final payload scale
decision, and why `_common_metric_source_scale` did or did not set scale.

## Scope

Mode: REPORT_LOCAL diagnostic first. SAFE_EXTENSION only if the diagnostic
proves the same missed selected-table scale-binding pattern in at least two
audited documents.

Audited documents only:

- WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- EDU `ac3c9ab0-e01a-4996-95f9-6466388ddc9c`

Prepare a separate optional NIC webcast-details noncandidate task prompt, but
do not implement NIC handling in this diagnostic.

## Hard Stops

- Do not rerun count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, or production data.
- Do not edit source PDFs.
- Do not merge dirty parent batches.
- Do not clean, stash, reset, or delete unrelated dirt.

## Required Evidence

- Prior scale-source evidence report:
  `reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/`
- Current source PDFs for WHC, AZJ, and EDU.
- Runtime/reporter-local selected-table provenance where available.
- Explicit `DATA_MISSING` for any requested field the current artifacts or
  report-local diagnostic cannot prove.

## Required Output

- Per-document diagnostic results for WHC, AZJ, EDU.
- Shared-pattern assessment and repair decision.
- Optional NIC webcast-details task prompt only.
- Validation and explicit no-sample/backfill statement.
