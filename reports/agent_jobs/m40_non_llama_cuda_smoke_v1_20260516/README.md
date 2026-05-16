# M40 Non-Llama CUDA Smoke

Generated: 2026-05-16T13:06:14+10:00

## Result

Classification: `NON_LLAMA_CUDA_WORKS_M40`

The Tesla M40 can still run CUDA work on this host. A temporary non-llama CUDA program compiled with `nvcc -arch=sm_52` succeeded with M40-only CUDA visibility. It called `cudaMemGetInfo`, allocated device memory, copied inputs, launched a vector-add kernel, synchronized, copied results back, verified them, and reset the device.

This narrows the failure:

- Not supported: "M40 cannot run CUDA at all."
- Still supported: current llama.cpp M40 model-load path is failing.
- Stronger interpretation: the issue is likely llama.cpp build/runtime behavior, llama.cpp interaction with current GPU state, or a specific CUDA API path under llama.cpp model fitting/loading rather than basic CUDA execution.

## Smoke Output

Command:

```bash
timeout 30s env CUDA_VISIBLE_DEVICES=0 /tmp/m40-cuda-smoke-20260516/smoke
```

Output:

```text
device_count=1
device0_name=Tesla M40 24GB
compute_capability=5.2
mem_before_free_mib=24370 total_mib=24472
mem_after_free_mib=24358 total_mib=24472
CUDA_SMOKE_OK
```

The smoke binary was compiled with:

```bash
/usr/bin/nvcc -std=c++14 -arch=sm_52 /tmp/m40-cuda-smoke-20260516/smoke.cu -o /tmp/m40-cuda-smoke-20260516/smoke
```

## GPU Telemetry

Before/around smoke:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 28, P8
200371, /tmp/m40-cuda-smoke-20260516/smoke, GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6, 2
```

After smoke:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 28, P8
```

No `nvidia-smi` timeout was observed.

## Runtime State

This task did not load any llama model and did not touch the virtual/rented GPU tunnel on `18001`.

Existing local router state remained:

```text
:8001 listener: llama-server PID 127293
defunct child: PID 151143
```

## Commands Run

```bash
pwd
git branch --show-current
git rev-parse --short=12 HEAD
git status --short --untracked-files=all
python3 scripts/agent_job_registry.py list-active
command -v nvcc
command -v nvidia-smi
python3 -c 'import torch ...'
ss -ltnp '( sport = :8001 or sport = :18001 or sport = :18011 )'
timeout 8s nvidia-smi --query-gpu=...
timeout 8s nvidia-smi --query-compute-apps=...
python3 scripts/agent_job_contract.py validate docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md
python3 scripts/agent_job_registry.py claim docs/agent_tasks/m40_non_llama_cuda_smoke_v1_20260516.md
/usr/bin/nvcc -std=c++14 -arch=sm_52 /tmp/m40-cuda-smoke-20260516/smoke.cu -o /tmp/m40-cuda-smoke-20260516/smoke
timeout 30s env CUDA_VISIBLE_DEVICES=0 /tmp/m40-cuda-smoke-20260516/smoke
```

## DATA_MISSING

- This did not test large CUDA allocations near 13 GiB.
- This did not test cuBLAS.
- This did not test llama.cpp after clearing the stuck `:8001` router.
- This did not test an older known-good llama.cpp build.

## Next Safe Step

The next useful split is a cuBLAS smoke or a fresh isolated llama.cpp process after stopping the stuck `:8001` router. Since basic CUDA works, the investigation should focus on llama.cpp runtime/build compatibility and cuBLAS/model-load behavior, not basic M40 CUDA availability.
