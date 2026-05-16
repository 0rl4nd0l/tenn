---
job_id: memory_integrity_audit_guard_v1_20260516
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_integrity_audit_guard_v1_20260516.md
  - scripts/audit_memory_integrity.py
  - scripts/test_audit_memory_integrity.py
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/**
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/README.md
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/status.json
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/diff-check.json
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/live_audit.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_integrity_audit_guard_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Add a reusable read-only memory-integrity audit guard for the cleaned market-memory state.

# Scope

Allowed:
- add a read-only script that checks active market-memory linked ticker invariants
- add focused tests with temporary SQLite fixtures
- write report artifacts from a live read-only audit run

Out of scope:
- mutating memory SQLite databases
- changing memory write paths or backend services
- changing Qdrant, Postgres, extraction, financial-truth data, or Cockpit UI

# Validation

- task-card validate, registry overlap check, claim, check-diff
- focused pytest for the new audit script
- live read-only audit against `/data/reports/research_memory/market_memory.sqlite`
- live `/api/health` smoke if backend is already running
