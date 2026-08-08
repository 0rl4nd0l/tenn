---
job_id: llama_server_8001_owner_resolution_followup_v1_20260526
lane: Reporting
supporting_lanes:
  - Runtime
  - Evaluation
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/llama_server_8001_owner_resolution_followup_v1_20260526.md
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/README.md
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/status.json
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/validation.json
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/diff-check.json
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/owner_resolution_report.md
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_gpu_process_guard.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_ss_8001.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_ps_llama.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_systemctl_units.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_systemctl_show_llama_cpp_router.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_systemctl_status_llama_cpp_router.txt
  - reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526/raw_proc_owner_links.txt
approval_required: false
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/llama_server_8001_owner_resolution_followup_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: pr_create
related_issue: 113
---

# Llama Server :8001 Owner Resolution Follow-Up

## Objective

Resolve issue #113 by auditing the current `:8001` llama-server launcher/owner
evidence without restarting, killing, or changing runtime configuration.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-runtime-llama-server-8001-owner-resolution-v1-20260601`.
- Branch: `audit/runtime-llama-server-8001-owner-resolution-v1-20260601`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Issue: #113.
- Primary task-card lane: Reporting.
- Supporting scope: Runtime, Evaluation, Query Orchestration.
- Intended files: this task card and this job's report artifacts only.
- Contested surfaces touched: none.
- Collision risk: LOW after active-registry check passes.
- Decision: proceed in AUDIT MODE only.

## Contract Check

- Target system layer: runtime operations evidence for local LLM service
  topology; no application pipeline layer is modified.
- Relevant contract rules: backend remains sole authority for financial data;
  Cockpit remains client/orchestration only; GPU process topology and
  llama-server runtime ownership must remain explicit and non-mutating.
- What must not change: financial truth, extraction, retrieval, memory stores,
  prompt semantics, source/evidence labels, Qdrant, Postgres, process state,
  service state, model/runtime/GPU configuration, and production data.
- Why safe: this job records read-only runtime evidence and writes only
  allowlisted report artifacts.
- GPU process check required: yes, read-only guard check only; no spawn,
  restart, kill, or config change is allowed.

## Required Behavior

- Identify the current `:8001` launcher/owner, or mark exact remaining
  evidence as `DATA_MISSING`.
- Reconcile socket owner, parent process, child worker, launcher path, and
  systemd user-unit state where available.
- Link any future remediation need to separate safe-extension work.
- Do not restart, kill, reload, or reconfigure any runtime process or service.

## Forbidden

- Starting, stopping, killing, restarting, reloading, or reconfiguring
  `llama-server` or user services.
- Model/runtime/GPU/service config mutation.
- Production DB, Qdrant, news, or memory writes.
- Canonical financial truth changes.
- Parser routing, extraction prompts, or gold labels.
- Unrelated dirty work, cleanup, branch mutation, stash, reset, rebase, or merge.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/llama_server_8001_owner_resolution_followup_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/llama_server_8001_owner_resolution_followup_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/llama_server_8001_owner_resolution_followup_v1_20260526.md --repo-root .`
- `scripts/gpu_process_guard.sh --check`
- `ss -ltnp | rg ':8001'`
- `ps -eo pid,ppid,stat,etime,cmd | rg 'llama-server|run_llama'`
- `systemctl --user list-units --type=service --all`
- `systemctl --user show llama-cpp-router.service`
- `systemctl --user status llama-cpp-router.service --no-pager`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/llama_server_8001_owner_resolution_followup_v1_20260526.md --repo-root .`
- Registry release and final status check.

## Final Report Requirements

- Files changed.
- Exact validation commands and results.
- Current `:8001` owner conclusion, or explicit `DATA_MISSING`.
- Service state, parent process, child worker, and launcher path reconciliation.
- Explicit statement that no runtime process, service config, production data,
  memory, retrieval, financial truth, prompt semantics, GPU/runtime
  configuration, Qdrant, or Postgres state was changed.
