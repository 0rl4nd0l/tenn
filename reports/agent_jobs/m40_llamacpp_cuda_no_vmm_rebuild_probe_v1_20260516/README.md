# M40 llama.cpp No-VMM Rebuild Probe Report

## Session Declaration

- Lane: Query Orchestration
- Branch: `fast/dev-storage-v1-20260513-170304`
- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Execution mode: `safe_extension`
- Intended files: task card and `reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/`
- Contested surfaces touched: none
- Collision risk: MEDIUM, because a temporary CUDA binary was built in `/tmp` and one isolated local model-load probe was run.
- Decision: `M40_CUDA_LLAMA_RUNTIME_STILL_FAILS`

## Summary

The throwaway M40-targeted llama.cpp rebuild succeeded, but it did not restore the local M40 runtime. The rebuilt binary used CUDA 11.5, GNU 10.5, `CMAKE_CUDA_ARCHITECTURES=52`, `GGML_CUDA_NO_VMM=ON`, `GGML_CUDA_GRAPHS=OFF`, and reported `VMM: no`. A single isolated Qwen2.5 model-load probe on `:18011` still failed before health came up, at the same llama.cpp CUDA memory-query function.

The failure is therefore not explained by missing `sm_52` build targeting or CUDA VMM alone.

## Confirmed Facts

- Current CUDA toolkit used by local build: nvcc 11.5.119.
- Current driver reported by `nvidia-smi`: 535.288.01, CUDA 12.2 maximum runtime.
- Existing CUDA llama.cpp binary was built from commit `c5a778891` with GNU 10.5 and `CMAKE_CUDA_ARCHITECTURES=52`.
- Existing CUDA build options included `GGML_CUDA_NO_VMM=OFF` and `GGML_CUDA_GRAPHS=ON`.
- First throwaway rebuild using GCC 11 failed during CUDA compilation in GCC 11 C++ headers.
- Retry using `gcc-10` and `g++-10` matched the existing build compiler family and completed successfully.
- Rebuilt binary reported:
  - `Device 0: Tesla M40 24GB, compute capability 5.2, VMM: no`
  - `Device 1: NVIDIA GeForce GT 1030, compute capability 6.1, VMM: no`
  - `version: 8233 (c5a778891)`
  - `built with GNU 10.5.0`
- Isolated Qwen2.5 probe command launched a single model load on `127.0.0.1:18011` with `CUDA_VISIBLE_DEVICES=0`, `--no-mmap`, `--fit off`, and `--n-gpu-layers 999`.
- The isolated probe exited before becoming healthy.
- Probe log reported:
  - `Device 0: Tesla M40 24GB, compute capability 5.2, VMM: no`
  - `CUDA error: all CUDA-capable devices are busy or unavailable`
  - failure in `ggml_backend_cuda_device_get_memory` at `cudaMemGetInfo`
- Kernel journal recorded NVRM Xid 32 for the no-VMM llama-server PID `296411`.
- Earlier in the same investigation, kernel journal also recorded NVRM Xid 69 for previous llama-server CUDA attempts.
- After the failure, a non-llama CUDA smoke still succeeded on the M40:
  - `device0_name=Tesla M40 24GB`
  - `compute_capability=5.2`
  - `CUDA_SMOKE_OK`
- Final `nvidia-smi` remained responsive and showed Tesla M40 visible, 0 MiB used, 0% utilization, P8, 28 C, no compute process.
- Final listener check showed no listener on `:8001`, `:18011`, `:18012`, or `:18001`.
- Cockpit health remained degraded only because `llamacpp` on `:8001` was down; backend, Ollama, Qdrant, Redis, cockpit service, GPU, and host were healthy.

## Web Compatibility Evidence

- NVIDIA documents Maxwell support as CUDA capability 5.0/5.2/5.3 with last CUDA Toolkit support through CUDA 12.x and last driver branch R580.
- NVIDIA CUDA 13 release notes state that CUDA Toolkit 13 removes offline compilation and library support for Maxwell, Pascal, and Volta, while CUDA Toolkit 12.x remains the supported build line for those architectures.
- NVIDIA Maxwell compatibility docs state CUDA 6.5 and later can generate native cubins for second-generation Maxwell compute capability 5.2.
- Local host is still on CUDA 11.5 build tooling and 535-series driver reporting CUDA 12.2, so this failure is not explained by having upgraded into CUDA 13.

## Inferred Facts

- The GPU is not generally dead: non-llama CUDA allocation/kernel/free succeeds after the llama.cpp failures.
- The GGUF model file is not the primary blocker for Qwen2.5: CPU llama.cpp loaded it and returned `ok` in the previous task.
- The local blocker is specific to the current llama.cpp CUDA backend interacting with the M40/driver stack, producing kernel Xids and failing even before inference.
- A pure no-VMM rebuild is insufficient.

