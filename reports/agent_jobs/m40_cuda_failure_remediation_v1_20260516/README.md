# M40 CUDA Failure Remediation

## Summary

Classification: `M40_CUDA_LLAMACPP_BACKEND_FAULT` with host reset/BIOS follow-up required.

The attempted CPU fallback was stopped and not used as a remediation. The local M40 can still run basic CUDA and can run a reduced-layer Qwen2.5 llama.cpp server, but the configured larger Qwen3.5/Qwen3.5-A3B path cannot be restored on the current host state with the current llama.cpp build or the tested older `b8209` build.

## Confirmed facts

- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD: `2b2197e0def9`
- Backend `:8000` stayed healthy.
- `:8001` was left unbound; no CPU fallback process was left running.
- M40 was visible to `nvidia-smi`, with 0 MiB VRAM used at closeout.
- Standalone CUDA smoke on the M40 passed after failures.
- Qwen2.5 reduced-layer CUDA probe loaded on the M40 and returned `ok`:
  - model: `model:qwen2.5-14b-instruct`
  - HTTP 200
  - prompt tokens: 33
  - completion tokens: 2
  - total time: about 4.0s
  - M40 residency: about 3.5 GiB during load
- Current llama.cpp `b8233/c5a778891` failed Qwen3.5 CUDA loads with `CUDA error: unspecified launch failure`.
- Temporary older llama.cpp `b8209/872646b30` was built under `/tmp` with:
  - `CMAKE_CUDA_ARCHITECTURES=52`
  - `GGML_CUDA_NO_VMM=ON`
  - `GGML_CUDA_GRAPHS=OFF`
  - `GGML_CUDA_FA=OFF`
  - GCC/G++ 10 host compiler
- The older `b8209` Qwen3.5 16-layer probe still failed after reaching about 7.9 GiB M40 model buffer.
- A lower 4-layer `b8209` retry failed immediately after the previous Xid, consistent with the M40 CUDA context needing reset.
- Non-interactive `sudo nvidia-smi --gpu-reset -i 1` was blocked by password requirement.

## Inferred facts

- This is not a total M40/CUDA failure: standalone CUDA and Qwen2.5 llama.cpp CUDA both worked.
- This is not solved by simply using the nearest older Qwen3.5-aware llama.cpp tag.
- The larger model path is failing in the Qwen3.5/qwen35moe + llama.cpp CUDA backend on Maxwell/M40.
- BIOS/IOMMU/PCIe configuration may amplify the failure, but it is not the sole explanation because Qwen2.5 CUDA succeeds on the same M40.

## Speculative claims

- A host reboot or privileged M40 GPU reset may be required before another meaningful Qwen3.5 probe.
- BIOS settings worth checking after a shutdown window: IOMMU disabled or passthrough, Above 4G Decoding enabled, PCIe slot forced Gen3, and M40 placed in a CPU-lane x16 slot if possible.
- A different older tag may behave differently, but anything older than `b8209` may not have the needed Qwen3.5 model-type support.

## DATA_MISSING

- No current proof that any available local llama.cpp build can load Qwen3.5 on this M40 after the Xid state.
- No privileged GPU reset was possible.
- No BIOS setting readout was available from the OS beyond DMI, PCIe link, IOMMU groups, and kernel logs.
- No durable `:8001` restore was performed.

## Commands and observations

- `git status --short --untracked-files=all`: unchanged pre-existing task/report dirt plus this task card/report.
- `timeout 8s /tmp/m40-cuda-smoke-20260516/smoke`: `CUDA_SMOKE_OK`.
- Current `b8233` Qwen3.5 reduced-layer probes:
  - failed at `cudaMemGetInfo` or `cudaEventSynchronize`
  - kernel logged M40 `Xid 69` and `Xid 32`
- Qwen2.5 reduced-layer probe:
  - command used `--n-gpu-layers 16 --ctx-size 4096 --batch-size 256 --ubatch-size 128 --no-mmap -fa off --no-op-offload`
  - `/health` returned ok
  - tiny chat returned `ok`
