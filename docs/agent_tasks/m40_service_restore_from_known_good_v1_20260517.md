---
job_id: m40_service_restore_from_known_good_v1_20260517
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/m40_service_restore_from_known_good_v1_20260517.md
  - reports/agent_jobs/m40_service_restore_from_known_good_v1_20260517/
  - reports/agent_jobs/m40_service_restore_from_known_good_v1_20260517/README.md
  - reports/agent_jobs/m40_service_restore_from_known_good_v1_20260517/status.json
  - reports/agent_jobs/m40_service_restore_from_known_good_v1_20260517/diff-check.json
  - scripts/runtime/m40_llama_router_8001_conservative.sh
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/m40_service_restore_from_known_good_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Stage a controlled, reversible restoration path for the local M40 llama.cpp service on `127.0.0.1:8001` using the known-good conservative Qwen2.5 14B command from `scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh`.

# Scope

- Inspect the existing systemd/service and launcher configuration before proposing any restore.
- Preserve a service-safe wrapper for the conservative `:8001` command.
- Write a report with current runtime state, differences from the risky path, exact manual restore command, rollback, and validation checklist.

# Hard boundaries

- Do not start or bind `:8001` in this task.
- Do not modify Cockpit routing.
- Do not modify model files.
- Do not run APEX/Qwen3.5.
- Do not install, enable, or restart live systemd units.
- Do not use auto parallelism, prompt cache, or fit auto/on in the staged command.
- Do not use CUDA1 unless a fresh device list proves CUDA1 is the M40.
