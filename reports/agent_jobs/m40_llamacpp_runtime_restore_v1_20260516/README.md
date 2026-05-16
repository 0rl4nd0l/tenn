# M40 llama.cpp Runtime Restore Report

## Decision

`LOCAL_LLAMA_PARTIAL_RESTORE_ONLY`

The task cleared the stuck `:8001` llama-server process and proved that Qwen2.5 can run through the CPU llama.cpp binary, but it did not restore the configured Tenn local llama.cpp endpoint. The normal endpoint remained down after cleanup because the CUDA llama.cpp path still failed on the M40.

## Key Evidence

- Stuck `:8001` process group was removed.
- M40 VRAM returned to 0 MiB and `nvidia-smi` stayed responsive.
- Fresh CUDA Qwen2.5 attempts on a temporary port failed at `ggml_backend_cuda_device_get_memory` / `cudaMemGetInfo`.
- CPU Qwen2.5 control on `:18012` returned HTTP 200 with content `ok`, 2 completion tokens, 35 total tokens, and about 2.17s total time.
- CPU control was stopped before closeout to avoid leaving an unintegrated fallback running.
- Backend config still pointed to `http://127.0.0.1:8001` with `llm_model=model:qwen3.5-35b-a3b`.
- Cockpit health reported degraded because `llamacpp` on `:8001` was down.

## Conclusion

This was not an APEX-only failure and not a Qwen2.5 model-file failure. The local failure surface is the llama.cpp CUDA path on the M40. The next safe step was a separate no-VMM rebuild probe, which is recorded under `reports/agent_jobs/m40_llamacpp_cuda_no_vmm_rebuild_probe_v1_20260516/`.
