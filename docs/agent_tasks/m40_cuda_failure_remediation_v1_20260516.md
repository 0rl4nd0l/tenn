---
job_id: m40_cuda_failure_remediation_v1_20260516
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/README.md
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/status.json
  - reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/diff-check.json
  - docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
  - docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
  - docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
  - docs/agent_tasks/local_cpu_qwen35_runtime_restore_v1_20260516.md
  - docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md
  - docs/agent_tasks/m40_llamacpp_runtime_restore_v1_20260516.md
  - docs/agent_tasks/m40_no_mmap_isolated_control_v1_20260516.md
  - docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md
  - docs/agent_tasks/virtual_gpu_runtime_restore_v1_20260516.md
  - reports/agent_jobs/apex_m40_gpu_vs_model_differential_probe_v1_20260516/
  - reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/
  - reports/agent_jobs/local_cpu_qwen35_runtime_restore_v1_20260516/
  - reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/
  - reports/agent_jobs/m40_llamacpp_runtime_restore_v1_20260516/
  - reports/agent_jobs/m40_no_mmap_isolated_control_v1_20260516/
  - reports/agent_jobs/m40_non_llama_cuda_smoke_v1_20260516/
  - reports/agent_jobs/virtual_gpu_runtime_restore_v1_20260516/
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516
mutation_mode: safe_extension
production_data_access: false
---

# Task

Investigate and remediate the M40/CUDA llama.cpp failure without CPU fallback and without source-code edits.

# Scope

Use bounded CUDA-only probes to determine whether the failure is:

- CUDA device-selection mismatch,
- large host-to-device transfer failure,
- APEX/full-offload specific,
- Qwen3.5 reduced-layer recoverable,
- or a lower-level M40/driver fault requiring reboot/driver reset/hardware action.

# Allowed Runtime Actions

- Compile temporary CUDA diagnostic programs under `/tmp`.
- Run bounded non-llama CUDA identity and transfer probes.
- Run at most two isolated llama.cpp CUDA model-load probes on temporary non-production ports:
  - configured Qwen3.5 Q4 with reduced GPU layers matching the existing preset,
  - Qwen2.5 with reduced GPU layers only if needed to distinguish size/full-offload sensitivity.
- If a CUDA probe succeeds and returns a coherent tiny response, restart only `:8001` with the same CUDA-safe settings.
- Stop only broken llama.cpp processes with failed/defunct children.
- Do not use CPU fallback.
- Do not use or mutate `:18001`.
- Do not edit source code, checked-in config, model aliases, model files, databases, Qdrant, news stores, or memory stores.
- Write reports under this task output directory.

# Classification

Classify the result as:

- `M40_CUDA_RESTORED_QWEN35_REDUCED_LAYERS`
- `M40_CUDA_PARTIAL_RESTORE_SMALL_MODEL`
- `M40_CUDA_DRIVER_OR_HARDWARE_FAULT`
- `M40_CUDA_LLAMACPP_BACKEND_FAULT`
- `DATA_MISSING`
