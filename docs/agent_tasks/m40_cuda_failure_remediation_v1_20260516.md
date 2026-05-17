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
  - scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh
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

## Manual recovery update - 2026-05-17

User manual testing corrected the earlier investigation result. The Tesla M40 is not inherently unusable for llama.cpp or llama-server on this host. The prior conclusion was premature because it over-indexed on a failing server/runtime path instead of first reconstructing a minimal known-good CLI path and then a conservative server path.

Confirmed manual recovery evidence:

- M40 topology and PCIe were sane after cold boot: CPU-lane topology `00:03.1-[2d] -> Tesla M40`, x16 width, ASPM disabled, no AER errors, and NVIDIA driver loaded cleanly.
- M40 llama-cli passed with Mistral 7B on CUDA0 at `--n-gpu-layers 1`, `8`, and `32`.
- M40 llama-cli passed with Qwen2.5 14B on CUDA0 at `--n-gpu-layers 1`, `8`, `16`, and `32`.
- Short outputs in those CLI tests came from `--n-predict 4`, not GPU failure.
- M40 llama-server passed with the conservative Qwen2.5 14B command preserved in `scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh`.
- The conservative server path returned `/health` status ok and a `/v1/chat/completions` response with assistant content `ok` on `127.0.0.1:18001`.
- `nvidia-smi` showed the llama-server process resident on the Tesla M40 at about 2611 MiB VRAM during the successful server smoke.
- The boot kernel log tail showed no fresh NVIDIA Xid after the successful server request.

Corrected classification:

- `M40_LLAMA_CPP_AND_SERVER_RECOVERED_CONSERVATIVE_QWEN25`

Corrected diagnosis:

- M40 works for llama.cpp and llama-server.
- The earlier failure was configuration/runtime-path specific, not proof that the M40 or M40 CUDA path was inherently broken.
- Suspect unsafe server-path variables include auto parallelism / `n_parallel=4`, `kv_unified=true`, prompt cache enabled, `n_slots=4`, `ctx-size 2048`, fit/device-memory behavior, and wrong device selection risk.

Future guardrail:

Do not declare the M40 unusable unless both minimal llama-cli and conservative llama-server smoke paths fail after a clean boot. Future runtime investigations must isolate variables in this order: hardware visibility, clean dmesg/kernel log, minimal CLI, CLI with increasing layers, conservative server, then production-like server.
