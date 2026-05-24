---
job_id: runtime_topology_reconciliation_impl_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/runtime_topology_reconciliation_impl_v1_20260524.md
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/
  - docs/startup.md
  - docs/setup/environment.md
  - systemd/llama-cpp-router.service
  - scripts/storage_guard.py
  - financial-engine_v2/scripts/nightly_news.sh
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/diff-check.json
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/status.json
  - docs/agent_tasks/runtime_topology_rebind_readiness_impl_v1_20260524.md
approval_required: true
approval_source: "User replied 'proceedd' after runtime_topology_reconciliation_audit_v1_20260522 final report on 2026-05-24."
timeout_seconds: 7200
output_dir: reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Runtime Topology Reconciliation Implementation

Proceed from `runtime_topology_reconciliation_audit_v1_20260522`.

Scope is controlled implementation after explicit user approval:

- checkpoint current runtime and fast-dev evidence first;
- do not touch Appendix 5B integration files owned by the active/stale integration registry lane;
- do not rebind Docker, systemd, or cron until prerequisites are proven safe in this job;
- prefer documentation/template guardrails and prerequisite fixes before runtime mutation;
- record every skipped mutation with the exact blocker.
