---
job_id: extraction_bank_operating_income_row_ref_collision_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_bank_operating_income_row_ref_collision_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/README.md
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/status.json
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/validation.json
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/diff-check.json
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/red_test.log
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/green_test.log
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/py_compile.log
  - reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616/ruff.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/README.md
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/diff-check.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/green_test.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/live_git_status.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/red_test.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/status.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/validation.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_bank_operating_income_row_ref_collision_v1_20260616
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# Bank Operating Income Row Ref Collision Integration

## Objective

Integrate the stranded post-merge PR #362 review fix commit
`c053cd77250c470af0af7af84764a7dd92fa9d36` into current
`origin/migration/clean-runtime-baseline-reconstruct-v1` through a new PR.

## Scope

- Start from current canonical base
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Apply only the bank `Total operating income` row-ref collision fix and its
  focused regression/report evidence from `c053cd77`.
- Open a new PR against `migration/clean-runtime-baseline-reconstruct-v1`.

## Hard Stops

- Do not run count-24/count-32.
- Do not run broad extraction, random samples, backfill, or canonical writes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schemas, runtime/model/GPU/service config, or production data.
- Do not touch unrelated extraction code.
- Do not merge the new PR.
- Stop if cherry-pick brings files outside this allowlist.

## Validation

- Task-card validate.
- Focused red test from the stranded fix before applying the code change.
- Focused green tests after applying the fix:
  - bank `Total operating income` regression.
  - existing LBL combined `metric_name` row-ref regression.
- `python3 -m py_compile` on `multipass_extraction.py`.
- Targeted `ruff` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`.
- Changed-path and forbidden-boundary guard.
