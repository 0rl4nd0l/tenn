---
job_id: issue240_intel_pulse_api_key_current_base_v1_20260627
owner: Codex
lane: Reporting
supporting_lanes:
  - Evaluation
  - Financial Truth
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 240
pr_refs:
  - 435
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue240-intel-pulse-api-key-current-base-v1-20260627
worktree: /home/l4nd0/tenn-issue240-intel-pulse-api-key-current-base-v1-20260627
output_dir: reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627
allowed_files:
  - docs/agent_tasks/issue240_intel_pulse_api_key_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/diff-check.json
  - reports/agent_jobs/issue240_intel_pulse_api_key_current_base_v1_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 240 Intel Pulse API Key Current-Base Replacement

## Objective

Replace stale/conflicting PR #435 with a current-base implementation for issue
#240. Preserve its Intel Pulse and diagnostic matrix route guards, and fix the
review blocker by honoring the existing browser-side `cockpit.apiKey`
localStorage key path.

## Scope

Scope: `safe_extension`

This task may guard only the Pulse/Matrix read routes, update the shared
Cockpit API-client key helper, add focused backend/frontend tests, and document
the final route auth policy.

## Existing Work Classification

- PR #435: `ACTIVE_LINKED` but `DIRTY` / `CONFLICTING`, with green checks on
  stale head and one P2 review finding about stored cockpit API keys.
- Branch `safe/issue240-intel-pulse-route-guard-current-base-v1-20260627`:
  preserve as prior work. Do not patch it in place.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #435 discussion with a link to the
  replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #240 only after live GitHub checks
  are green, no unresolved review blockers remain, canonical containment is
  verified after merge, and a closeout comment records the evidence.

Branch deletion, remote branch deletion, label changes, milestones, project
edits, and cleanup are not authorized.

## Hard Stops

- Do not mutate DB, Qdrant, news stores, memory stores, canonical financial
  truth, extraction outputs, parser prompts, gold labels, runtime services,
  or model/GPU config.
- Do not change Intel Pulse financial/extraction semantics or matrix cell-state
  logic.
- Do not resolve #148 Signals/Memory capability decisions in this task.
- Do not patch stale PR #435 worktrees in place.
- Do not delete branches or worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue240_intel_pulse_api_key_current_base_v1_20260627.md`
- Focused backend route auth tests for Pulse and Matrix.
- Focused frontend API-client tests for env and browser-localStorage API-key
  propagation.
- `ruff` on touched backend files/tests.
- Local frontend test if available; otherwise record missing Vitest/toolchain.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue240_intel_pulse_api_key_current_base_v1_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py validate`
