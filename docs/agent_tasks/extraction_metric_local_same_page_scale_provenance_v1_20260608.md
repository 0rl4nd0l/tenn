---
job_id: extraction_metric_local_same_page_scale_provenance_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_local_same_page_scale_provenance_v1_20260608.md
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/README.md
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/status.json
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/capture_runner.py
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/case_candidate_audit.json
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/provenance_capture.json
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/repair_decision.json
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/validation.json
  - reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_metric_local_same_page_scale_provenance_v1_20260608
mutation_mode: safe_extension
production_data_access: false
---

# Metric-Local Same-Page Scale Provenance Capture

## Objective

Build a no-write metric-local same-page scale provenance capture for AZJ plus
one additional clean same-page candidate from the fixed scale-table harness.
Use the fixed harness manifest as the case contract and decide whether a narrow
same-page scale propagation repair is justified.

## Scope

Primary lane: Financial Truth.

Supporting lanes: Evaluation, Provenance, Query Orchestration.

Mode: NO-WRITE PROVENANCE CAPTURE / AUDIT FIRST / REPAIR ONLY IF PROVEN.

Base commit:
`bafdb45c88bfab3aa238954ed737f186bbfe7ef6`.

Worktree:
`/home/l4nd0/tenn-metric-local-same-page-scale-provenance-v1-20260608`.

Branch:
`safe/extraction-metric-local-same-page-scale-provenance-v1-20260608`.

## Input Evidence

- Harness manifest:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/harness_manifest.json`
- Harness report:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/README.md`
- AZJ/EDU pass3a capture:
  `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json`
- Selected-table diagnostic:
  `reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_results.json`
- Existing count-24 bounded-validation artifacts under:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/`

## Required Work

- Re-read the fixed harness manifest and classify which cases can serve as
  same-page scale candidates.
- Capture AZJ metric-local selected page/table/row refs, same-page scale,
  table-local scale, metric source scale fields, and common-scale trace from
  existing no-write artifacts.
- Identify one additional clean same-page candidate from the fixed harness or
  mark `DATA_MISSING` if none exists in current artifacts.
- Keep EDU mixed selected surfaces fail-closed.
- Decide whether two clean cases prove the same source-bound row/page root cause.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, broad backfill, or full ticker-universe
  extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime/model/GPU/service config, schema, or production data.
- Do not edit source PDFs.
- Do not loosen validation gates, infer broad scale, change nearest-$100k
  policy, or expand canonical metrics.
- Do not implement production extraction code unless at least two clean cases
  prove the same source-bound root cause and the change is separately captured
  in a new exact allowlist.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_metric_local_same_page_scale_provenance_v1_20260608.md`
- Registry `list-active --read-only` or `DATA_MISSING`.
- JSON validation for report artifacts.
- `py_compile` for the report-local runner.
- `ruff` for the report-local runner if available.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_metric_local_same_page_scale_provenance_v1_20260608.md --repo-root .`
- Verify no source PDFs are staged.

## Final Report Requirements

Report AZJ provenance, second-candidate decision, EDU fail-closed status,
root-cause decision, any fix made, whether count-24 rerun is justified, whether
count-32 remains blocked, `DATA_MISSING`, unsafe actions avoided, and the exact
next prompt.