- Older source build:
  - `git worktree add --detach /tmp/tenn-m40-llamacpp-b8209-src-20260516 b8209`
  - initial GCC 11 build failed with CUDA 11.5 host compiler errors
  - rebuild with GCC/G++ 10 succeeded
- Older `b8209` Qwen3.5 16-layer probe:
  - `CUDA0 model buffer size = 7923.38 MiB`
  - failed at `cudaEventSynchronize`
- Older `b8209` Qwen3.5 4-layer retry:
  - failed at `cudaMemGetInfo`
  - likely after previous Xid left the M40 CUDA context unhealthy for llama.cpp
- `sudo -n timeout 15s nvidia-smi --gpu-reset -i 1`: failed, password required.

## Runtime state

- Before: `:8001` unhealthy/unbound after stopping CPU fallback.
- After: `:8001` intentionally left unbound; no fallback was started.
- Backend `:8000`: healthy.
- Cockpit route probe was not repeated after the M40 restore failed; earlier backend health remained ok.

## GPU state

- M40 visible before and after.
- Closeout M40 state: 0 MiB used, no compute processes, `nvidia-smi` responsive.
- Kernel logs include M40 `Xid 32`/`Xid 69` from Qwen3.5 llama.cpp probes.

## Concurrent jobs observed

- This job: `m40_cuda_failure_remediation_v1_20260516`.
- No direct overlapping active job was observed during the latest closeout check.

## Collision risks

- Runtime collision risk was medium because only temp ports and `:8001` process state were touched.
- No source code, databases, Qdrant, memory stores, model files, or runtime config files were edited.
- Temporary source/build directories were created under `/tmp`.

## Decision

Do not claim Qwen3.5/APEX restored on M40.

Post-reboot continuation: the host was later observed with a clean, idle M40 and a fresh `:8001` router, so the recommended single temp-port `b8209` Qwen3.5 reduced-layer probe was rerun on `:18011`. It failed before health with the same CUDA failure at `ggml_backend_cuda_device_get_memory` / `cudaMemGetInfo` and logged another M40 `Xid 69`.

Recommended next safe step: stop trying local M40 Qwen3.5/APEX loads on this host. The older `b8209` path no longer restores the larger model after reboot. To restore full functionality without a model-quality regression, use a newer GPU or a verified `:18001` virtual/rented GPU endpoint. If local-only service availability is more important than full functionality, use a clearly labeled degraded smaller-model path; do not present that as restored APEX/Qwen3.5 capability.

Project Memory save recommendation: SAVE_RECOMMENDED.

## Post-Reboot b8209 Continuation - 2026-05-16T18:31:59+10:00

### Session declaration

```text
Lane: Query Orchestration
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: SAFE EXTENSION, bounded temp-build/temp-port runtime probe
Intended files: existing task card and reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/
Contested surfaces touched: local llama.cpp runtime/GPU only
Collision risk: MEDIUM, because one isolated model-load probe touched the M40 CUDA path
Decision: older llama.cpp b8209 does not restore Qwen3.5 on the M40
```

### Current-turn preflight

- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git branch --show-current`: `fast/dev-storage-v1-20260513-170304`
- `git rev-parse --short=12 HEAD`: `2b2197e0def9`
- Current dirty state before report update included unrelated `cockpit-ui/next-env.d.ts`, unrelated `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json`, and untracked M40 task cards.
- Active registry jobs were unrelated Financial Truth / Reporting worktrees, with no direct Query Orchestration runtime overlap.
- `scripts/gpu_process_guard.sh --check` returned clean before the probe.

### Confirmed facts

- The rebuilt older binary was created under `/tmp/tenn-m40-llamacpp-b8209-build-20260516b` from tag `b8209`, commit `872646b30`.
- Build options used CUDA 11.5, GCC/G++ 10.5, `CMAKE_CUDA_ARCHITECTURES=52`, `GGML_CUDA_NO_VMM=ON`, `GGML_CUDA_GRAPHS=OFF`, and `GGML_CUDA_FA=OFF`.
- `CUDA_VISIBLE_DEVICES=0 /tmp/tenn-m40-llamacpp-b8209-build-20260516b/bin/llama-server --version` reported one CUDA device: `Tesla M40 24GB`, compute capability `5.2`, `VMM: no`.
- The temp probe used `127.0.0.1:18011`, model `/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf`, alias `model:qwen3.5-35b-a3b-b8209-reduced`, `--n-gpu-layers 16`, `--ctx-size 16384`, `--batch-size 512`, `--ubatch-size 256`, `--no-mmap`, and `--fit off`.
- The temp probe process aborted before `/health` became available.
- The log showed:
  - `CUDA error: unspecified launch failure`
  - `current device: 0, in function ggml_backend_cuda_device_get_memory`
  - `cudaMemGetInfo(free, total)`
- Kernel logs showed `NVRM: Xid (PCI:0000:2d:00): 69, pid=119806, name=llama-server`.
- `nvidia-smi` stayed responsive after the failure and showed the M40 at `3 MiB / 24576 MiB`, no compute processes.
- Live `:8001` was not intentionally restarted or replaced by the b8209 build.
- Live `:8001` currently has router PID `79669` and a defunct child PID `84334` from an APEX load attempt recorded in `/tmp/llama-server-8001.log`.
- `:8000`, `:8081`, and `:18001` were not listening during the current continuation checks.

### Inferred facts

- Reboot/clean initial M40 state did not make the older `b8209` Qwen3.5 reduced-layer path usable.
- This is not a CPU limitation: the failing call happens inside llama.cpp CUDA device memory discovery before generation.
- This is not solved by the older nearby Qwen3.5-aware llama.cpp tag, no-VMM build, disabled CUDA graphs, no mmap, or reduced 16-layer offload.
- The local M40 remains visible and `nvidia-smi` responsive, but it is not reliable for the Qwen3.5/APEX llama.cpp path.

### DATA_MISSING

- No successful Qwen3.5/APEX local-M40 response exists after reboot.
- No verified `:18001` virtual/rented GPU endpoint exists in this continuation.
- The temporary non-llama CUDA smoke binary from the earlier task was no longer present under `/tmp`, so a fresh post-failure non-llama smoke was not rerun.
- No privileged GPU reset was available.

### Commands added in this continuation

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
python3 scripts/agent_job_registry.py claim docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md
git -C /mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp worktree add --detach /tmp/tenn-m40-llamacpp-b8209-src-20260516b b8209
CC=/usr/bin/gcc-10 CXX=/usr/bin/g++-10 cmake -S /tmp/tenn-m40-llamacpp-b8209-src-20260516b -B /tmp/tenn-m40-llamacpp-b8209-build-20260516b -DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DGGML_CUDA_GRAPHS=OFF -DGGML_CUDA_FA=OFF -DCMAKE_CUDA_ARCHITECTURES=52 -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-10 -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
cmake --build /tmp/tenn-m40-llamacpp-b8209-build-20260516b --target llama-server -j 4
env CUDA_VISIBLE_DEVICES=0 /tmp/tenn-m40-llamacpp-b8209-build-20260516b/bin/llama-server --version
setsid env CUDA_VISIBLE_DEVICES=0 GGML_CUDA_DISABLE_GRAPHS=1 LD_LIBRARY_PATH=/tmp/tenn-m40-llamacpp-b8209-build-20260516b/bin /tmp/tenn-m40-llamacpp-b8209-build-20260516b/bin/llama-server --host 127.0.0.1 --port 18011 --model /mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf --alias model:qwen3.5-35b-a3b-b8209-reduced --chat-template-file /home/l4nd0/.config/tenn/qwen3.5-chat-template.jinja --ctx-size 16384 --batch-size 512 --ubatch-size 256 --main-gpu 0 --n-gpu-layers 16 --parallel 1 --threads 4 --no-mmap --fit off --api-key local-openai-key
journalctl -k -b --since '10 minutes ago' --no-pager
nvidia-smi
scripts/gpu_process_guard.sh --json
```

