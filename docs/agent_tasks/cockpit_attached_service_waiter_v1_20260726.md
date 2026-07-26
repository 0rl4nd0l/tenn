---
job_id: cockpit_attached_service_waiter_v1_20260726
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_attached_service_waiter_v1_20260726
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/cockpit_attached_service_waiter_v1_20260726.md
  - scripts/codex_event_waiter.py
  - scripts/test_codex_event_waiter.py
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - .agents/skills/tenn-fix/SKILL.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
---

# Cockpit Attached Service Waiter V1

## Objective

Add a lifecycle-safe attached waiter mode for foreground services such as the
Next.js process launched by `cockpit start new`. The waiter must prove readiness
without treating the healthy long-lived process as a command timeout.

## Owner Authorization

The owner explicitly requested this repair after reviewing the failed canonical
activation. This authorizes the Tier 1 source, test, documentation, commit,
push, and draft-PR work listed above. It does not authorize runtime activation,
service or store mutation, extraction, merge, or deployment.

## Regression Adjudication

- target_identity: canonical `107c926930ef5a14783a8293bac9b47c9046bfed`;
  clean isolated repair worktree
- alleged_old_fix: PR #520 repaired llama executable resolution and remains
  effective
- canonical_lineage: PRs #520 and #521 are ancestors of the repair base
- current_repro: `cockpit start new` reached `Next.js Ready`, then finite
  command mode timed out after 900 seconds and terminated the serving process
  group
- scope_comparison: different
- permanent_gate: add an isolated long-lived fake-service regression
- runtime_functionality_proof: `BROKEN` in the activation report; no runtime
  proof is authorized in this repair
- classification: `NEW_FAILURE_CLASS` with contributing `TEST_GAP`
- next_action: implement the narrow attached-service waiter mode

## Scope

- Add an explicit waiter mode for an attached foreground service.
- Require a shell-free readiness command supplied as an argv vector.
- Write an atomic readiness record while continuing to supervise the service.
- Keep the service attached until it exits or the waiter is interrupted.
- Fail closed if the service exits before readiness or readiness times out.
- Preserve bounded redacted logging and exact process-group cleanup.
- Teach the risk-aware command hook to validate the new invocation shape.
- Document the attached-service operator lifecycle.

## Hard Boundaries

- Do not run `cockpit start new`, open listeners, activate the stack, or touch
  Docker, Redis, Postgres, Qdrant, GPU, models, extraction caches, or protected
  configuration.
- Do not change Cockpit, Compose, llama, model, extraction, or product behavior.
- Do not detach or orphan the service process.
- Do not use a shell or `eval` for either the service or readiness command.
- Do not merge, deploy, mark the PR ready, or mutate unrelated worktrees.

## Required Validation

- Task-card contract validation and Git guard in the isolated worktree.
- RED regression proving finite command mode times out a healthy long-running
  fake service.
- Focused waiter and hook tests.
- Python compilation and changed-file lint.
- Shell-free end-to-end render/probe using only disposable processes and files;
  no listeners.
- `git diff --check` and task-card diff validation.
- Final scope and secret-leak review.

## Definition Of Done

- A fake service can become ready and remain alive under attached supervision.
- Early service exit and readiness timeout fail closed and clean descendants.
- Direct finite-command behavior remains unchanged.
- Spaces and argument boundaries survive without a shell.
- Documentation explains that callers must keep the waiter attached and
  explicitly interrupt it after runtime checks.
- One focused commit is pushed and one draft PR is opened against
  `migration/clean-runtime-baseline-reconstruct-v1`.
