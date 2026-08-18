---
job_id: remaining_loose_issue_task_cards_classification_v1_20260527
lane: Reporting
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/remaining_loose_issue_task_cards_classification_v1_20260527.md
  - reports/agent_jobs/remaining_loose_issue_task_cards_classification_v1_20260527/README.md
  - reports/agent_jobs/remaining_loose_issue_task_cards_classification_v1_20260527/status.json
  - reports/agent_jobs/remaining_loose_issue_task_cards_classification_v1_20260527/classification_matrix.md
  - reports/agent_jobs/remaining_loose_issue_task_cards_classification_v1_20260527/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/remaining_loose_issue_task_cards_classification_v1_20260527
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# Remaining Loose Issue Task Cards Classification

Mode detail: audit-only preservation decision for the two issue-control task
cards named by the operator.

## Objective

Classify these target files using current local and read-only GitHub evidence:

- `docs/agent_tasks/github_issue_backlog_audit_v1_20260526.md`
- `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`

## Allowed Scope

- Inspect current branch, HEAD, dirty state, worktrees, registry read-only
  status, target task cards, their report directories, and live GitHub issue
  state.
- Write only this classification task card and report bundle.
- Do not alter the already-preserved target cards or their report artifacts.

## Forbidden

- Product, backend, frontend, runtime, parser, prompt, gold-label, model, GPU,
  service, DB, Qdrant, news, memory, or canonical financial truth mutation.
- GitHub issue, PR, label, milestone, project, comment, or closeout mutation.
- Branch cleanup, merge, rebase, reset, stash, prune, delete, or cherry-pick.
- Unrelated staging or cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/remaining_loose_issue_task_cards_classification_v1_20260527.md`
- `python3 scripts/agent_job_contract.py check-diff --no-write-report docs/agent_tasks/remaining_loose_issue_task_cards_classification_v1_20260527.md`
- JSON parse report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Final `git status --short --branch --untracked-files=all`
