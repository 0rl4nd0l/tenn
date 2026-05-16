# M40 No-Mmap Isolated Control

Generated: 2026-05-16T13:03:00+10:00

## Result

Classification: `NO_MMAP_STILL_FAILS_CUDA`

Important correction: `127.0.0.1:18001` is the virtual/rented GPU tunnel path. Treating it as an invalid stale listener was wrong. The local isolated control was moved to `127.0.0.1:18011`.

The temporary `18011` process did not remain running and did not bind a listener. Its log still captured the decisive result: with `--no-mmap`, CUDA graphs disabled, M40-only CUDA visibility, and the smaller Qwen2.5 model, llama.cpp failed at the same CUDA memory query path.

## Evidence

Temporary command:

```bash
setsid env \
  CUDA_VISIBLE_DEVICES=0 \
  GGML_CUDA_DISABLE_GRAPHS=1 \
  LD_LIBRARY_PATH=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin \
  /mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server \
  --host 127.0.0.1 \
  --port 18011 \
  --model /mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf \
  --alias model:qwen2.5-14b-no-mmap-control \
  --ctx-size 8192 \
  --batch-size 1024 \
  --ubatch-size 512 \
  --main-gpu 0 \
  --n-gpu-layers 999 \
  --parallel 1 \
  --threads 4 \
  --no-mmap \
  --api-key local-openai-key
```

Log finding from `/tmp/m40-no-mmap-control-18011.log`:

```text
ggml_cuda_init: found 1 CUDA devices:
  Device 0: Tesla M40 24GB, compute capability 5.2, VMM: yes
main: loading model
srv load_model: loading model '/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf'
common_init_result: fitting params to device memory
CUDA error: unspecified launch failure
current device: 0, in function ggml_backend_cuda_device_get_memory
cudaMemGetInfo(free, total)
```

Port/process cleanup check:

```text
:18011 listener: none
temporary PID 182858: not running
:8001 remains the existing router PID 127293
```

## Interpretation

The old `LLAMA_SERVER_MMAP=0` fix is no longer sufficient in the current live GPU state. The failure now reproduces in a fresh isolated process with:

- non-APEX Qwen2.5 model
- direct llama.cpp process, not router child
- `--no-mmap`
- CUDA graphs disabled
- M40-only CUDA visibility

This strengthens the conclusion that the current failure is in the M40 CUDA runtime path, driver/GPU state, or llama.cpp CUDA build compatibility. It is not explained by APEX alone and is not explained by mmap alone.

It still does not prove the physical M40 is permanently dead, because `nvidia-smi` can see it and return. But the card is currently failing real CUDA memory queries used by llama.cpp.

## DATA_MISSING

- No non-llama CUDA microbenchmark was run.
- No reboot/GPU reset was performed.
- No alternate older llama.cpp build was tested.
- No CPU-only model control was run in this task.

## Next Safe Step

Stop retrying llama model loads on the M40 until the GPU state is reset or tested outside llama.cpp.

The next diagnostic should be one of:

1. A timeout-bounded non-llama CUDA smoke test on the M40.
2. A host reboot/GPU reset, then one isolated no-mmap Qwen2.5 control.
3. An older known-good llama.cpp build/runtime with CUDA 11.x and `sm_52` explicitly targeted.

For Tenn availability, demote/label local M40 chat as degraded and use either CPU/local smaller fallback or a verified virtual/rented GPU path.
