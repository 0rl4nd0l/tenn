---
job_id: memory_company_context_active_only_read_guard_v1_20260517
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_company_context_active_only_read_guard_v1_20260517.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_endpoints.py
  - reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/**
  - reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/status.json
  - reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/validation.json
  - reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Prevent ticker-specific company context from feeding expired historical company-memory rows into reasoning/read-context APIs by default.

# Scope

Allowed:
- update backend context API company-memory loading so ticker context uses active company memory entries by default
- preserve change-log visibility and existing memory index behavior
- add focused endpoint/unit tests for active-only company context
- write task/report artifacts

Out of scope:
- mutating company, market, or thesis memory SQLite data
- cleanup, canonicalization, reindexing, or rewrite
- changing write-path extraction, Qdrant, Postgres, financial truth, chat routing, Cockpit UI, or runtime launch scripts
- staging unrelated dirty files from any live runtime worktree

# Validation

- task-card validate, registry active-job check, claim, check-diff
- focused pytest for context endpoint company-memory loading
- ruff on touched backend files
- live read-only endpoint check after restart if safely available
