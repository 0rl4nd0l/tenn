# NVMe Dirty Surface Classification

Generated: 2026-05-16T18:20:00+10:00

## Session Declaration

```text
Lane: Evaluation
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: AUDIT ONLY
Intended files: docs/agent_tasks/nvme_dirty_surface_classification_v1_20260516.md; reports/agent_jobs/nvme_dirty_surface_classification_v1_20260516/
Contested surfaces touched: none
Collision risk: LOW
Decision: proceed with audit artifact checkpoint only
```

## Summary

The NVMe checkout is the correct active workspace for new Tenn dev/runtime work. Its current dirty surface is small and classifiable:

- one modified prior report status file from `news_loader_ollama_url_hardening_integrate_nvme_v1_20260515`
- ten untracked runtime/GPU task cards from the M40/APEX/virtual-GPU investigation series
- matching report directories exist for all ten untracked runtime/GPU task cards
- all ten task cards validate under `scripts/agent_job_contract.py`

No product source files are dirty in the NVMe checkout.

## Classification

The untracked runtime/GPU task cards are preservation candidates, not cleanup noise. They document a single runtime investigation chain around local M40 llama.cpp CUDA instability, CPU fallback rejection, and virtual/rented GPU unavailability.

Recommended handling:

- preserve these task cards in one Query Orchestration/runtime-hygiene checkpoint after review
- do not delete them until their report bundles are confirmed committed or intentionally archived
- do not mix them with unrelated product work
- do not use CPU fallback as the default runtime restore path without explicit user approval

The modified `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json` appears to be registry-release metadata overwriting a richer validation summary. Preserve or repair it separately before any broad cleanup.

## Evidence

Current worktree:

```text
/home/l4nd0/tenn-fast-dev-storage-v1
fast/dev-storage-v1-20260513-170304
HEAD 2b2197e
```

Current dirty files at audit start:

```text
M  reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
?? docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
?? docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
?? docs/agent_tasks/local_cpu_qwen35_runtime_restore_v1_20260516.md
?? docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
?? docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md
?? docs/agent_tasks/m40_llamacpp_runtime_restore_v1_20260516.md
?? docs/agent_tasks/m40_no_mmap_isolated_control_v1_20260516.md
?? docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md
?? docs/agent_tasks/virtual_gpu_runtime_restore_v1_20260516.md
```

Active registry jobs at claim time:

```text
memory_handoff_context_prefill_v1_20260516
```

That job is Reporting-lane and uses `/home/l4nd0/tenn-overview-news-commentary-approval-v1-20260516`, so it did not overlap this Evaluation audit.

## Runtime Task Findings

- `apex_m40_runtime_stability_audit_v1_20260516`: classified APEX on M40 as `UNSTABLE_DO_NOT_RELY_ON_APEX`.
- `apex_m40_runtime_recovery_or_degrade_v1_20260516`: attempted bounded local recovery; APEX remained unstable.
- `apex_m40_gpu_vs_model_differential_probe_v1_20260516`: classified the failure as broader than APEX, pointing to `CUDA_M40_LLAMACPP_RUNTIME_PATH_FAILURE`.
- `m40_no_mmap_isolated_control_v1_20260516`: `--no-mmap` did not restore the small-model CUDA path.
- `m40_non_llama_cuda_smoke_v1_20260516`: basic non-llama CUDA worked on the M40.
- `m40_llamacpp_runtime_restore_v1_20260516`: local llama restore was partial only; CPU control worked but was not left running.
- `m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516`: no-VMM rebuild still failed.
- `virtual_gpu_runtime_restore_v1_20260516`: virtual/rented GPU path was unavailable.
- `local_cpu_qwen35_runtime_restore_v1_20260516`: CPU fallback was intentionally stopped after user correction.
- `m40_cuda_failure_remediation_v1_20260516`: final classification was `M40_CUDA_LLAMACPP_BACKEND_FAULT`; recommended host reboot or privileged M40 reset before further Qwen3.5 probes.

## DATA_MISSING

- `.cursor/agents/repository_audit.md` is absent in this checkout, so the repository-audit skill's detailed local checklist could not be read.
- `graphify-out/GRAPH_REPORT.md` is absent in this checkout.
- This audit did not verify whether every matching report artifact is already committed on another branch.

## Next Safe Step

Create a focused Query Orchestration/runtime-hygiene checkpoint from the NVMe checkout that stages only the ten runtime/GPU task cards and their matching report bundles, plus an explicit decision on whether to repair or preserve the overwritten news-loader status file.
