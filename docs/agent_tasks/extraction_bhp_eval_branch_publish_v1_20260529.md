---
job_id: extraction_bhp_eval_branch_publish_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_bhp_eval_branch_publish_v1_20260529.md
  - reports/agent_jobs/extraction_bhp_eval_branch_publish_v1_20260529/README.md
  - reports/agent_jobs/extraction_bhp_eval_branch_publish_v1_20260529/status.json
  - reports/agent_jobs/extraction_bhp_eval_branch_publish_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_bhp_eval_branch_publish_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: branch_push_only
related_issue: 96
---

# Extraction BHP Eval Branch Publish V1

## Objective

Publish the local evaluation branch
`safe/extraction-bhp-canary-gold-fixture-v1-20260529` to `origin` so the BHP
canary real-gold fixture and real-gold source-path validation fix are durable
outside the local worktree.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Mode: SAFE EXTENSION.
- Worktree: `/home/l4nd0/tenn-extraction-bhp-canary-gold-fixture-v1-20260529`.
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`.
- GitHub mutation allowed: branch push only.

## Contract Check

Target system layer: Evaluation/Provenance publication of already-validated
test/report artifacts. This task does not invoke extraction, storage,
retrieval, or analysis.

Relevant contract rules: source-backed financial truth remains evaluation-only;
no canonical financial truth can be promoted by publishing a branch; backend
source-of-truth and pipeline invariants remain untouched.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
routing, extraction prompts, runtime/model/GPU/service config, schemas, Cockpit
UI, issue state, issue comments, labels, milestones, and PRs.

Why safe: this task pushes only the existing isolated branch after validating
that the worktree is clean and task-card/report files are in scope. It does not
merge into the live baseline and does not claim #96 completion.

GPU process check required: no. This task must not start, restart, or depend on
`llama-server` and must not run live extraction jobs.

## Hard Stops

- Do not open a PR.
- Do not comment on, close, label, or edit GitHub issues.
- Do not push the live baseline branch.
- Do not force-push.
- Do not run canary, extraction, or backfill.
- Do not mutate production DB, Qdrant, news, memory, or source PDFs.

## Required Behavior

- Validate and claim this task card.
- Confirm the branch has no uncommitted product/eval changes before pushing.
- Push only `safe/extraction-bhp-canary-gold-fixture-v1-20260529` to origin.
- Record the final local and remote head in the report.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_bhp_eval_branch_publish_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_bhp_eval_branch_publish_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_bhp_eval_branch_publish_v1_20260529.md --repo-root .`
- `git status --short --branch`
- `git push -u origin safe/extraction-bhp-canary-gold-fixture-v1-20260529`
- `git ls-remote origin refs/heads/safe/extraction-bhp-canary-gold-fixture-v1-20260529`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_bhp_eval_branch_publish_v1_20260529.md --repo-root .`
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, local head, remote head, worktree, task card, validation commands
and results, files changed, confirmation that no PR/issue/runtime/datastore
mutation occurred, and remaining #96 blocker.
