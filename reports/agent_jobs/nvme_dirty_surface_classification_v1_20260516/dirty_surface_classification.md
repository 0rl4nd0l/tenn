# Dirty Surface Classification

| Path | State | Lane | Classification | Recommendation |
| --- | --- | --- | --- | --- |
| `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json` | modified tracked | Query Orchestration | prior report metadata overwritten by registry release | preserve or repair separately; do not absorb into runtime task-card checkpoint without review |
| `docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/m40_no_mmap_isolated_control_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/m40_llamacpp_runtime_restore_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/virtual_gpu_runtime_restore_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint |
| `docs/agent_tasks/local_cpu_qwen35_runtime_restore_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint; mark CPU fallback rejected |
| `docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md` | untracked | Query Orchestration | valid task card with matching report | preserve in runtime-hygiene checkpoint; final decision artifact |

## Decision

The NVMe checkout is suitable as the active target for future work, but should first receive a narrow checkpoint of this runtime investigation metadata. There is no evidence in this audit that product source changes need to be cleaned or reverted in the NVMe checkout.

## Do Not Touch

- Do not alter HDD preserve dirty files from this NVMe cleanup path.
- Do not delete untracked runtime task cards until their report bundles are safely committed or intentionally archived.
- Do not restart llama.cpp or run GPU probes as part of repo hygiene.
