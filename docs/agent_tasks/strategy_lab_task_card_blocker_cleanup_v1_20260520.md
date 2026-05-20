---
job_id: strategy_lab_task_card_blocker_cleanup_v1_20260520
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md
  - docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/diff-check.json
mutation_mode: safe_extension
production_data_access: false
output_dir: reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520
approval_required: false
timeout_seconds: 7200
allow_unapproved_safe_extension: true
---

# Task

Resolve the stale or unrelated untracked Strategy Lab task card that is blocking the ASX fixture-contract integration overlap gate.

# Target Artifact

- `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`

# Scope

This is repo hygiene only. Inspect the task card and its matching report directory, then choose the smallest safe resolution:

- checkpoint/archive if meaningful;
- remove the single stale orphaned task card if clearly justified;
- stop and report if active, contested, or unclear.

Do not touch ASX fixture integration files. Do not touch Strategy Lab source or implementation. Do not touch source code, runtime config, Docker/systemd/env, DBs, Qdrant, news, memory, source registry, model files, parser/extraction, Cockpit UI/source, or broad worktree dirt.

# Required Preflight

Run and report:

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry job only if safe.

# Required Inspection

- Read `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`.
- Search only for `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/`.
- Do not inspect broad source unless the task card points to a report path.

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md`
- `git diff --check`

If committing, run the staged allowlist leak check specified in the request and require no output.

# Required Report

Write:

`reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/README.md`

Include confirmed facts, inferred facts, DATA_MISSING, active registry state, exact status of the Strategy Lab task card, whether the matching report directory exists, chosen resolution option, files changed, validation commands and exact results, final git status, registry release status, commit hash if committed, and next step.
