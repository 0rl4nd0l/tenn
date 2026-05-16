---
job_id: nvme_dirty_surface_classification_v1_20260516
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_dirty_surface_classification_v1_20260516.md
  - reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/**
  - reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/README.md
  - reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/status.json
  - reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/diff-check.json
  - reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/dirty_surface_classification.md
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
  - docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
  - docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
  - docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
  - docs/agent_tasks/local_cpu_qwen35_runtime_restore_v1_20260516.md
  - docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
  - docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md
  - docs/agent_tasks/m40_llamacpp_runtime_restore_v1_20260516.md
  - docs/agent_tasks/m40_no_mmap_isolated_control_v1_20260516.md
  - docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md
  - docs/agent_tasks/virtual_gpu_runtime_restore_v1_20260516.md
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify the current dirty surface in the NVMe fast-dev checkout and recommend the next safe action. Do not clean, stage, commit, revert, move, delete, or checkpoint product/runtime work.

# Scope

Allowed:
- inspect current branch, HEAD, active registry jobs, git status, ignored status, and matching report directories
- classify the existing modified report artifact and untracked runtime/GPU task cards
- write this audit task card and report artifacts only

Out of scope:
- product code edits
- runtime restart or GPU process changes
- database, Qdrant, memory, news store, financial truth, or production data mutation
- deleting or archiving the existing untracked task cards
- committing the existing dirty files

# Safety Notes

The non-report paths in `allowed_files` are pre-existing dirty files observed at task start. They are included only so `check-diff` can distinguish known environmental dirt from audit scope. They are not approved write targets for this audit.

# Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme_dirty_surface_classification_v1_20260516.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/nvme_dirty_surface_classification_v1_20260516.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme_dirty_surface_classification_v1_20260516.md --write-report`
- release registry claim
