---
job_id: extraction_broad_run_pr_readiness_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_run_pr_readiness_v1_20260617.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/GUARD.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/VALIDATION.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/PR_REVIEW.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/validation.json
  - reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_broad_run_pr_readiness_v1_20260617
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# Extraction Broad-Run PR Readiness

## Objective

Run a local PR-readiness gate for the current three-commit branch:

- `deba6e0b` source/test/report implementation
- `a0b54e66` saved LBL artifact replay
- `4f58d1b7` positive synthetic risk fixture

## Hard Stops

- Do not push or open a PR under this task card.
- Do not run count-24, count-32, broad extraction, broad backfill, random
  samples, full ticker-universe extraction, or runtime services.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, model/GPU/service config, production data, GitHub, or
  remote branches.

## Required Output

- Guard, state, decisions, validation, PR review, and next-goal notes.
- Local review decision for owner approval.

## Validation

- Validate the three implementation task cards and this task card.
- Check report artifacts for the three implementation report bundles.
- Run focused code validation for `broad_extraction_test.py` and
  `test_broad_extraction_test.py`.
- Check branch diff whitespace against
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