## Full-Function Restore Gate - 2026-05-16T18:36:55+10:00

### Objective audit

Concrete success criteria for "restore full functionality without regression":

- Tenn chat must have a working OpenAI-compatible llama.cpp endpoint.
- The configured model path must remain APEX/Qwen3.5-class, not CPU fallback and not a smaller local model presented as equivalent.
- The endpoint must pass `/v1/models` and a synthetic tiny generation.
- Cockpit/backend config must expose the endpoint as healthy.
- No source/config/model/data-store mutation should be hidden inside the recovery.

Current evidence does not satisfy those criteria.

### Current live state

- `git rev-parse --short=12 HEAD`: `87562bf0b026`
- Backend `:8000` is healthy.
- `:8001` router is listening, but `/v1/models` reports `model:qwen3.5-35b-a3b-apex` as `failed`.
- M40 is visible and idle: `3 MiB / 24576 MiB`, no compute processes.
- `:18001` virtual/rented GPU endpoint is not listening.
- `vastai show instances-v1 --raw` reports `total_instances: 0`.
- `/api/cockpit/config` reports:
  - `llm_model`: `model:qwen3.5-35b-a3b-apex`
  - `llm_endpoint`: `http://127.0.0.1:8001`
  - `runtime_target`: `local`
  - `rented_gpu.configured`: `false`
  - `rented_gpu.error`: `TENN_RENTED_GPU_LLAMACPP_URL is not set`

### Remote restore feasibility

- The exact APEX GGUF is publicly resolvable at Hugging Face:
  - `https://huggingface.co/mudler/Qwen3.5-35B-A3B-APEX-GGUF/resolve/main/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`
  - `Content-Length: 17293089248`
- Local model sizes:
  - `Qwen3.5-35B-A3B-APEX-I-Compact.gguf`: `17293089248` bytes
  - `Qwen3.5-35B-A3B-Q4_K_M.gguf`: `22016023168` bytes
  - `qwen2.5-14b-instruct-q4_k_m.gguf`: `8988110976` bytes
- Vast has candidate GPU offers in dry-run search, including verified 24 GB and 48 GB options, but no instance is currently rented.

### Decision

There is no no-spend, no-regression local remediation left in the current state. Full functionality now requires provisioning a verified remote/newer-GPU llama.cpp runtime on `127.0.0.1:18001 -> remote localhost:8001`, or installing a newer local GPU.

Paid provisioning must not proceed without explicit confirmation of offer, price, disk, runtime window, model download, and destroy deadline.

### Offer refresh - 2026-05-16T18:38:22+10:00

- `vastai show instances-v1 --raw`: `total_instances: 0`
- Previously suggested offer `26051046` was no longer returned by `vastai search offers 'id=26051046 rentable=true'`.
- Current cheapest verified 48 GB candidate from dry-run search:
  - Offer ID: `26051042`
  - GPU: `RTX 6000Ada`
  - VRAM: `49140` MiB
  - Price with 80 GB storage: about `$0.542/hr`
  - Region: Taiwan
  - Direct ports: `124`
  - Reliability: `0.9982534`
  - Driver: `570.211.01`
  - Disk available: `93.25` GB
- APEX GGUF URL still resolves with `Content-Length: 17293089248`.

Updated approval phrase:

```text
Confirm rent Vast offer 26051042 for up to 60 minutes, max spend $0.60, download the APEX GGUF, and destroy if runtime smoke fails.
```

### Prepared provisioning plan

This plan is intentionally not executed without approval.

Confirmed rental fields:

- Offer: `26051042`
- GPU: `RTX 6000Ada`
- VRAM: 48 GB
- Price cap: `$0.60` for up to 60 minutes

## Local-M40-Only Continuation - 2026-05-16T19:31:00+10:00

### Session declaration

