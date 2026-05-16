---
job_id: smoke_sync_mode_gate_v1_20260516
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/smoke_sync_mode_gate_v1_20260516.md
  - financial-engine_v2/scripts/smoke_local.sh
  - scripts/test_smoke_local_mode_handling.py
  - reports/agent_jobs/smoke_sync_mode_gate_v1_20260516/**
  - reports/agent_jobs/smoke_sync_mode_gate_v1_20260516/README.md
  - reports/agent_jobs/smoke_sync_mode_gate_v1_20260516/status.json
  - reports/agent_jobs/smoke_sync_mode_gate_v1_20260516/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/smoke_sync_mode_gate_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Make the local smoke script handle backend task mode explicitly so the regular validation path can distinguish an intentionally non-sync backend from a failed sync backfill.

# Scope

Allowed:
- inspect `financial-engine_v2/scripts/smoke_local.sh` mode handling
- make sync backfill required only when explicitly requested
- keep health/docs/RAG smoke behavior unchanged
- add focused tests for sync-mode skip/require behavior
- write task/report artifacts

Out of scope:
- changing backend route behavior, pipeline/backfill semantics, live data, Qdrant, Postgres, financial truth, embeddings, Cockpit UI, or runtime startup scripts
- running heavy or mutating production backfills beyond existing smoke validation
- staging unrelated shared-checkout dirty files

# Validation

- task-card validate, registry overlap check, claim, check-diff
- shell syntax check for `financial-engine_v2/scripts/smoke_local.sh`
- focused pytest for smoke mode handling
- validation script smoke where safe