## Speculative Claims

- The remaining failure may require an older llama.cpp revision, a different CUDA backend build option set, a driver reset/reboot after Xids, or moving this workload to the virtual/rented GPU path.
- Because the failure occurs during `cudaMemGetInfo`, an in-driver/device state issue triggered by llama.cpp is plausible, but non-llama CUDA success means that is not proven as a whole-GPU failure.

## DATA_MISSING

- No proof that an older llama.cpp revision restores M40 model loading.
- No proof that a reboot or GPU reset would clear the llama.cpp CUDA Xid behavior.
- No proof that the configured `model:qwen3.5-35b-a3b` can be served locally on M40 right now.
- No test was run against `:18001`, because this task explicitly avoided the virtual/rented GPU path.

## Commands Run

Representative commands:

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md
python3 scripts/agent_job_registry.py claim docs/agent_tasks/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516.md
scripts/gpu_process_guard.sh --check
cmake -S /mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp -B /tmp/tenn-m40-llamacpp-no-vmm-build-20260516 -DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DGGML_CUDA_GRAPHS=OFF -DGGML_CUDA_FA=OFF -DCMAKE_CUDA_ARCHITECTURES=52 -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
CC=/usr/bin/gcc-10 CXX=/usr/bin/g++-10 cmake -S /mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp -B /tmp/tenn-m40-llamacpp-no-vmm-build-20260516 -DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DGGML_CUDA_GRAPHS=OFF -DGGML_CUDA_FA=OFF -DCMAKE_CUDA_ARCHITECTURES=52 -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-10 -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
cmake --build /tmp/tenn-m40-llamacpp-no-vmm-build-20260516 --target llama-server -j 4
/tmp/tenn-m40-llamacpp-no-vmm-build-20260516/bin/llama-server --version
setsid env CUDA_VISIBLE_DEVICES=0 GGML_CUDA_DISABLE_GRAPHS=1 LD_LIBRARY_PATH=/tmp/tenn-m40-llamacpp-no-vmm-build-20260516/bin /tmp/tenn-m40-llamacpp-no-vmm-build-20260516/bin/llama-server --host 127.0.0.1 --port 18011 --model /mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf --alias model:qwen2.5-14b-no-vmm-control --ctx-size 8192 --batch-size 1024 --ubatch-size 512 --main-gpu 0 --n-gpu-layers 999 --parallel 1 --threads 4 --no-mmap --fit off --api-key local-openai-key
journalctl -k --since '20 minutes ago' --no-pager
timeout 30s env CUDA_VISIBLE_DEVICES=0 /tmp/m40-cuda-smoke-20260516/smoke
timeout 15s nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,pstate --format=csv,noheader,nounits
curl -sS --max-time 5 http://127.0.0.1:8081/api/cockpit/health
```

## Runtime Health Before and After

- Before: normal `:8001` llama.cpp endpoint was already down after the earlier cleanup.
- During: temporary `:18011` no-VMM CUDA probe exited before health.
- After: no llama-server listener remains on `:8001`, `:18011`, `:18012`, or `:18001`; Cockpit is degraded due to `llamacpp` down.

## GPU Health Before and After

- Before: M40 visible, 0 MiB used, no compute process.
- During no-VMM llama.cpp probe: llama-server failed and kernel logged NVRM Xid 32.
- After: M40 visible, 0 MiB used, no compute process, non-llama CUDA smoke passed.

## Concurrent Jobs Observed

- `overview_news_commentary_approval_v1_20260516`, lane Reporting, separate worktree, no runtime/query overlap.
- Earlier in this task, `memory_contamination_past_entries_cleanup_v1_20260516`, lane Memory, separate worktree, no runtime/query overlap.

## Collision Risks

- Runtime collision risk was MEDIUM because temporary CUDA build/probe touched GPU state and produced kernel Xids.
- Repo collision risk was LOW because only task/report artifacts were written in the NVMe worktree.
- No source code, checked-in config, runtime config, aliases, model files, DBs, Qdrant, news stores, or memory stores were edited.

## Recommended Next Safe Step

Do not rely on local M40 llama.cpp CUDA for Tenn chat right now. The safe choices are:

1. Restore service availability through an explicit degraded path, such as CPU router on `:8001`, with clear degraded labeling and no alias lying.
2. Wire and validate the virtual/rented GPU path intentionally, since `:18001` is a valid virtual GPU path but was out of scope here.
3. If local M40 acceleration remains required, run a separate task to test an older known-good llama.cpp revision or driver-reset/reboot recovery, with one bounded model-load attempt per variant.
