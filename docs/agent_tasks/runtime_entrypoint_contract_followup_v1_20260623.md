---
job_id: runtime_entrypoint_contract_followup_v1_20260623
title: Runtime entrypoint contract follow-up
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/runtime_entrypoint_contract_followup_v1_20260623
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/runtime_entrypoint_contract_followup_v1_20260623.md
  - docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md
  - scripts/runtime_entrypoint_contract.py
  - scripts/test_runtime_entrypoint_contract.py
  - agent_contract.json
  - docs/entrypoints.md
  - docs/startup.md
  - reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/STATE.md
  - reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/VALIDATION.md
  - reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/PR_REVIEW.md
  - reports/agent_jobs/runtime_entrypoint_contract_followup_v1_20260623/STATE.md
  - reports/agent_jobs/runtime_entrypoint_contract_followup_v1_20260623/VALIDATION.md
  - reports/agent_jobs/runtime_entrypoint_contract_followup_v1_20260623/PR_REVIEW.md
  - reports/agent_jobs/runtime_entrypoint_contract_followup_v1_20260623/diff-check.json
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/entrypoints.md
  - docs/startup.md
docs_changed:
  - docs/entrypoints.md
  - docs/startup.md
docs_followup: NONE
reason: "Post-merge Scout B review found runtime contract validation and startup doc gaps after PR #389."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused control-plane contract/docs repair after subagent review."
worker_model_allowed: false
worker_decision_limit: "not_applicable"
escalation_needed: false
---

# Runtime Entrypoint Contract Follow-up

## Objective

Address post-merge review findings from PR #389:

- make runtime docs validation assert actual contract values, not only broad
  headings;
- replace the stale `/home/l4nd0/tenn/scripts/cockpit` startup symlink command;
- document the Full-Stack Cockpit Mode host llama.cpp side effect;
- make the merged #389 task card closeout self-check pass explicitly as
  control-plane-only work.

## Scope

Control-plane contract code, tests, docs, task-card metadata, and report
artifacts only.

## Forbidden

- No product runtime, DB, Qdrant, Redis, news, memory, source-PDF, gold-label,
  model, GPU, systemd host, Docker host, cron, `.env`, dependency lockfile, CI,
  production venv, or host-global changes.

## Required Validation

- `python3 scripts/runtime_entrypoint_contract.py --check`
- `python3 scripts/test_runtime_entrypoint_contract.py`
- `python3 -m py_compile scripts/runtime_entrypoint_contract.py`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/runtime_entrypoint_contract_followup_v1_20260623.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/runtime_entrypoint_contract_followup_v1_20260623.md --repo-root .`
- `git diff --check`

## Done Criteria

- Runtime docs validation fails when contract values are missing.
- Startup docs use a repo-root-relative cockpit symlink command.
- Full-Stack Cockpit Mode docs and machine contract name host llama.cpp side
  effects.
- The merged #389 task card closeout/report checks pass on current canonical.
