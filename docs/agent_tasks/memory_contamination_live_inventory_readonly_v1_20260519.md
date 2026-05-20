---
job_id: memory_contamination_live_inventory_readonly_v1_20260519
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_contamination_live_inventory_readonly_v1_20260519.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/README.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/db_path_resolution.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/schema_inventory.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_contamination_summary.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_duplicate_clusters.csv
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_source_fanout_clusters.csv
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/ticker_spot_checks.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/known_historical_source_checks.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/candidate_entry_id_status_check.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/cleanup_readiness.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519
mutation_mode: audit_only
production_data_access: false
production_data_access_requested: true
read_only_production_memory_inventory: true
allow_audit_code_changes: true
---

# Task

Read-only live inventory for company-memory contamination state.

The user requested production memory inventory, but the repo-local task-card
validator hard-requires `production_data_access: false`. This card therefore
keeps the validator-required field unchanged and records the user-approved
read-only production inventory scope in custom metadata and this body.

# Purpose

Determine whether active contaminated or memo-level fanout rows still exist in
the current live company-memory database.

# Boundaries

- Audit only.
- Read-only filesystem and SQLite access for production memory inventory.
- No cleanup, expiry, delete, update, migration, alias canonicalization,
  statement rewrite, Qdrant reindex, news resync, memory writer calls, live
  chat/API write paths, runtime changes, model changes, or GPU changes.
- Do not dump broad personal data or large statement bodies.
- Produce row-ID manifests and short previews only where needed for operator
  review.

# Required Outputs

Write only the allowlisted artifacts under:

`reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/`

The report must classify:

- current active company-memory DB path and storage location;
- whether active duplicate/fanout contamination is present;
- affected source IDs and ticker spot checks;
- surfacing risk from DB inventory and code inspection only;
- cleanup readiness for a future operator-approved cleanup task.

# Hard Stops

Stop and report if:

- active DB path cannot be resolved;
- DB cannot be opened read-only;
- active registry shows overlapping Memory work;
- any step would mutate DB/data/runtime/source outside allowlisted artifacts;
- a query requires broad personal data dumping;
- artifact output would expose secrets or excessive user personal data.
