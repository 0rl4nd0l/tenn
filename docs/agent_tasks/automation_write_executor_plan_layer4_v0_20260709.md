---
job_id: automation_write_executor_plan_layer4_v0_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_write_executor_plan_layer4_v0_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
stacked_on_pr: 494
allowed_files:
  - docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md
  - scripts/automation_write_executor_plan.py
  - scripts/test_automation_write_executor_plan.py
  - reports/agent_jobs/automation_write_executor_plan_layer4_v0_20260709/README.md
  - reports/agent_jobs/automation_write_executor_plan_layer4_v0_20260709/STATE.md
  - reports/agent_jobs/automation_write_executor_plan_layer4_v0_20260709/VALIDATION.md
  - reports/agent_jobs/automation_write_executor_plan_layer4_v0_20260709/diff-check.json
---

# Automation Write Executor Plan Layer 4 V0

## Approval

USER_APPROVED: Orlando approved continuing the automation backlog stack after
PR #494 passed checks.

## Objective

Add a dry-run executor-plan helper for strict write-gate manifests. The helper
should consume the Layer 3 manifest, refuse unsafe or unapproved manifests, and
render the exact future command plan an owner or later executor would review
before any GitHub, git, host-state, runtime, timer, or data write happens.

## Scope

- Add a stdlib `scripts/automation_write_executor_plan.py` helper.
- Accept manifest JSON from inline input or a file.
- Return machine-readable JSON only when `--json` is passed.
- Preserve `read_only: true` and mark every generated command with
  `execute: false`.
- Support dry-run plans for:
  - `open_issue`
  - `comment_existing_issue`
  - `comment_existing_pr`
  - `create_draft_pr`
  - `park_high_risk`
  - `review_only`
- Fail closed when manifest `read_only` is false, `may_execute` is false,
  required targets are missing, command surfaces are unknown, or the action type
  is unsupported.
- Add focused tests using inline JSON and temp files only.

## Out Of Scope

- No GitHub writes by this helper: no issue create/edit/comment/close, PR
  create/edit/comment/merge, label mutation, branch mutation, workflow
  dispatch, or API mutation.
- No git writes by this helper: no branch creation, worktree creation, commit,
  push, merge, rebase, cherry-pick, reset, stash, prune, or cleanup.
- No writes to `~/.codex/automations/tenn/state/candidates.jsonl` during this
  implementation or validation.
- No automation-runner prompt changes.
- No systemd timer/service install, daemon reload, enable/start/stop/restart,
  or live automation mutation.
- No DB, Qdrant, Redis, news-store, memory-store, source-PDF, gold-label,
  extraction prompt, backfill, Docker, service, model/GPU, or secret mutation.
- No actual high-risk branch or worktree creation.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
- initial red test: `python3 -m unittest scripts.test_automation_write_executor_plan`
- green tests: `python3 -m unittest scripts.test_automation_write_executor_plan scripts.test_automation_write_gate scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
- `python3 scripts/automation_write_executor_plan.py --help`
- `python3 scripts/automation_write_executor_plan.py plan --manifest-json '{"read_only":true,"status":"eligible","may_execute":true,"action":{"type":"open_issue","target":{"title":"Safe","body_source":"reports/demo.md","lane":"reporting","risk":"low","root_cause":"safe gap"}}}' --json`
- `python3 -m py_compile scripts/automation_write_executor_plan.py scripts/test_automation_write_executor_plan.py`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
