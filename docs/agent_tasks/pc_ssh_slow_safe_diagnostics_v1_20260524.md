---
job_id: pc_ssh_slow_safe_diagnostics_v1_20260524
title: PC and SSH slow safe diagnostics
owner: Codex
lane: Evaluation
supporting_lanes:
  - Runtime/Ops
  - Repo Hygiene
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/pc_ssh_slow_safe_diagnostics_v1_20260524
allowed_files:
  - docs/agent_tasks/pc_ssh_slow_safe_diagnostics_v1_20260524.md
  - reports/agent_jobs/pc_ssh_slow_safe_diagnostics_v1_20260524/**
forbidden:
  - source_code_edits
  - git_commits_without_explicit_hygiene_approval
  - docker_volume_prune
  - docker_system_prune_all
  - model_deletion
  - worktree_deletion
  - rm_rf
  - db_mutation
  - qdrant_mutation
  - news_mutation
  - memory_mutation
  - service_restarts_without_explicit_safe_process_evidence
  - gpu_runtime_config_edits
  - cron_or_systemd_changes
---

# PC and SSH Slow Safe Diagnostics

## Objective

Diagnose current PC and SSH slowness on the live Tenn host with bounded, read-only system diagnostics and produce a clear report of bottlenecks, safe next actions, and unsafe actions avoided.

## Mode

`AUDIT / SAFE OPS DIAGNOSTICS ONLY`

Allowed writes are limited to this task card and:

- `reports/agent_jobs/pc_ssh_slow_safe_diagnostics_v1_20260524/`

## Scope

Collect current-turn evidence for CPU, RAM, swap, disk usage, disk I/O wait, Docker/container load, llama/GPU pressure, SSH/network latency, file watcher or Cursor pressure, Codex/dev-job pressure, and kernel/system warnings.

Repo access is only for context, task-card validation, registry visibility, and report output. This task must not edit source code, data stores, runtime configuration, Docker volumes, models, worktrees, cron, or systemd units.

## Safe Process Policy

An obvious runaway non-critical dev/test process may be stopped only if all of these are true:

- it is clearly a dev/test process such as stale pytest, pnpm build, playwright, next dev, orphaned Codex helper, or runaway Cursor/tsserver;
- it is not postgres, qdrant, backend, worker, llama, ollama, Docker daemon, cron, or a systemd service;
- stopping it does not risk data loss;
- PID, command, reason, and result are recorded in the report.

If unsure, do not stop it. Report the proposed command for user approval.

## Required Outputs

- `reports/agent_jobs/pc_ssh_slow_safe_diagnostics_v1_20260524/README.md`
- `reports/agent_jobs/pc_ssh_slow_safe_diagnostics_v1_20260524/status.json`

## Required Report Sections

- Confirmed facts
- Inferred facts
- DATA_MISSING
- top CPU processes
- top memory processes
- disk usage
- I/O wait findings
- Docker/container load
- GPU/llama status
- SSH/network findings
- system warnings/errors
- any process stopped, or explicit "none stopped"
- final diagnosis
- safe next actions
- unsafe actions avoided
- whether a follow-up implementation/ops task is recommended

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pc_ssh_slow_safe_diagnostics_v1_20260524.md`
- `python3 scripts/agent_job_registry.py list-active`
- JSON parse `status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/pc_ssh_slow_safe_diagnostics_v1_20260524.md`

## Hard Stops

Stop and report instead of mutating if diagnostics indicate the likely next step would require source edits, broad cleanup, Docker prune, model deletion, worktree deletion, DB/Qdrant/news/memory mutation, backend/worker/postgres/qdrant/llama/ollama termination, service restart, GPU/runtime config edit, cron/systemd edit, or any uncertain process stop.
