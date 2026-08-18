---
job_id: extraction_results_meeting_noncandidate_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_results_meeting_noncandidate_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/README.md
  - reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/status.json
  - reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/validation.json
  - reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
---

# Results Of Meeting Noncandidate Guard

## Objective

Add one narrow #96 source-noncandidate extraction guard for title-only
`results of meeting` documents.

## Source Evidence

Issue #96 has a current status comment saying `MQR results-of-meeting is fixed
locally but not yet in origin/migration`. Live origin baseline still returns
`None` from `_detect_source_noncandidate_class("Results of Meeting", "")`.

Existing candidate-exclusion reports already use
`meeting_or_proxy_notice` for meeting/proxy material:

- `reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/`
- `reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/`

## Allowed Repair Shape

- Add a focused regression that title-only `results-of-meeting.pdf` is blocked
  as `source_noncandidate:meeting_or_proxy_notice`.
- Add a control proving financial reporting titles such as `half-year-results`
  remain candidates.
- Extend only the deterministic source-noncandidate classifier.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, backfill, or
  full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime state, model/GPU config, or production data.
- Do not broaden the rule to generic financial `results` titles.

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