```text
Lane: Query Orchestration
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: SAFE EXTENSION, local runtime remediation only
Intended files: reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/
Contested surfaces touched: canonical local llama.cpp user service on :8001, Ollama embedding runner state
Collision risk: MEDIUM, because this touched the local M40 runtime process state
Decision: local M40 APEX is still not restored; stop further APEX loads until privileged GPU reset or host reboot
```

### Confirmed facts

- User explicitly redirected away from Vast/remote GPU and back to local M40 repair.
- Task card validation still passed for `docs/agent_tasks/m40_cuda_failure_remediation_v1_20260516.md`.
- Active registry only showed a stale unrelated Reporting job; this M40 remediation task was claimed narrowly.
- `scripts/gpu_process_guard.sh --check` returned exit 0 before the local continuation.
- Live launcher pinning is correct in practice:
  - live `:8001` process had `CUDA_VISIBLE_DEVICES=0`
  - `llama-server --version` with that environment reported one CUDA device: `Tesla M40 24GB`
  - live process file descriptors pointed at `/dev/nvidia1`, the M40 device
- The canonical `:8001` router was initially healthy and listed all model presets as unloaded.
- The service had `MemoryMax=12G`; runtime-only override raised it to `28G`.
- Runtime-only systemd manager environment was set:
  - `LLAMA_SERVER_MMAP=0`
  - `LLAMA_SERVER_DISABLE_CUDA_GRAPHS=1`
- The restarted router did include `--no-mmap` in its command and in spawned child args.
- The build logged `GGML_CUDA_DISABLE_GRAPHS=1`, but `system_info` still printed `USE_GRAPHS = 1`, so this current build does not provide proof that CUDA graphs were actually disabled.
- `ollama ps` showed `nomic-embed-text:latest` loaded as `100% GPU`, and `nvidia-smi` showed the Ollama runner using about `628 MiB` on the M40.
- `ollama stop nomic-embed-text:latest` unloaded the embedding model and returned the M40 to `0 MiB / 24576 MiB`.
- Non-root `nvidia-smi --gpu-reset -i 1` failed with `Insufficient Permissions`, both before and after unloading Ollama.

### Probe results

- A canonical router load of `model:qwen2.5-14b-instruct` initially reached `loaded` and M40 VRAM rose to about `10547-11176 MiB`.
- A later tiny qwen2.5 generation attempt timed out after 60 seconds because the router was unloading a previous APEX worker and reloading qwen2.5.
- qwen2.5 reload with mmap enabled failed during CUDA tensor upload:
  - `CUDA error: unspecified launch failure`
  - `ggml_backend_cuda_buffer_set_tensor`
  - `cudaMemcpyAsync`
  - kernel logged M40 `Xid 32`
- qwen2.5 reload with `--no-mmap` also failed:
  - `mmap = false`
  - `CUDA error: unspecified launch failure`
  - `ggml_backend_cuda_device_event_synchronize`
  - `cudaEventSynchronize`
  - kernel logged M40 `Xid 32`
- A clean APEX retry after stopping Ollama and restarting the router with `--no-mmap` failed immediately:
  - model: `model:qwen3.5-35b-a3b-apex`
  - args included `--no-mmap`, `--fit off`, `--n-gpu-layers 999`, `--ctx-size 16384`
  - `CUDA error: unspecified launch failure`
  - `ggml_backend_cuda_device_get_memory`
  - `cudaMemGetInfo(free, total)`
  - kernel logged M40 `Xid 69`
- After the APEX Xid, the router kept the model status stuck at `loading` even though the worker was gone.
- A restart to clear the stuck router state left `:8001` listening, but a bounded `/health` probe then hung; the service was force-killed and stopped.
- Final local GPU state after stopping llama and unloading Ollama: M40 visible, `0 MiB / 24576 MiB`, no intentional compute process left.

### Inferred facts

