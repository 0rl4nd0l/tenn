# Untracked Task-Card Preservation Classification

Job: `untracked_task_card_preservation_classification_v1_20260526`

GitHub issue: #94 - https://github.com/0rl4nd0l/tenn/issues/94

Result: `PASS_CLASSIFICATION_COMPLETE`

## Session Declaration

- Agent: Codex
- Lane: Repo Hygiene requested; validator lane `Evaluation`
- Supporting lanes: Reporting, Evaluation
- Execution mode: audit-first preservation classification
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- HEAD: `61723bdca4ea30ce404d606cec63e47b9cb739b3`
- Contested surfaces touched: none
- Collision risk: LOW
- Decision: proceed with report-only classification

## Scope

Issue #94 asked for classification of two persistent unrelated untracked task cards:

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

The audit also recorded the current out-of-scope dirty task card:

- `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`

That file is not one of the two #94 target artifacts and was left untouched.

## Classification

Both #94 target task cards are valid uncommitted artifacts to commit.

The matching report bundles exist locally, the target task cards validate, and the files are not tracked by git. The correct next action is not cleanup. The correct next action is a separate scoped preservation task that stages and commits the two task cards plus their existing report bundles, using `git add -f` for ignored `reports/` files after a fresh validation pass.

## Per-File Findings

### A2M Backend Reload News Status Activation Smoke

Path: `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`

Classification: `valid uncommitted artifact to commit`

Evidence:

- The task card validates with `python3 scripts/agent_job_contract.py validate`.
- The matching report bundle exists at `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/`.
- The report records `runtime_smoke_complete` with JSON validation pass, task-card validation pass, `git diff --check` pass, and `check-diff` pass.
- The card itself is untracked and is not returned by `git ls-files`.
- Exact GitHub issue/PR searches for `a2m_backend_reload_news_status_activation_smoke` returned no issue or PR.
- Adjacent follow-up work is already covered elsewhere, including #83, #84, and #87. Those trackers cover downstream findings, not preservation of this task-card artifact.

Recommended next action:

Create a scoped artifact-preservation task and commit this task card together with its existing report bundle. Use `git add -f reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/` because `reports/` is ignored. Do not delete, stash, reset, move, or rewrite the task card.

### Automation Audit Issue Preservation

Path: `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

Classification: `valid uncommitted artifact to commit`

Evidence:

- The task card validates with `python3 scripts/agent_job_contract.py validate`.
- The matching report bundle exists at `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/`.
- The report preserved four issue drafts without GitHub mutation.
- The underlying actionable findings are now represented by GitHub issues #79, #80, #81, #82, and #85.
- The card itself is untracked and is not returned by `git ls-files`.
- Exact GitHub issue/PR searches for `automation_audit_issue_preservation` returned no issue or PR.

Recommended next action:

Create the same scoped artifact-preservation task and commit this task card together with its existing report bundle. Use `git add -f reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/` because `reports/` is ignored. Do not delete, stash, reset, move, or rewrite the task card.

## Duplicate Search Summary

The exact artifact names had no issue or PR duplicates:

- `a2m_backend_reload_news_status_activation_smoke`: no issue, no PR
- `automation_audit_issue_preservation`: no issue, no PR

Adjacent issue coverage found:

- #79 `[Ops] Automation topology reconciliation audit v1` - open
- #80 `[Repo Hygiene] Registry read-only no-lock list-active mode v1` - closed
- #81 `[Ops/News] Nightly news cron observability and systemd migration audit v1` - open
- #82 `[Runtime] llama-server :8001 ownership/provenance audit v1` - open
- #83 `[Query] News projection materialization/parity repair planning v1` - open
- #84 `[Provenance] Audit missing cockpit_announcement_context runtime schema` - open
- #85 `[Repo Hygiene] Integrate registry read-only no-lock list-active fix` - open
- #87 `[Query Orchestration] A2M recall chat answer lacks required visible evidence` - open
- #94 is the live tracker for this exact two-card preservation classification

Closed adjacent hygiene issues #64, #69, and #75 are broader prior repo-hygiene/result-review work and do not preserve these two exact files.

## Data Missing

`DATA_MISSING`: No committed artifact-preservation task currently exists for these two exact task cards and their report bundles.

No DATA_MISSING remains for the classification itself.

## Forbidden Mutation Attestation

- No product/backend/frontend/runtime files were changed.
- No DB, Qdrant, news, memory, or canonical financial truth was mutated.
- No parser routing, extraction prompts, gold labels, runtime/model/GPU/service config, branch, stash, reset, merge, rebase, prune, or PR operation was performed.
- The two target task cards were read-only inspected and not edited.
- No GitHub issues were created, closed, or edited.

## Final Recommendation

Run one narrow follow-up preservation task:

`untracked_task_card_artifact_preservation_commit_v1_20260526`

Allowed files should be limited to:

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/**`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/**`
- its own task card and report bundle

The follow-up should fresh-validate both task cards, fresh-check git status and registry overlap, use `git add -f` for ignored report bundles, and commit only if the diff remains exactly scoped.
