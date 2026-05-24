---
job_id: runtime_topology_reconciliation_audit_v1_20260522
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md
  - reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/
  - docs/
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522
mutation_mode: audit_only
production_data_access: false
---

# Runtime Topology Reconciliation Audit

Audit Tenn runtime topology and produce an approval-gated reconciliation plan so active runtime surfaces can use the canonical `/home/l4nd0/tenn` path.

## Scope

- Primary lane: Evaluation
- Supporting lanes: Repo Hygiene, Reporting, Runtime/Ops
- Mode: audit first; plan only by default
- Risk: high for mutation

## Constraints

- Do not mutate live runtime bindings.
- Do not stop, start, restart, rebind, edit, or delete Docker containers, systemd services, cron entries, symlinks, mounts, data/report paths, old checkouts, or runtime config.
- Write the report only under `reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/`.

## Required Output

Produce `reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/README.md` with confirmed facts, live runtime binding table, Docker/systemd/cron/data findings, approval-gated implementation and rollback commands clearly marked as not run, validation plan, final git status, registry release, and project memory recommendation.
