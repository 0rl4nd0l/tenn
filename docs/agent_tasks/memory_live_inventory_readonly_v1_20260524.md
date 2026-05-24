---
job_id: memory_live_inventory_readonly_v1_20260524
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_live_inventory_readonly_v1_20260524.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/README.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/status.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.csv
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/read_only_proof.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_live_inventory_readonly_v1_20260524
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Memory Live Inventory Read-only

## Objective

Resolve the active local memory store path from current runtime/config evidence, inventory active company-memory rows and historical contamination markers read-only, and report whether active rows can still surface as ticker memory context.

## Allowed Work

- Read-only SQLite opens using immutable/query-only mode.
- Report-local JSON/CSV artifacts.
- Code-path inspection for current read selection and surfacing.

## Forbidden

- No memory delete, update, rewrite, migration, alias canonicalisation, reindex, resync, chat smoke that writes events, Qdrant mutation, or production-store mutation.

## Validation

- Validate this task card.
- Prove read-only open settings.
- Record path resolution evidence and before/after file metadata.
- Validate JSON artifacts and run `git diff --check`.
