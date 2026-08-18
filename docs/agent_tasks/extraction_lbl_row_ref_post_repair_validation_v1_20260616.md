---
job_id: extraction_lbl_row_ref_post_repair_validation_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_lbl_row_ref_post_repair_validation_v1_20260616.md
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/README.md
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/status.json
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/validation.json
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/pr_snapshot.json
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/readiness_decision.json
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/forbidden_path_audit.json
  - reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Extraction LBL Row Ref Post Repair Validation

## Objective

Produce a report-only readiness packet for PR #362 after the bounded LBL
income-statement row-ref repair was committed, pushed, and opened against
`migration/clean-runtime-baseline-reconstruct-v1`.

## Scope

Worktree:
`/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616`.

Branch:
`safe/extraction-lbl-income-row-ref-repair-v1-20260616`.

PR:
`https://github.com/0rl4nd0l/tenn/pull/362`.

Mode: REPORT_ONLY / READINESS DECISION.

## Evidence Inputs

- Repair task card:
  `docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`
- Repair report:
  `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/`
- Repair commit:
  `d16c630af158ce3e5bcb3d7180adb7d3cb23273c`
- PR #362 metadata and current branch state.

## Required Decision

Choose one:

- `A`: PR is ready for review/merge.
- `B`: Need one more focused repair.
- `C`: Need current saved-artifact scorecard after this repair.
- `D`: Need count-24 approval packet refresh.
- `E`: Blocked.

The report may include a secondary recommendation, but the primary decision
must be exactly one of `A`, `B`, `C`, `D`, or `E`.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction or backfill.
- Do not mutate canonical truth, DB, Qdrant, Redis, news, memory, source PDFs,
  prompts, gold labels, schema, runtime/model/GPU config.
- Do not use PR #318.
- Do not clean unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_row_ref_post_repair_validation_v1_20260616.md`
- Registry read-only inspection.
- PR #362 read-only snapshot.
- Repair report JSON validation.
- Replay-summary assertions for target row refs.
- Forbidden-path audit.
- `git diff --check`.
- Task-card `check-diff`.
