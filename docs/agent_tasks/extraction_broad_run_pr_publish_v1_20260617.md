---
job_id: extraction_broad_run_pr_publish_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_run_pr_publish_v1_20260617.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/GUARD.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/VALIDATION.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/PR_BODY.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/publication.json
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/validation.json
  - reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_broad_run_pr_publish_v1_20260617
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Broad-Run PR Publish

## Objective

Publish the reviewed local branch
`safe/extraction-broad-run-provenance-risk-flags-v1-20260617` and open a draft
PR against `migration/clean-runtime-baseline-reconstruct-v1`.

User approval: Orlando replied `proceed` after the prior report requested
explicit approval to push and open a PR.

## Hard Stops

- Do not merge the PR.
- Do not use PR #318.
- Do not run count-24, count-32, random samples, broad extraction, broad
  backfill, full ticker-universe extraction, or runtime services.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, model/GPU/service config, or production data.
- Do not retarget the PR away from
  `migration/clean-runtime-baseline-reconstruct-v1`.

## Required Output

- Guard, state, decisions, validation, PR body, next-goal notes, and
  machine-readable publication metadata.

## Validation

- Re-run guard checks before GitHub mutation.
- Validate this task card and check its local diff/report contract.
- Push the branch with tracking.
- Open a draft PR with the committed `PR_BODY.md`.
