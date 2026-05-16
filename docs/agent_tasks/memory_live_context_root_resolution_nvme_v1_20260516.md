---
job_id: memory_live_context_root_resolution_nvme_v1_20260516
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_live_context_root_resolution_nvme_v1_20260516.md
  - financial-engine_v2/backend/app/services/source_registry.py
  - financial-engine_v2/backend/tests/test_source_registry_root.py
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/**
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/README.md
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/status.json
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/validation.json
  - reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_live_context_root_resolution_nvme_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Fix the NVMe live-runtime memory context root so backend memory APIs prefer existing populated research-memory stores before creating empty fallback SQLite stores.

# Scope

Allowed:
- update `source_registry.py` root selection for research memory stores
- add focused tests for existing-store preference and writable fallback behavior
- validate live blocker evidence without mutating memory databases
- write task/report artifacts

Out of scope:
- mutating company, market, or thesis memory SQLite data
- cleanup, canonicalization, reindexing, or rewrite
- changing Qdrant, Postgres, financial truth, chat routing, Cockpit UI, or runtime launch scripts
- staging unrelated dirty files from the live runtime worktree

# Validation

- task-card validate, registry overlap check, claim, check-diff
- focused pytest for source registry root selection
- targeted import/path probe for `RESEARCH_MEMORY_ROOT`
- live read-only endpoint check after deployment/restart only if safely available
