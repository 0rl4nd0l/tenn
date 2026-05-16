---
job_id: nvme_runtime_gpu_artifact_preservation_v1_20260516
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_runtime_gpu_artifact_preservation_v1_20260516.md
  - reports/agent_jobs/nvme_runtime_gpu_artifact_preservation_v1_20260516/**
  - reports/agent_jobs/nvme_runtime_gpu_artifact_preservation_v1_20260516/README.md
  - reports/agent_jobs/nvme_runtime_gpu_artifact_preservation_v1_20260516/status.json
  - reports/agent_jobs/nvme_runtime_gpu_artifact_preservation_v1_20260516/diff-check.json
  - docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
  - reports/agent_jobs/apex_m40_gpu_vs_model_differential_probe_v1_20260516/README.md
  - reports/agent_jobs/apex_m40_gpu_vs_model_differential_probe_v1_20260516/diff-check.json
  - reports/agent_jobs/apex_m40_gpu_vs_model_differential_probe_v1_20260516/status.json
  - reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/README.md
  - reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/diff-check.json
  - reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/status.json
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/README.md
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/diff-check.json
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/status.json
  - reports/agent_jobs/local_cpu_qwen35_runtime_restore_v1_20260516/README.md
  - reports/agent_jobs/local_cpu_qwen35_runtime_restore_v1_20260516/diff-check.json
  - reports/agent_jobs/local_cpu_qwen35_runtime_restore_v1_20260516/status.json
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/README.md
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/diff-check.json
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/status.json
  - reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/README.md
  - reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/diff-check.json
  - reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/status.json
  - reports/agent_jobs/m40_llamacpp_runtime_restore_v1_20260516/README.md
  - reports/agent_jobs/m40_llamacpp_runtime_restore_v1_20260516/diff-check.json
  - reports/agent_jobs/m40_llamacpp_runtime_restore_v1_20260516/status.json
  - reports/agent_jobs/m40_no_mmap_isolated_control_v1_20260516/README.md
  - reports/agent_jobs/m40_no_mmap_isolated_control_v1_20260516/diff-check.json
  - reports/agent_jobs/m40_no_mmap_isolated_control_v1_20260516/status.json
  - reports/agent_jobs/m40_non_llama_cuda_smoke_v1_20260516/README.md
  - reports/agent_jobs/m40_non_llama_cuda_smoke_v1_20260516/diff-check.json
  - reports/agent_jobs/m40_non_llama_cuda_smoke_v1_20260516/status.json
  - reports/agent_jobs/virtual_gpu_runtime_restore_v1_20260516/README.md
  - reports/agent_jobs/virtual_gpu_runtime_restore_v1_20260516/diff-check.json
  - reports/agent_jobs/virtual_gpu_runtime_restore_v1_20260516/status.json
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/nvme_runtime_gpu_artifact_preservation_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Preserve the remaining NVMe runtime/GPU investigation metadata after the runtime remediation job released. Commit only metadata artifacts; do not run runtime probes, change source code, or touch the unrelated modified news-loader status file.

# Scope

Allowed:
- preserve the remaining untracked M40 remediation task card
- preserve existing ignored report bundles for the M40/APEX/virtual-GPU investigation chain
- write this task card and report artifacts

Out of scope:
- source code edits
- runtime restarts, GPU probes, model loads, or service changes
- database, Qdrant, memory, news store, or financial truth mutation
- modifying `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json`

# Notes

At checkpoint start, nine earlier untracked runtime task cards were already absent from the worktree. Their report bundles still existed and are preserved by this task.
