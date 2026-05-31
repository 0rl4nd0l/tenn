---
job_id: memory_system_fitness_audit_v1_20260526
title: Memory System Fitness Audit v1
owner: Codex
lane: Memory
primary_lane: Memory
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
  - Reporting
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_system_fitness_audit_v1_20260526
allowed_files:
  - docs/agent_tasks/memory_system_fitness_audit_v1_20260526.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/README.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/status.json
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/memory_surface_inventory.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/fit_gap_matrix.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/read_write_path_map.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/followups.md
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/validation.json
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/diff-check.json
  - reports/agent_jobs/memory_system_fitness_audit_v1_20260526/code_review.json
allow_audit_code_changes: true
---

# Memory System Fitness Audit v1

Resolve GitHub issue #88 with an audit-only/report-only memory-system fitness
review.

## Scope

- Inventory active Tenn memory classes and management surfaces.
- Compare current implementation to intended analyst workflow requirements.
- Assess read paths, write paths, provenance boundaries, staleness/expiry,
  contamination controls, user-thesis/preference separation, session continuity,
  UI visibility, validation, and observability.
- Produce an architecture-fitness verdict and ranked issue-ready follow-up
  roadmap.

## Required Boundaries

Do not change:

- product code;
- memory stores;
- production DB, Qdrant, news, or memory data;
- canonical financial truth;
- parser or extraction routing;
- extraction prompts;
- gold labels;
- embedding configuration or vector collections;
- runtime, model, GPU, service, scheduler, or provider config.

No cleanup, expiration, migration, reindex, dedupe, rewrite, or memory-row
mutation is authorized.

## System Contract Compliance

Target system layer: audit/evaluation of Memory-related Analysis and Client
surfaces. This task does not modify ingestion, extraction, storage, retrieval,
analysis logic, client product behavior, or data stores.

Relevant contract rules:

- Backend remains the sole authority for authoritative data and retrieval.
- Cockpit remains a client/orchestration layer only.
- Memory remains qualitative/reasoning context and must not override canonical
  financial truth.
- No fallback, substitution, duplicate pipeline, or data-store mutation is
  introduced.

GPU guard: not required. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_system_fitness_audit_v1_20260526.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_system_fitness_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_system_fitness_audit_v1_20260526.md`
- duplicate checks against GitHub issues for memory-system audit/follow-up scope
- read-only static inspections of docs, source, tests, and existing task cards
- JSON parse report metadata
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_system_fitness_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py release memory_system_fitness_audit_v1_20260526`