- This is not a GT 1030 misrouting issue; the active llama.cpp CUDA device is the Tesla M40.
- This is not only an APEX model-file issue; after Xid, even qwen2.5 can fail in the same llama.cpp CUDA upload/synchronization path.
- This is not solved by `--no-mmap`, larger systemd `MemoryMax`, or unloading Ollama from the M40.
- Ollama-on-M40 is a separate regression/risk because embeddings should not consume the M40 during local llama.cpp repair, but removing it did not restore APEX.
- The M40 now needs a privileged GPU reset or host reboot before any more meaningful local llama.cpp model-load tests.

### DATA_MISSING

- No successful APEX/Qwen3.5 generation exists on the local M40 in this continuation.
- No successful post-Xid qwen2.5 tiny generation exists after the clean APEX retry.
- No privileged GPU reset was available.
- No BIOS setting readout was changed or proven relevant in this continuation.

### Current decision

Stop local APEX load attempts for this session. The last clean local attempt still produced `cudaMemGetInfo` failure and M40 `Xid 69`; continuing without a privileged GPU reset or reboot risks more wedged router/process state and does not move toward restoration.

Recommended next safe local step: schedule a host reboot or privileged `nvidia-smi --gpu-reset -i 1`, keep Ollama embeddings off the M40, then start `:8001` with `--no-mmap` and test one small qwen2.5 control before a single APEX retry. If APEX still fails on a clean reset state, local M40 full-function APEX should be treated as blocked on llama.cpp/CUDA/Maxwell compatibility or hardware/BIOS/PCIe investigation.
- Disk: 80 GB
- Image: `ghcr.io/ggml-org/llama.cpp:server-cuda`
- Model URL: `https://huggingface.co/mudler/Qwen3.5-35B-A3B-APEX-GGUF/resolve/main/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`
- Expected remote bind: `127.0.0.1:8001`
- Expected local tunnel: `127.0.0.1:18001 -> remote localhost:8001`
- Synthetic smoke prompt: `Reply exactly: ok`
- Failure policy: destroy if remote `/v1/models`, local tunnel `/v1/models`, or synthetic generation fails inside the setup window.

Provisioning command shape after approval:

```bash
GGUF_URL='https://huggingface.co/mudler/Qwen3.5-35B-A3B-APEX-GGUF/resolve/main/Qwen3.5-35B-A3B-APEX-I-Compact.gguf'
ONSTART_CMD='set -euo pipefail
mkdir -p /workspace/models /workspace/logs
if [ -d /root/.ssh ]; then
  chown -R root:root /root/.ssh || true
  chmod 700 /root/.ssh || true
  if [ -f /root/.ssh/authorized_keys ]; then
    chmod 600 /root/.ssh/authorized_keys || true
  fi
fi
MODEL_PATH=/workspace/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf
LLAMA_SERVER_BIN="$(command -v llama-server || true)"
if [ -z "$LLAMA_SERVER_BIN" ] && [ -x /app/llama-server ]; then
  LLAMA_SERVER_BIN=/app/llama-server
fi
if [ -z "$LLAMA_SERVER_BIN" ] && [ -x /usr/local/bin/llama-server ]; then
  LLAMA_SERVER_BIN=/usr/local/bin/llama-server
fi
if [ -z "$LLAMA_SERVER_BIN" ]; then
  echo "llama-server not found in image" | tee /workspace/logs/provisioning.error
  exit 42
fi
if [ ! -s "$MODEL_PATH" ]; then
  curl -fL --retry 3 --connect-timeout 20 --max-time 1800 "$GGUF_URL" -o "$MODEL_PATH"
fi
nohup "$LLAMA_SERVER_BIN" --host 127.0.0.1 --port 8001 --model "$MODEL_PATH" --alias model:qwen3.5-35b-a3b-apex --ctx-size 16384 --n-gpu-layers 999 --parallel 1 >/workspace/logs/llama-server.log 2>&1 &
echo $! >/workspace/logs/llama-server.pid
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8001/v1/models >/workspace/logs/models.json; then
    exit 0
  fi
  sleep 2
done
tail -200 /workspace/logs/llama-server.log || true
exit 44'

vastai create instance 26051042 \
  --image ghcr.io/ggml-org/llama.cpp:server-cuda \
  --disk 80 \
  --ssh --direct \
  --env "-e GGUF_URL=${GGUF_URL}" \
  --onstart-cmd "$ONSTART_CMD"
```

