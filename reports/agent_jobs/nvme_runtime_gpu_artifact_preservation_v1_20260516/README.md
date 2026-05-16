# NVMe Runtime/GPU Artifact Preservation

Generated: 2026-05-17T00:50:00+11:00

## Summary

Preserved the remaining NVMe runtime/GPU investigation metadata without touching product code or runtime state.

The checkpoint includes:

- the remaining untracked M40 remediation task card
- ten report bundles for the M40/APEX/virtual-GPU investigation chain
- this preservation task card and report

The unrelated modified `news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json` was deliberately left unstaged and uncommitted.

## Important Observation

At the start of this checkpoint, only `docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md` remained as an untracked runtime task card. The other nine task cards identified by the previous NVMe dirty-surface audit were already absent from the worktree. Their report bundles remained present under `reports/agent_jobs/` and were preserved.

## Preserved Report Bundles

- `apex_m40_runtime_stability_audit_v1_20260516`
- `apex_m40_runtime_recovery_or_degrade_v1_20260516`
- `apex_m40_gpu_vs_model_differential_probe_v1_20260516`
- `m40_no_mmap_isolated_control_v1_20260516`
- `m40_non_llama_cuda_smoke_v1_20260516`
- `m40_llamacpp_runtime_restore_v1_20260516`
- `m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516`
- `virtual_gpu_runtime_restore_v1_20260516`
- `local_cpu_qwen35_runtime_restore_v1_20260516`
- `m40_cuda_failure_remediation_v1_20260516`

## Validation

- task-card validation passed
- registry overlap check passed
- registry claim and release passed
- `check-diff` passed
- `git diff --cached --check` passed before commit

## Remaining Dirt

The only intended remaining dirt after this checkpoint is:

```text
M reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
```

That artifact should be handled separately because it belongs to a prior news-loader job, not the runtime/GPU investigation chain.
