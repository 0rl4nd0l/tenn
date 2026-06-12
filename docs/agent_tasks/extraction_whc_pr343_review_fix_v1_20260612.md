---
job_id: extraction_whc_pr343_review_fix_v1_20260612
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_pr343_review_fix_v1_20260612.md
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_docling_extract.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/README.md
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/status.json
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/live_git_status.json
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/code_fixer.json
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/validation.json
  - reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_whc_pr343_review_fix_v1_20260612
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
---

# WHC PR #343 Review Fix

## Objective

Apply the two code-review warnings found during PR #343 merge-readiness review:

1. Do not reuse stale openability diagnostics when requested pages differ from
   cached diagnostics.
2. Fail closed when selected-table openability diagnostics contain malformed
   `period_phrases`.

## Hard Stops

- Do not run count-24, count-32, broad extraction, random samples, backfill,
  service routes, or production persistence.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schemas, runtime config, model config, or GPU config.
- Do not use PR #318 as a patch source.
- Do not merge PR #343 or close PR #340.

## Validation

- Task-card validate.
- Registry `list-active --read-only`.
- Focused docling and multipass tests.
- `py_compile` and `ruff` where available.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface path audit.
