---
job_id: dirty_task_card_classification_for_mcp_unblock_20260507
lane: Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/dirty_task_card_classification_for_mcp_unblock_20260507
allowed_files:
  - docs/agent_tasks/dirty_task_card_classification_for_mcp_unblock_20260507.md
  - reports/agent_jobs/dirty_task_card_classification_for_mcp_unblock_20260507/README.md
  - docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md
  - docs/agent_tasks/marketplace_matches_workflow_audit_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_preserve_merge_back_v1.md
  - docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md
---

# Task

Audit the dirty/untracked task-card files blocking the Tenn Agent MCP scaffold. Report ownership, likely status, validation results, registry overlap, and safest next step.

# Allowed writes

- This task card.
- Final report at `reports/agent_jobs/dirty_task_card_classification_for_mcp_unblock_20260507/README.md`.

# Allowed reads

- The four dirty/untracked task cards listed in `allowed_files`.
- Relevant registry/task-card/hook docs/scripts.
- Relevant recent commits/logs for these task-card names or job IDs.

# Not allowed

- Do not implement the MCP scaffold.
- Do not create `tools/tenn_agent_mcp/`.
- Do not commit.
- Do not move/delete task cards.
- Do not edit existing task-card content except this task card if format adaptation is required.
- Do not touch backend/Cockpit/runtime/financial truth/Qdrant/news/company memory/market memory/extraction/gold labels.
- Do not access production data.

# Final report

Write:

`reports/agent_jobs/dirty_task_card_classification_for_mcp_unblock_20260507/README.md`

If the repo requires additional task-card fields, adapt minimally and report the adaptation.

## Required preflight

Run and report:

- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `python3 scripts/agent_job_registry.py list-active --repo-root "$(pwd)" || true`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dirty_task_card_classification_for_mcp_unblock_20260507.md || true`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/dirty_task_card_classification_for_mcp_unblock_20260507.md --repo-root "$(pwd)" || true`

If exact commands differ, inspect script help and use the correct repo-supported form.

Hard stop:
If an active registry job currently owns any of the dirty task-card files, stop and report only.

## Inspect these task cards

Classify each file:

- `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md`
- `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md`
- `docs/agent_tasks/query_legacy_chat_envelope_preserve_merge_back_v1.md`
- `docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md`

For each, report:

- exists? yes/no
- git status: untracked/modified/etc.
- task-card validates? yes/no, exact command/result
- job_id
- lane
- mutation_mode
- output_dir
- allowed_files summary
- likely owner/workstream
- related report directory exists? yes/no
- related commit/report evidence found? yes/no
- appears completed / pending / stale / active / DATA_MISSING
- safe preservation recommendation:
  - commit as pending task-card checkpoint
  - keep untracked for active local job
  - archive/move later after user approval
  - delete later after user approval
  - DATA_MISSING

Do not change the files.

## Check recent evidence

Search recent commits/logs for each task-card basename and job_id.

Use safe read-only commands such as:

- `git log --oneline --all -- docs/agent_tasks/<file>`
- `git log --oneline --all --grep '<job_id>'`
- `rg '<job_id>|<task-card basename>' reports docs scripts . || true`

Avoid huge raw searches if unnecessary. Summarize relevant hits only.

## Required final report

Write:

`reports/agent_jobs/dirty_task_card_classification_for_mcp_unblock_20260507/README.md`

Include:

- Summary
- Confirmed facts
- Inferred facts
- DATA_MISSING
- Repo preflight
- branch
- HEAD
- git status before/after
- worktrees
- registry/list-active
- Blocking files table
- Effect on MCP scaffold
- Recommended next action
- Validation run
- Files changed
- Final worktree status

The blocking files table must include these columns:

- path
- status
- validates?
- lane
- mutation_mode
- likely workstream
- report evidence
- recommended disposition
- rationale

State whether the MCP scaffold can safely be rerun now, or what still blocks it.

Choose one recommended next action:

- Safe checkpoint commit prompt recommended
- Manual user review required
- Separate active job should complete first
- Stale task cards can be archived later with approval
- DATA_MISSING

Validation run must list every command and exact pass/fail result.

Files changed should be only:

- this task card
- this report

Final worktree status must include:

- `git status --short`
- `git diff --check`
