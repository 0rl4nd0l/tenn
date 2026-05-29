---
job_id: extraction_bhp_eval_draft_pr_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_bhp_eval_draft_pr_v1_20260529.md
  - reports/agent_jobs/extraction_bhp_eval_draft_pr_v1_20260529/README.md
  - reports/agent_jobs/extraction_bhp_eval_draft_pr_v1_20260529/status.json
  - reports/agent_jobs/extraction_bhp_eval_draft_pr_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_bhp_eval_draft_pr_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: draft_pr_create_only
related_issue: 96
---

# Extraction BHP Eval Draft PR V1

## Objective

Create a draft PR for the already-published branch
`safe/extraction-bhp-canary-gold-fixture-v1-20260529`, targeting
`migration/clean-runtime-baseline-reconstruct-v1`, so the BHP canary
real-gold fixture and source-path validation fix have a visible review surface.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`.
- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- GitHub mutation allowed: draft PR creation only.

## Contract Check

Target system layer: Evaluation/Provenance review visibility for
already-validated test/report artifacts. This task does not invoke extraction,
storage, retrieval, or analysis.

Relevant contract rules: source-backed financial truth remains evaluation-only;
no canonical financial truth can be promoted by opening a draft PR; backend
source-of-truth and pipeline invariants remain untouched.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
routing, extraction prompts, runtime/model/GPU/service config, schemas, Cockpit
UI, issue state, issue comments, labels, milestones, and non-draft PR state.

Why safe: this task creates only a draft PR from an already-pushed branch after
verifying no existing PR for the branch. It does not merge the branch, mutate
issue #96, or claim graduation.

GPU process check required: no. This task must not start, restart, or depend on
`llama-server` and must not run live extraction jobs.

## Hard Stops

- Do not create a ready-for-review PR.
- Do not comment on, close, label, or edit GitHub issues.
- Do not merge the PR.
- Do not push, reset, or force-push the live baseline branch.
- Do not run canary, extraction, or backfill.
- Do not mutate production DB, Qdrant, news, memory, or source PDFs.

## Required Behavior

- Validate and claim this task card.
- Confirm no existing PR exists for this head branch.
- Create one draft PR targeting `migration/clean-runtime-baseline-reconstruct-v1`.
- Record PR URL/number and final local/remote branch heads in the report.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_bhp_eval_draft_pr_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_bhp_eval_draft_pr_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_bhp_eval_draft_pr_v1_20260529.md --repo-root .`
- `gh pr list --state all --head safe/extraction-bhp-canary-gold-fixture-v1-20260529`
- `gh pr create --draft --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/extraction-bhp-canary-gold-fixture-v1-20260529`
- `gh pr view <number> --json number,title,state,isDraft,headRefName,baseRefName,url`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_bhp_eval_draft_pr_v1_20260529.md --repo-root .`
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, local head, remote head, PR URL/number, worktree, task card,
validation commands and results, confirmation that no issue/runtime/datastore
mutation occurred, and remaining #96 blocker.
