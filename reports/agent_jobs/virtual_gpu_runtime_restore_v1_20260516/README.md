# Virtual GPU Runtime Restore Report

## Decision

`VIRTUAL_GPU_UNAVAILABLE`

## Summary

The intended virtual GPU path is `127.0.0.1:18001 -> remote localhost:8001`, with `TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001`. That path is not currently available. No Vast instances are active, and a replacement SSH tunnel to the last observed host/port failed with connection refused.

During this task a transient SSH tunnel existed on `:8002` and briefly returned llama.cpp `/health` and `/v1/models` for `qwen2.5-14b-instruct`, but the tunnel exited before a tiny chat request could run. `:8002` is also not the documented Tenn rented-GPU endpoint.

Separately, `:8001` respawned while this task was running, but that did not restore functionality. The parent router answers `/health`; the child process for `model:qwen3.5-35b-a3b-apex` is defunct, and `/tmp/llama-server-8001.log` shows the same M40 CUDA tensor upload failure.

## Confirmed Facts

- `:18001` was not listening at task start.
- Existing SSH tunnel on `:8002` was `127.0.0.1:8002 -> remote 127.0.0.1:8001` through `root@ssh8.vast.ai:16000`.
- `:8002` briefly returned:
  - `/health`: `{"status":"ok"}`
  - `/v1/models`: `qwen2.5-14b-instruct`
- The `:8002` tunnel exited before the tiny chat request, producing connection refused.
- Attempted replacement tunnel on `:18001` failed:
  - `ssh: connect to host ssh8.vast.ai port 16000: Connection refused`
- `vastai show instances-v1 --raw` returned zero instances.
- Backend config still reports rented GPU not configured:
  - `rented_gpu.configured=false`
  - `TENN_RENTED_GPU_LLAMACPP_URL is not set`
- `:8001` later listened again with the CUDA router parent PID `324723`.
- `:8001 /health` returned HTTP 200.
- `:8001 /v1/models` showed `model:qwen3.5-35b-a3b-apex` in `loading` status.
- Child PID `327685` for APEX was defunct.
- `/tmp/llama-server-8001.log` showed `CUDA error: unspecified launch failure` during `ggml_backend_cuda_buffer_set_tensor` / `cudaMemcpyAsync`.

## Inferred Facts

- Virtual/rented GPU routing cannot be restored without a new working tunnel or a new paid Vast instance.
- The transient `:8002` endpoint is not stable enough to route Tenn chat.
- `:8001` health is not sufficient evidence of a usable local runtime because router health can stay green while the model child is defunct.

## DATA_MISSING

- No active Vast instance ID exists to reconnect.
- No current SSH host/port for a healthy rented runtime exists.
- No current virtual GPU `/v1/chat/completions` success exists.

## Collision and Safety

- No source code, runtime config, model aliases, databases, Qdrant, news stores, or memory stores were edited.
- No paid instance was started or rented.
- No real Tenn data was sent to the virtual endpoint; only health/model probes and a synthetic tiny prompt were attempted.

## Recommended Next Step

If full remote acceleration is required, rent/provision a new Vast runtime only after explicit confirmation of offer, price, model/runtime image, disk, and destroy deadline. For immediate no-spend service restoration, use a clearly labeled CPU-degraded local `:8001` path.
