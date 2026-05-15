# Vast Rented GPU Runtime Setup

Use this setup only when a task explicitly approves a paid Vast rental. For dry runs, search offers and inspect CLI help only.

## Required Runtime Shape

Tenn needs an OpenAI-compatible llama.cpp endpoint, not just a GPU host.

- Remote endpoint: `http://127.0.0.1:8001/v1/models`
- Local tunnel endpoint: `http://127.0.0.1:18001/v1/models`
- Tenn env var: `TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001`

`nvidia-smi` is useful hardware evidence, but it is not runtime evidence.

## Candidate Checklist

Before renting, confirm:

- Runtime mode: `llama.cpp OpenAI-compatible server`
- Image/template: `ghcr.io/ggml-org/llama.cpp:server-cuda` or equivalent
- `llama-server`: present
- GGUF model: present or mounted
- Onstart command: binds `--host 127.0.0.1 --port 8001`
- Disk: enough for model, runtime files, and logs
- `/v1/models`: expected within 2 minutes
- Cost controls: hourly cap, total budget, runtime minutes, destroy deadline
- Smoke prompt: synthetic no-data prompt

Avoid `nvidia/cuda:*devel*` images for smoke tests unless the task is explicitly runtime provisioning.

## Rental Command Shape

Only after exact user confirmation:

```bash
vastai create instance <OFFER_ID> \
  --image <IMAGE> \
  --disk <GB> \
  --ssh --direct \
  --onstart-cmd '<ONSTART_CMD>'
```

The onstart command must start a local-only llama.cpp server:

```bash
llama-server --host 127.0.0.1 --port 8001 --model <MODEL_PATH>
```

Do not expose `llama-server` publicly unless the user explicitly requests and secures that path.

## Immediate Smoke

On the remote instance:

```bash
nvidia-smi
curl -m 10 -sS http://127.0.0.1:8001/v1/models
```

If remote `/v1/models` fails and no fast already-present runtime/model exists, stop and recommend destroy rather than spending time building or downloading.

Open the local tunnel:

```bash
export TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001

ssh -i ~/.ssh/vastai_nopass \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=accept-new \
  -p <VAST_SSH_PORT> \
  -L18001:localhost:8001 \
  root@<VAST_SSH_HOST>
```

Then locally:

```bash
curl -m 10 -sS http://127.0.0.1:18001/v1/models
```

## Tenn Smoke

Use synthetic prompts only. Confirm local default routing remains local, explicit `rented_gpu` uses the remote endpoint only when configured, `auto` light prompts remain local, `auto` heavy prompts use remote only when configured and heavy criteria are present, bad endpoints fail clearly, and no real Tenn data is sent remote.

## Destroy Guard

Require exact confirmation before destroy:

```text
Confirm destroy Vast instance <INSTANCE_ID>.
```

Recommend destroy when the runtime endpoint is absent, the model is absent, the cost window is approaching, or smoke is complete.

## Previous Failure Pattern

The failure to avoid is "GPU verified is not runtime verified": SSH worked, `nvidia-smi` showed an RTX 4090, but the instance was a bare CUDA image with no `llama-server`, no `llama-cli`, no GGUF model, no useful onstart command, and no listener on `127.0.0.1:8001`. The correct gate is `/v1/models`, first remote and then through the local tunnel.
