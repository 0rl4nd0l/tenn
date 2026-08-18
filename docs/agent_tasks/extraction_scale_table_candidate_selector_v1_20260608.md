---
job_id: extraction_scale_table_candidate_selector_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_scale_table_candidate_selector_v1_20260608.md
  - reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/README.md
  - reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/selection.json
  - reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/status.json
  - reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/validation.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# Scale Table Candidate Selector

## Objective

Build a report-only fixed-harness candidate selector for scale-table
provenance cases. Use only existing fixed harness artifacts, count summaries,
and prior exact-doc replay artifacts. Rank exact documents where scale or
provenance evidence still shows a concrete mismatch or `DATA_MISSING`.
Recommend at most one suspect document plus one clean control for a future
isolated-cache pass3a replay. If no suspect exists, recommend closing the
scale-table repair path.

## Scope

Mode: AUDIT_ONLY and REPORT_LOCAL.

Inputs are read-only:

- Existing count-24 approval and bounded-validation summaries.
- Existing count-24 failure taxonomy and regression-consolidation artifacts.
- Existing scale-table source evidence and selected-table provenance reports.
- Existing AZJ/EDU pass3a provenance capture artifacts.
- Existing CXO/NSR pass3a replay artifacts.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not run production repair.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, normal parser caches, services,
  model/GPU config, or production data.
- Do not create, edit, label, comment on, close, or reopen GitHub issues.
- Do not clean, stash, reset, merge, rebase, cherry-pick, delete branches, or
  delete unrelated dirt.

## Required Output

- Evidence inventory with exact artifact paths used.
- Ranked exact-document candidate list with mismatch or `DATA_MISSING`
  reasons.
- At most one suspect document recommendation.
- One clean control recommendation if available.
- Decision on whether to close the scale-table repair path.
- Static validation evidence and explicit no-sample/backfill statement.
