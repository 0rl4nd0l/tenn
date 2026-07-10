---
job_id: automation_small_model_routing_v1_20260710
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
approval_required: true
timeout_seconds: 1200
output_dir: reports/agent_jobs/automation_small_model_routing_v1_20260710
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/automation_small_model_routing_v1_20260710.md
  - docs/dev/automation_index.md
  - scripts/codex_automation_runner.py
  - scripts/test_codex_automation_runner.py
  - reports/agent_jobs/automation_small_model_routing_v1_20260710/STATE.md
  - reports/agent_jobs/automation_small_model_routing_v1_20260710/VALIDATION.md
  - reports/agent_jobs/automation_small_model_routing_v1_20260710/diff-check.json
---

# Automation Small Model Routing V1

## Approval

USER_APPROVED: Orlando asked Codex to ensure Tenn automations use a smaller
model when viable.

USER_APPROVED_PUBLISH: After local implementation and validation, Orlando
explicitly approved pushing the task branch and opening draft PR #499. Later
review-fix approval covers updates to that existing PR, but not merge or live
execution-surface mutation.

## Objective

Route low-risk audit/proposal Codex automation jobs to an explicit smaller
model by default, while keeping higher-risk regression scouts on the configured
default model unless an operator explicitly overrides them.

## Scope

- Add automation-runner model policy metadata for each registered job.
- Pass a smaller Codex model for jobs where the work is audit-only and
  proposal-oriented.
- Preserve default model routing for higher-risk extraction and bug-regression
  scouts.
- Document the routing policy and environment overrides.
- Validate reasoning-effort overrides before launching Codex.
- Add focused tests for command construction, policy classification, override
  precedence, blank-value fallback, and invalid reasoning values.

task scope: `control_plane_only`

## Out Of Scope

- No live systemd install, enable, disable, start, stop, restart, reload, or
  unit edit.
- No mutation of runtime, data stores, extraction prompts, source PDFs, gold
  labels, model/GPU runtime config, Docker, or secrets.
- No GitHub issue, label, comment, close/reopen, ready-for-review, or merge
  mutation. Branch push and draft PR #499 publication are explicitly approved.
- No broad automation redesign or changes to automation job prompts beyond
  model routing metadata.

## Model Routing Plan

- Native `automation-health` remains native and spends no Codex model tokens.
- Small-model viable jobs: `repo-hygiene`, `daily-closeout`, `doc-drift`,
  `future-opportunities`, and `memory-drift`.
- Default-model jobs: `extraction-regression` and `bug-regression`, because
  they adjudicate higher-risk financial-truth, parser, route, and regression
  evidence.
- Operators can override all automation model choices with environment
  variables instead of editing timer units.

## Validation Plan

- `python3 scripts/tenn_dev_status.py`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_small_model_routing_v1_20260710.md`
- `python3 -m unittest scripts/test_codex_automation_runner.py`
- `python3 scripts/codex_automation_runner.py list`
- `python3 scripts/codex_automation_runner.py repo-hygiene --dry-run`
- `python3 scripts/codex_automation_runner.py extraction-regression --dry-run`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_small_model_routing_v1_20260710.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_small_model_routing_v1_20260710.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_small_model_routing_v1_20260710.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_small_model_routing_v1_20260710.md`
- `git diff --check`
- `git status --short --untracked-files=all`
