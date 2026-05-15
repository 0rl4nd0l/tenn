# Rented GPU Runtime Workflow

This workflow is for using a rented Vast.ai GPU as a Tenn chat runtime. The success target is a working remote OpenAI-compatible llama.cpp server, not a bare GPU host.

## Correct Success Gate

`nvidia-smi` proves only that the GPU is visible. It does not prove Tenn can use the instance.

Runtime success requires both checks:

```bash
curl -m 10 -sS http://127.0.0.1:8001/v1/models
curl -m 10 -sS http://127.0.0.1:18001/v1/models
```

The first command runs on the remote instance. The second runs locally after the SSH tunnel is open.

## Pre-Rental Gates

Before renting, verify:

1. Runtime mode is `llama.cpp OpenAI-compatible server`.
2. Remote bind is `127.0.0.1:8001`, not public internet.
3. Local tunnel is `127.0.0.1:18001 -> remote localhost:8001`.
4. Image/template includes `llama-server`, a `.gguf` model or mounted model volume, a startup/onstart command, and enough disk.
5. If anything is not preloaded, setup can finish within 5-10 minutes without broad build/download, or the user has explicitly approved runtime provisioning.
6. Hourly cost, hard destroy time, and exact destroy confirmation text are known.
7. The smoke prompt is synthetic and contains no Tenn data.

## Image Criteria

Prefer `ghcr.io/ggml-org/llama.cpp:server-cuda`, `ghcr.io/ggml-org/llama.cpp:full-cuda`, or an equivalent image that already has `llama-server`.

Require an onstart command equivalent to:

```bash
llama-server --host 127.0.0.1 --port 8001 --model <MODEL_PATH>
```

Avoid bare `nvidia/cuda:*devel*` images for runtime smoke. They are acceptable only for an explicitly approved provisioning task, not for a quick Tenn runtime test.

## Post-Rental Gates

Within 2 minutes of rental, verify:

```bash
ssh ...
nvidia-smi
curl -m 10 -sS http://127.0.0.1:8001/v1/models
```

If `/v1/models` fails and no fast already-present runtime/model exists, stop and recommend destroy. The previous failure pattern was GPU verified but runtime not verified: SSH and `nvidia-smi` worked, but there was no `llama-server`, no `.gguf`, no useful onstart, and no `/v1/models`.

## Tunnel

Use a localhost tunnel:

```bash
export TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001

ssh -i ~/.ssh/vastai_nopass \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=accept-new \
  -p <VAST_SSH_PORT> \
  -L18001:localhost:8001 \
  root@<VAST_SSH_HOST>
```

Then verify locally:

```bash
curl -m 10 -sS http://127.0.0.1:18001/v1/models
```

## Tenn Smoke Sequence

Use only synthetic prompts.

Check:

- Local default remains local.
- Explicit `rented_gpu` routes remote only when `TENN_RENTED_GPU_LLAMACPP_URL` is configured.
- `auto` light/simple prompts stay local.
- `auto` heavy prompts route remote only when the endpoint is configured and heavy criteria are present.
- Bad endpoint fails clearly.
- No real Tenn data is sent remote.

## Cost And Destroy Policy

Require exact user confirmation before destroy:

```text
Confirm destroy Vast instance <INSTANCE_ID>.
```

Proactively recommend destroy when `/v1/models` cannot be reached quickly, runtime/model is absent, the cost window is approaching, or smoke is complete.

Every attempt report must include instance ID, GPU/model, image/template, price/hr, SSH host/port, created time, destroy deadline, remote and local `/v1/models` results, exact model IDs, synthetic generation result if run, whether any real data was sent remote, destroy recommendation, and DATA_MISSING entries.
