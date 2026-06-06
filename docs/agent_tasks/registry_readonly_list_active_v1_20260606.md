---
job_id: registry_readonly_list_active_v1_20260606
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/registry_readonly_list_active_v1_20260606
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/registry_readonly_list_active_v1_20260606.md
  - scripts/agent_job_registry.py
  - scripts/test_agent_job_registry.py
  - AGENTS.md
  - .agents/skills/tenn-task-card-registry-safety/SKILL.md
  - reports/agent_jobs/registry_readonly_list_active_v1_20260606/README.md
---

# Registry Read-only List-active v1

## Objective

Add and verify a safe `python3 scripts/agent_job_registry.py list-active
--read-only` mode that inspects active Tenn agent jobs without mutating registry
or report state.

## Scope

- Keep this as Repo Hygiene / Control Plane infrastructure only.
- Start with focused tests for read-only behavior.
- Preserve existing write-capable registry commands.
- Update only directly relevant control-plane docs if implementation changes the
  current guidance.
- Write the closeout report under the allowed output directory.

## Hard Stops

- Stop if the change requires product, backend, frontend, runtime, data,
  extraction, prompt, gold-label, service config, DB, Qdrant, news, memory,
  source PDF, or backfill mutation.
- Stop if the dirty source worktree would need cleanup, reset, stash, rebase,
  merge, deletion, or modification.
- Stop if validation requires dependency installation or broad tests.
- Stop if the staged set expands beyond this task card's allowlist.

## Validation

- Focused registry tests or dependency-free equivalent harness when `pytest` is
  unavailable.
- `python3 scripts/agent_job_registry.py list-active --read-only` against a
  safe non-mutating target.
- Task-card validate/check-diff when available and safe.
- `git diff --check`.
- Final `git status --short --untracked-files=all`.
