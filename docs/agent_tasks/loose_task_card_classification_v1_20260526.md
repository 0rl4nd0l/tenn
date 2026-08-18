---
job_id: loose_task_card_classification_v1_20260526
lane: Reporting
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/loose_task_card_classification_v1_20260526.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md
  - reports/agent_jobs/loose_task_card_classification_v1_20260526/README.md
  - reports/agent_jobs/loose_task_card_classification_v1_20260526/status.json
  - reports/agent_jobs/loose_task_card_classification_v1_20260526/classification_matrix.md
  - reports/agent_jobs/loose_task_card_classification_v1_20260526/diff-check.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/README.md
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/status.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/duplicate_search_matrix.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/created_issues.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/skipped_items.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/loose_task_card_classification_v1_20260526
mutation_mode: audit_only
production_data_access: false
---

# Loose Task Card Classification

Mode detail: audit-only preservation decision for remaining task-card artifacts.

## Objective

Classify the two named task cards and decide whether any loose artifact should be
preserved before issue-resolution work continues:

- `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`
- `docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md`

## Allowed Scope

- Inspect branch, HEAD, dirty status, registry read-only status, target task
  cards, referenced reports, and read-only GitHub issue evidence.
- Generate the classification report bundle.
- Preserve only the proven durable evidence bundle for completed task-card work.

## Forbidden

- Product, backend, frontend, runtime, parser, prompt, gold-label, model, GPU,
  service, DB, Qdrant, news, memory, or canonical financial truth mutation.
- GitHub issue or PR mutation.
- Branch cleanup, merge, rebase, reset, stash, prune, or delete.
- Unrelated dirty-file cleanup.

## Validation

- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/loose_task_card_classification_v1_20260526.md`
- JSON parse report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/loose_task_card_classification_v1_20260526.md`

## Hard Stops

- Active registry overlap with the target files.
- Evidence that either task card would create duplicate GitHub work.
- Any required action outside the allowed files or forbidden surfaces.
