# APEX/M40 GPU vs Model Differential Probe

Generated: 2026-05-16T12:54:54+10:00

## Answer

The evidence does not point to "just the APEX model" failing. A second already-configured model, `model:qwen2.5-14b-instruct`, also failed on the same CUDA device-memory path.

Best classification: `CUDA_M40_LLAMACPP_RUNTIME_PATH_FAILURE`

That means:

- Not proven: physical M40 is dead.
- Not proven: APEX GGUF alone is corrupt.
- Strongly supported: the current local llama.cpp CUDA path on the M40 is failing when model child processes query/use CUDA memory.

## Evidence

Before the differential probe, `nvidia-smi` returned promptly:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 25, P8
```

No compute apps were listed.

The router reported APEX as stuck from the previous recovery:

```text
model:qwen3.5-35b-a3b-apex status.value = loading
```

One tiny non-APEX request was then run:

```bash
timeout 60s curl -sS -w '\nHTTP_CODE=%{http_code}\nTIME_TOTAL=%{time_total}\nSIZE_DOWNLOAD=%{size_download}\n' \
  -o /tmp/qwen25_m40_tiny_response.json \
  http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer local-openai-key' \
  -d '{"model":"model:qwen2.5-14b-instruct","messages":[{"role":"user","content":"Reply exactly: ok"}],"temperature":0,"max_tokens":8,"stream":false}'
```

The request timed out with exit code 124 and produced an empty response file.

The log showed the non-APEX model started loading on the M40:

```text
model:qwen2.5-14b-instruct
model = /mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf
Device 0: Tesla M40 24GB
main: loading model
```

Then it hit the same CUDA failure path:

```text
CUDA error: unspecified launch failure
current device: 0, in function ggml_backend_cuda_device_get_memory
cudaMemGetInfo(free, total)
```

After the probe:

```text
model:qwen2.5-14b-instruct status.value = loading
model:qwen3.5-35b-a3b-apex status.value = unloaded, failed=true, exit_code=1
PID 151143 [llama-server] <defunct>
M40 memory still 3 MiB
```

## Interpretation

This is broader than APEX. APEX fails, and a smaller Qwen 2.5 model also fails when the child process reaches CUDA memory/device handling.

The M40 is still visible to the NVIDIA driver, and `nvidia-smi` is not hanging in these probes, so the evidence does not prove a fully dead GPU. It points to one of:

- CUDA context/device state is bad for llama.cpp model loads.
- This llama.cpp CUDA build/runtime is incompatible or unstable on the M40.
- The M40/driver is healthy enough for telemetry but failing CUDA work.

## DATA_MISSING

- No CPU-only control run was performed.
- No non-llama CUDA microbenchmark was run.
- No alternate llama.cpp build/runtime was tested.
- No reboot/reset was performed.

Those are the tests needed to separate "GPU hardware/driver" from "llama.cpp build/runtime" more sharply.

## Next Safe Step

Do not keep retrying model loads in the current router. The next clean diagnostic should be one of:

1. Run a timeout-bounded non-llama CUDA smoke test on the M40.
2. Run the same tiny model CPU-only, to prove model file/template health without CUDA.
3. Run a fresh isolated llama.cpp process with CUDA graphs disabled and a tiny/smaller model, not through the stuck router.

If the goal is getting Tenn usable now, demote local APEX/M40 and label it degraded; use a smaller verified CPU/local model or a verified rented GPU path.

## Commands Run

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
python3 scripts/agent_job_registry.py claim docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
timeout 5s curl -sS -i http://127.0.0.1:8001/v1/models
timeout 8s nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,pstate --format=csv,noheader,nounits
timeout 8s nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv,noheader,nounits
tail -n 60 /tmp/llama-server-8001-recovery-20260516.log
timeout 60s curl ... model:qwen2.5-14b-instruct ...
tail -n 80 /tmp/llama-server-8001-recovery-20260516.log
ps -o pid,ppid,pgid,sid,stat,etime,cmd -p 127293,129004,151143
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_gpu_vs_model_differential_probe_v1_20260516.md
```

## Validation

`status.json` is valid JSON.

`check-diff` returned `ok: true`; all current dirty paths were accounted for in the task card. The unrelated news-loader report status path was included only as pre-existing dirt and was not modified by this task.
