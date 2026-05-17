---
job_id: memory_nvme_fastdev_context_root_integration_v1_20260517
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_nvme_fastdev_context_root_integration_v1_20260517.md
  - docs/agent_tasks/memory_live_context_root_resolution_nvme_v1_20260516.md
  - docs/agent_tasks/memory_company_context_active_only_read_guard_v1_20260517.md
  - financial-engine_v2/backend/app/services/source_registry.py
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_source_registry_root.py
  - financial-engine_v2/backend/tests/test_context_endpoints.py
  - reports/agent_jobs/memory_nvme_fastdev_context_root_integration_v1_20260517/**
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/**
  - reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_nvme_fastdev_context_root_integration_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Integrate the NVMe live memory context root and active-only company context guard onto `fast/dev-storage-v1-20260513-170304`.

# Scope

Allowed:
- cherry-pick the existing memory root override and active-only company context commits
- retain the prior memory task/report artifacts needed for provenance
- add this integration task/report artifacts
- run focused backend tests, ruff, check-diff, and live/read-only endpoint checks if safely available

Out of scope:
- mutating company, market, thesis, Qdrant, or Postgres data
- cleanup, canonicalization, reindexing, or rewrite of memory stores
- modifying Cockpit UI, runtime launcher behavior, financial truth, extraction, or query routing beyond the existing memory commits
- touching dirty runtime preserve worktrees

# Validation

- task-card validate, active-job check, claim, check-diff
- focused pytest for source registry root selection and context endpoint active-only loading
- ruff on touched backend files
- optional live check against currently running backend for status only