Post-create gates:

```bash
vastai show instance <INSTANCE_ID> --raw
vastai attach ssh <INSTANCE_ID> ~/.ssh/vastai_nopass.pub
vastai logs <INSTANCE_ID> --tail 200
ssh -i ~/.ssh/vastai_nopass -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -p <VAST_SSH_PORT> root@<VAST_SSH_HOST> 'nvidia-smi && curl -m 10 -sS http://127.0.0.1:8001/v1/models'
ssh -i ~/.ssh/vastai_nopass -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -p <VAST_SSH_PORT> -N -L18001:localhost:8001 root@<VAST_SSH_HOST>
curl -m 10 -sS http://127.0.0.1:18001/v1/models
```

Synthetic generation gate through the local tunnel:

```bash
curl -sS --max-time 120 http://127.0.0.1:18001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"model:qwen3.5-35b-a3b-apex","messages":[{"role":"user","content":"Reply exactly: ok"}],"temperature":0,"max_tokens":8,"stream":false}'
```

### Offer refresh - 2026-05-16T18:41:14+10:00

- `vastai show instances-v1 --raw`: `total_instances: 0`
- Previously prepared offer `26051042` was no longer returned by `vastai search offers 'id=26051042 rentable=true'`.
- Current cheapest verified 48 GB candidate from dry-run search:
  - Offer ID: `26051049`
  - GPU: `RTX 6000Ada`
  - VRAM: `49140` MiB
  - Price with 80 GB storage: about `$0.542/hr`
  - Region: Taiwan
  - Direct ports: `124`
  - Reliability: `0.9982534`
  - Driver: `570.211.01`
  - Disk available: `93.25` GB

Updated approval phrase:

```text
Confirm rent Vast offer 26051049 for up to 60 minutes, max spend $0.60, download the APEX GGUF, and destroy if runtime smoke fails.
```

## Preserve Dirty Runtime Diff Check - 2026-05-16T18:44+10:00

A later dirty-state handoff showed runtime-related edits in `/mnt/hdd-data/home/l4nd0/tenn` on branch `preserve/dirty-work-20260430T065748Z`. The relevant inspected diffs add or modify:

- `scripts/cockpit`: `cockpit reboot full virtual`, API-only/full-virtual profile, skip local llama startup in virtual mode.
- `financial-engine_v2/backend/app/routes/cockpit_api.py`: runtime target fields, rented GPU snapshot, rented GPU model listing/load support.
- `financial-engine_v2/scripts/run_local_backend.sh` and `docs/setup/environment.md`: shared secrets env-file loading.
- `scripts/run_llama_server.sh`, `scripts/run_extraction_server.sh`, and install docs: M40 preferred-GPU / CUDA-visible-device launcher support.

These changes do not constitute a no-regression local model fix:

- They can support routing to a rented GPU once `TENN_RENTED_GPU_LLAMACPP_URL` is set and `:18001` is healthy.
- They can support an API-only virtual mode, but that is a cloud/API fallback, not restored local APEX/Qwen3.5.
- They do not change the current observed M40 failure: Qwen3.5/APEX llama.cpp CUDA loads still fail on the local Tesla M40.

Current live check at this point:

- Fast worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`, branch `fast/dev-storage-v1-20260513-170304`, HEAD `87562bf0b026`.
- Preserve worktree: `/mnt/hdd-data/home/l4nd0/tenn`, branch `preserve/dirty-work-20260430T065748Z`, HEAD `b0f26d67f791`, with unrelated/user dirty runtime and UI files.
- `:8001` is listening via llama-router PID `995`, no loaded model, M40 idle.
- `:8000` backend was down in the fast-worktree runtime check.
- `:18001` remains absent.

Conclusion: preserve dirty work may be useful plumbing for the approved remote-GPU path, but it does not remove the approval gate or restore local full functionality.
