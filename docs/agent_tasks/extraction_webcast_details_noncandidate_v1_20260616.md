---
job_id: extraction_webcast_details_noncandidate_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_webcast_details_noncandidate_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/README.md
  - reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/status.json
  - reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/validation.json
  - reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
---

# Webcast Details Noncandidate Guard

## Objective

Add one narrow #96 source-document policy guard for webcast-details
announcements that currently look like half-year results candidates because
their title includes `half-year results`.

## Source Evidence

The scale-table provenance harness records NIC
`50398d3d-27f7-4d9e-8a26-a2d69f128a1c` as a document-family policy gap:

- Title/source path: `2025-08-11_half-year-results-webcast-details_...pdf`
- Forbidden output: `webcast-details title promoted to financial report without
  exact source review`
- Root cause group: `document_family_policy_gap`

On fresh origin baseline
`4cfecaa74ddb8a0f1604877ead837cbdfb48c3a1`,
`classify_source_document("half-year-results-webcast-details.pdf", ...)`
returns `financial_report` with reason `half_year_source_phrase`.

## Allowed Repair Shape

- Add a red regression proving `half-year-results-webcast-details.pdf` is
  blocked as `source_noncandidate:webcast_details_notice`.
- Preserve valid `half-year-results.pdf` financial-report candidate behavior.
- Add the new noncandidate class to source-document contract docs.
- Do not inspect or mutate source PDFs.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, backfill, or
  full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime state, model/GPU config, or production data.
- Do not broaden the rule to generic financial `results` or presentation titles.

## Validation

- Task-card validate.
- Registry read-only check.
- Focused source-document classifier pytest.
- `py_compile` for `multipass_extraction.py`.
- `ruff` for modified code/tests.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.

## Final Report Requirements

Report source evidence, exact files changed, red/green validation, unsafe
actions avoided, and PR status.
