---
job_id: agent_contract_registry_mainline_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/agent_contract_registry_mainline_v1_20260607.md
  - scripts/agent_job_contract.py
  - scripts/agent_job_registry.py
  - scripts/test_agent_job_contract.py
  - scripts/test_agent_job_registry.py
  - reports/agent_jobs/agent_contract_registry_mainline_v1_20260607/README.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/agent_contract_registry_mainline_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Restore Tenn task-card validation and safe read-only active-job registry
inspection on current `origin/main`.

# Background

Clean mainline worktrees currently report `DATA_MISSING` for task-card
validation because `scripts/agent_job_contract.py` is absent. Current reports
also still flag `scripts/agent_job_registry.py list-active --read-only` as
missing or unsafe, even though older branch work proved a no-lock/no-write
implementation in a different baseline.

# Required Behavior

- Add repo-local task-card validation tooling that can validate current main
  task cards and support strict allowed-file diff checks.
- Add `list-active --read-only` so read-only registry inspection:
  - does not acquire a registry lock,
  - does not create the registry root when it is absent,
  - does not create `.lock` or `owner.json`,
  - does not write report/status artifacts,
  - returns explicit `read_only` and `lock_acquired` fields.
- Preserve lock-writing behavior for explicit mutating registry operations such
  as claim, heartbeat, release, and overlap checks.
- Keep production-data access explicit in task-card metadata instead of forcing
  degraded or misleading validation outcomes.

# Hard Boundaries

- Do not edit product runtime, Cockpit, news, extraction, parser, Qdrant,
  Redis, DB, source PDF, model/GPU, service, cron, timer, or GitHub issue
  surfaces.
- Do not clean, reset, stash, overwrite, or absorb unrelated dirty work from
  the live checkout.
- Do not run lock-writing registry commands against the live shared checkout.

# Required Validation

- Validate this task card with the restored validator.
- Run focused contract and registry tests.
- Prove `list-active --read-only` is no-lock/no-write in a temporary git repo
  where the registry root is missing and in a temporary git repo where active
  records already exist.
- Run `check-diff --no-write-report` for this task card.
- Run `git diff --check`.

# Definition Of Done

Mainline branches should no longer need to report `DATA_MISSING` for task-card
validation or read-only active-job inspection. Any remaining registry mutation
commands must remain explicit, lock-writing, and outside read-only audit paths.
