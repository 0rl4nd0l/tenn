---
job_id: nvme_runtime_audit_artifact_checkpoint_v1_20260519
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md
  - docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
  - docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
  - docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
  - docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md
  - docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/
  - reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/
  - reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/
  - reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/
  - reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/README.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/status.json
  - reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/README.md
  - reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/cockpit_reboot_full.log
  - reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/cockpit_start_new_detached.log
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/README.md
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/README.md
  - reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/README.md
  - reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/README.md
  - reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/status.json
  - reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Preserve recent NVMe/runtime/route/Home/APEX audit task cards and report artifacts in the clean NVMe runtime baseline so future Codex jobs are not blocked by unrelated untracked audit cards.

# Scope

This is an artifact-only checkpoint. It may create this task card, verify the listed audit task cards and report directories, write the checkpoint report, force-add only the listed ignored report directories, and commit only those task/report artifacts if the staged diff contains no source, runtime, or data files.

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git status --short --ignored docs/agent_tasks reports/agent_jobs`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md`
- registry/list-active if supported
- registry/check-overlap if supported

# Allowed work

- Create this checkpoint task card.
- Verify each listed task card and report directory exists.
- Write the checkpoint report under `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/README.md`.
- Stage only the allowed task cards and report artifacts.
- Use force-add only for the specific allowed report directories because `reports/` is ignored.
- Commit only this artifact checkpoint if and only if the staged diff contains no source/runtime/data files.

# Hard stops

Stop if:

- any staged file is outside the allowed list;
- `git status` shows source-code changes in this worktree beyond the known task/report artifacts;
- registry shows active overlapping Evaluation/Runtime/Reporting checkpoint work;
- reports cannot be force-added without pulling in unrelated report directories;
- commit would include source/runtime/data changes;
- task-card validation fails.

# Validation

Run and report:

- `git diff --cached --name-status`
- `git diff --cached --stat`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md`
- `git status --short` after commit
- registry release if claimed

# Required report

Write `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/README.md` including:

- Confirmed facts
- DATA_MISSING
- exact artifacts preserved
- whether reports were force-added
- commit hash if committed
- final git status
- registry status
- Project Memory save recommendation
