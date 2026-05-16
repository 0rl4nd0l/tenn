---
job_id: memory_validation_gate_isolation_v1_20260516
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_validation_gate_isolation_v1_20260516.md
  - scripts/validate_system.sh
  - scripts/validate_memory_integrity.sh
  - scripts/test_validate_system_routing_smoke.py
  - scripts/test_validate_memory_integrity_script.py
  - reports/agent_jobs/memory_validation_gate_isolation_v1_20260516/**
  - reports/agent_jobs/memory_validation_gate_isolation_v1_20260516/README.md
  - reports/agent_jobs/memory_validation_gate_isolation_v1_20260516/status.json
  - reports/agent_jobs/memory_validation_gate_isolation_v1_20260516/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_validation_gate_isolation_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Make the memory integrity validation gate runnable and testable independently of the broader runtime smoke gate.

# Scope

Allowed:
- extract the memory integrity portion of `scripts/validate_system.sh` into a dedicated script
- keep `scripts/validate_system.sh` calling the memory gate in the regular validation path
- add tests proving the memory-only gate can pass/fail without backend runtime smoke
- write task/report artifacts

Out of scope:
- changing backend endpoints, memory write paths, live SQLite data, Qdrant, Postgres, financial truth, embeddings, Cockpit UI, or `financial-engine_v2/scripts/smoke_local.sh` behavior
- staging unrelated shared-checkout dirty files
- mutating production data

# Validation

- task-card validate, registry overlap check, claim, check-diff
- shell syntax checks for touched shell scripts
- focused pytest for validation script behavior
- live read-only memory-only validation command
