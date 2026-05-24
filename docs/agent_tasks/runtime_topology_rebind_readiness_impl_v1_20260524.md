---
job_id: runtime_topology_rebind_readiness_impl_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/runtime_topology_rebind_readiness_impl_v1_20260524.md
  - reports/agent_jobs/runtime_topology_rebind_readiness_impl_v1_20260524/
  - scripts/storage_guard.py
  - scripts/start_config.env
  - scripts/verify_nvme_runtime_endpoints.sh
  - systemd/llama-cpp-router.service
  - financial-engine_v2/scripts/nightly_news.sh
  - docs/
approval_required: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/runtime_topology_rebind_readiness_impl_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Runtime Topology Rebind Readiness Implementation

## Goal

Reconcile Tenn runtime topology so active runtime surfaces use canonical
`/home/l4nd0/tenn` where safe, after confirming the Appendix 5B preservation
blocker is cleared.

## Boundaries

- Audit first, then only perform runtime rebind steps that pass the hard-stop
  gates in this card.
- Do not delete, prune, move, rsync, or discard old worktrees.
- Do not run `docker compose down`, remove Docker volumes, or prune Docker
  resources.
- Do not mutate Postgres, Qdrant, news, memory, parser routing, extraction
  truth, models, GPU drivers, or production data stores.
- Do not edit old HDD checkouts or fast-dev.
- Treat broad `docs/`, `scripts/`, and `systemd/` allowances as
  docs/templates/guardrail allowances only.
- The local task-card contract accepts `audit_only`, `safe_extension`, or
  `blocked`; this card uses `safe_extension` with `approval_required: true`
  for the approval-gated runtime rebind lane.

## Required Preflight

- Confirm `/home/l4nd0/tenn` and `/home/l4nd0/tenn-runtime` resolution.
- Confirm branch, HEAD, working-tree state, git worktrees, and git common dir.
- Validate this task card and registry overlap.
- Claim the registry job only if safe.
- Confirm commit `c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967` is an ancestor of
  canonical `HEAD`.
- Inspect current reconciliation, fast-dev preservation, and Appendix 5B
  integration reports if present.

## Hard Stops

Stop report-only if any of these are true:

- Appendix 5B commit `c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967` is absent.
- Fast-dev still has non-Appendix 5B `PRESERVE_AND_INTEGRATE` code absent from
  canonical.
- Canonical has tracked dirty files in runtime, docs, scripts, or service
  targets that would make runtime rebinding ambiguous.
- Active registry jobs overlap runtime or repo-hygiene surfaces.
- Docker source paths cannot be identified.
- Qdrant or Postgres volumes appear at risk.
- `/data` or `/reports` aliases do not resolve to `/mnt/tenn-nvme2`.
- NVIDIA/M40 health is broken in a way that would confound runtime rebind.
- Required commands would delete/prune/rsync data or mutate DB, Qdrant, news, or
  memory state.

## Allowed Runtime Actions

If all hard-stop gates pass:

- Recreate only `backend`, `worker`, and `gpu_worker` from canonical compose,
  preserving Qdrant/Postgres volumes.
- Recreate Cockpit UI from `/home/l4nd0/tenn/cockpit-ui` only after backend
  health passes.
- Rebind cron only if the canonical newspaper4k venv exists and a safe dry-run
  path passes.

## Report

Write evidence and final report under:

`reports/agent_jobs/runtime_topology_rebind_readiness_impl_v1_20260524/`
