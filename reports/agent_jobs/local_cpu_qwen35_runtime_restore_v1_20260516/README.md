# Local CPU Qwen3.5 Runtime Restore Report

## Decision

`CPU_QWEN35_RUNTIME_FAILED`

## Summary

This task was intentionally aborted after user correction: CPU fallback is a regression for the active goal. The temporary CPU Qwen3.5 server was stopped and `:8001` was left unbound. No source code, runtime config, model files, aliases, databases, Qdrant, news stores, or memory stores were edited.

## Evidence

- Started temporary CPU llama.cpp server on `:8001` with alias `model:qwen3.5-35b-a3b`.
- The process began loading `/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf`.
- Host memory pressure was high during load: about 21 GiB RSS and swap use increased.
- User corrected that CPU fallback is regression.
- The CPU process was terminated.
- Final listener check showed no listener on `:8001`.

## Next Step

Continue CUDA-only M40 investigation and remediation. Do not use CPU fallback as the restore path for this goal.
