# M40 CUDA Failure Remediation

## Corrected diagnosis: M40 works; unsafe server config failed

The earlier investigation result was wrong or premature when it implied that the Tesla M40, or the M40 CUDA path for llama.cpp, was not viable. The user reported that this setup had worked before the motherboard move, and later manual user testing proved that the M40 can run both llama.cpp CLI and llama-server. Codex did not find that recovery path; this report preserves the recovery evidence from manual user testing and corrects the diagnosis.

Corrected diagnosis: the M40 can run llama.cpp and llama-server; the previous failure was configuration/runtime-path specific.

Manual recovery evidence:

- M40 topology and PCIe were sane after cold boot: CPU-lane topology `00:03.1-[2d] -> Tesla M40`, x16 width, ASPM disabled, no AER errors, and NVIDIA driver loaded cleanly.
- `llama-cli` with Mistral 7B on CUDA0 / Tesla M40 passed at `--n-gpu-layers 1`, `8`, and `32`.
- `llama-cli` with Qwen2.5 14B on CUDA0 / Tesla M40 passed at `--n-gpu-layers 1`, `8`, `16`, and `32`.
- The initially short chat outputs were caused by `--n-predict 4`, not by GPU failure.
- `llama-server` with the conservative Qwen2.5 14B config listened on `http://127.0.0.1:18001`.
- The successful server path used CUDA0 as the Tesla M40 24GB at `0000:2d:00.0`, `n_slots = 1`, `n_ctx = 512`, prompt cache disabled, `kv_unified = false`, and offloaded `8/49` layers to the GPU.
- `/health` returned `{"status":"ok"}`.
- `/v1/chat/completions` returned assistant content `ok`.
- `nvidia-smi` showed `/home/l4nd0/.local/bin/llama-server` resident on the Tesla M40 at about 2611 MiB VRAM.
- The kernel log tail after the successful request showed no fresh NVIDIA Xid.

Known-good command:

```bash
/home/l4nd0/.local/bin/llama-server \
  --model /mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 18001 \
  --n-gpu-layers 8 \
  --ctx-size 512 \
  --device CUDA0 \
  --split-mode none \
  --main-gpu 0 \
  --fit off \
  --parallel 1 \
  --cache-ram 0
```

The same command is preserved as `scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh`.

Unsafe or suspect settings from the earlier failing server path:

- auto parallelism / `n_parallel=4`
- `kv_unified=true`
- prompt cache enabled / large cache behavior
- `n_slots=4`
- `ctx-size 2048`
- fit/device-memory behavior
- wrong device selection risk; in this environment the known-good path used `CUDA0` for the M40 while earlier confusion selected the GT 1030 path

Do not declare the M40 unusable unless both minimal llama-cli and conservative llama-server smoke paths fail after a clean boot.

## Agent process failure

The user reported that this runtime had worked before the motherboard move. The investigation should have prioritised reconstructing the old known-good runtime path before drawing conclusions from a single failing server configuration. It over-indexed on one failing server path and did not isolate runtime variables early enough.

Future agents must isolate variables in this order:

1. hardware visibility
2. clean dmesg/kernel log
3. minimal llama-cli
4. llama-cli with increasing GPU layers
5. conservative llama-server
6. production-like llama-server

Future agents must distinguish these failure classes before making a hardware viability claim:

- hardware failure
- CUDA/driver failure
- device selection failure
- server config failure
- model-size/config failure
- production routing failure

## Conservative smoke validation - 2026-05-17

The known-good server was already running on `127.0.0.1:18001`, so no second server was started.

Validation commands:

```bash
ss -ltnp | grep -E ':8001|:18001' || true
curl -s http://127.0.0.1:18001/health || true
curl -s http://127.0.0.1:18001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Reply exactly: ok"}],"max_tokens":8,"temperature":0}'
nvidia-smi
journalctl -k -b --no-pager | grep -iE 'xid|nvrm|cuda|gpu' | tail -160
```

Validation result:

- `:18001` was listening with `/home/l4nd0/.local/bin/llama-server`.
- `:8001` was not listening in the preflight port check.
- `/health` returned `{"status":"ok"}`.
- `/v1/chat/completions` returned assistant content `ok` from `qwen2.5-14b-instruct-q4_k_m.gguf`.
- `nvidia-smi` showed the llama-server process on the Tesla M40 using about 2611 MiB VRAM.
- `journalctl -k -b` showed NVIDIA driver load messages for GPU IDs `0x00002200` and `0x00002d00`, with no fresh NVIDIA Xid in the captured tail after the successful request.
- `sudo dmesg -T ...` could not be captured non-interactively because sudo required a password.
- `:18001` was left running because it was already running before this correction pass.
- `:8001` was not started, stopped, rebound, or otherwise touched.

## Summary

Classification: `M40_LLAMA_CPP_AND_SERVER_RECOVERED_CONSERVATIVE_QWEN25`.

The attempted CPU fallback was stopped and not used as a remediation. Later manual user testing proved the local M40 can run llama.cpp CLI and a conservative Qwen2.5 14B llama-server path. Production `:8001` / systemd routing was not restored in this correction pass.

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

## Local APEX Preset Regression Probe - 2026-05-17T00:02+10:00

### Session declaration

```text
Lane: Query Orchestration
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: SAFE EXTENSION, host-runtime config repair plus one bounded APEX probe
Intended files: reports/agent_jobs/m40_cuda_failure_remediation_v1_20260516/
Host config touched: /home/l4nd0/.config/tenn/llamacpp-presets.ini, /home/l4nd0/.config/tenn/llama-server.env
Contested surfaces touched: local llama.cpp router service and Tesla M40 runtime only
Collision risk: MEDIUM
Decision: local APEX is still not restored
```

### What changed

Current-turn evidence found a concrete regression against the last documented working APEX-on-M40 shape:

- Historical commit `cdb9041` says APEX returned `ok` with router preset `--n-gpu-layers 20`.
- Current host preset had `[model:qwen3.5-35b-a3b-apex] gpu-layers = 999`.
- The host preset was restored to `gpu-layers = 20`.
- `LLAMA_SERVER_MMAP=0` was added to `/home/l4nd0/.config/tenn/llama-server.env` so the router persists `--no-mmap` across restarts.

### Validation run

Pre-checks:

- `nvidia-smi`: Tesla M40 visible, `0 MiB` before the probe, no compute processes.
- Tiny CUDA smoke on the M40 passed with `CUDA_VISIBLE_DEVICES=0`:
  - `device0=Tesla M40 24GB cc=5.2`
  - `CUDA_SMOKE_OK value=42`
- `ollama ps` was initially empty.

Router restart:

- `systemctl --user start llama-cpp-router.service` succeeded.
- Router command included `--no-mmap`.
- `/v1/models` showed `model:qwen3.5-35b-a3b-apex` with:
  - `--n-gpu-layers 20`
  - `--ctx-size 16384`
  - `--batch-size 512`
  - `--ubatch-size 256`
  - `--fit off`

Tiny APEX request:

```bash
timeout 180s curl -sS --max-time 170 \
  -H 'Authorization: Bearer local-openai-key' \
  -H 'Content-Type: application/json' \
  http://127.0.0.1:8001/v1/chat/completions \
  -d '{"model":"model:qwen3.5-35b-a3b-apex","messages":[{"role":"user","content":"Reply exactly: ok"}],"temperature":0,"max_tokens":8,"stream":false}'
```

Observed result:

- First child loaded far enough to report `offloaded 20/41 layers to GPU`.
- M40 reached about `8744 MiB` used during load.
- The router then force-killed that APEX child after a 10 second unload timeout.
- A second APEX child immediately failed at:
  - `CUDA error: unspecified launch failure`
  - `ggml_backend_cuda_device_get_memory`
  - `cudaMemGetInfo(free, total)`
- Kernel logged another M40 Xid:
  - `NVRM: Xid (PCI:0000:2d:00): 69, pid=71038, name=llama-server`
- The client request was manually killed after the CUDA failure.

Cleanup:

- `ollama` unexpectedly loaded `nomic-embed-text:latest` on the M40 during the probe; it was stopped with `ollama stop nomic-embed-text:latest`.
- The crashed router child left APEX stuck as `loading`; the router process did not exit cleanly on SIGTERM.
- `systemctl --user kill -s SIGKILL llama-cpp-router.service` was used to clear the crashed process tree.
- Router was restarted without loading a model.

Final live state:

- `:8001` router was initially restarted healthy with APEX visible but `unloaded`.
- APEX preset remains corrected to `gpu-layers = 20` and `--no-mmap`.
- Another request hit `:8001` after cleanup and triggered a second APEX failure at `00:03:30`, logging another M40 `Xid 69`.
- To prevent repeated failed APEX loads, `llama-cpp-router.service` was stopped with SIGKILL cleanup.
- Final router state: inactive/dead.
- Final M40 state: idle at `0 MiB`, no compute processes.
- Latest kernel log still contains the current-turn `Xid 69`.

### Interpretation

Confirmed:

- There was a real host preset regression: APEX had drifted from the documented working `20/41` offload shape back to full `999` offload.
- The M40 can still execute a tiny CUDA kernel after earlier failures.
- The current llama.cpp router can start cleanly and enumerate APEX with the corrected preset.
- The corrected `20` layer APEX path still fails on this boot with Xid 69 and does not answer a tiny prompt.

Inferred:

- Full-offload preset drift explains why the larger model path got worse, but it is not the only remaining failure.
- The current blocker is still the M40/driver/llama.cpp CUDA interaction after or during APEX load, not a simple model alias or CPU fallback issue.
- The unexpected Ollama embedding load is a separate regression/noise source and should be prevented from using the M40 during APEX work.

DATA_MISSING:

- No successful local-M40 APEX completion exists after this repair.
- No privileged GPU reset was available after the current-turn Xid 69.
- No BIOS readout is available from OS evidence.

Recommended next safe step:

1. Do not run another APEX load in this boot.
2. Reboot or privileged-reset the M40.
3. Before any APEX request, keep Ollama embeddings off the M40.
4. Re-test exactly the corrected `gpu-layers = 20`, `--no-mmap` APEX path once.
5. If that still Xids on a clean reset, local APEX-on-M40 is blocked below Tenn config and needs driver/BIOS/PCIe or llama.cpp Maxwell debugging.

### Final safety stop

Because another process/request retriggered APEX after the failed probe, leaving `:8001` online with APEX as the configured default is unsafe on this boot. The service was stopped rather than left available to cause repeated M40 Xids.

## Reset Gate State - 2026-05-17T00:06+10:00

Current live evidence after the safety stop:

- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD: `023bd9fcdc6d`
- Dirty files are this task card/report bundle only.
- `llama-cpp-router.service`: inactive/dead.
- `llama-cpp-router.service`: disabled after this note, so a reboot should not auto-start the router before the reset-gate checks.
- M40: visible, `0 MiB`, no compute processes.
- Ollama: `nomic-embed-text:latest` remains loaded CPU-side, not on the M40.
- Latest current-boot M40 kernel fault remains `Xid 69` from `llama-server`.

The next APEX test must be a clean-reset test, not another same-boot probe:

1. Keep automatic `:8001` startup disabled until the reset-gate checks are complete.
2. Reboot the host or perform a privileged reset of the Tesla M40.
3. Confirm `nvidia-smi` is responsive and M40 is idle.
4. Confirm Ollama embeddings are not using the M40.
5. Start the router with the corrected APEX preset (`gpu-layers = 20`, `--no-mmap`).
6. Run exactly one tiny direct APEX request.

If that clean-reset probe still logs Xid 69, the remaining blocker is below Tenn host config: driver/BIOS/PCIe/power or llama.cpp Maxwell backend behavior.

Autostart safety action run:

```bash
systemctl --user disable llama-cpp-router.service
systemctl --user is-enabled llama-cpp-router.service
```

Result: `disabled`; router remained inactive/dead and the M40 stayed at `0 MiB` with no compute processes.

## Clean GPU Reset APEX Probe - 2026-05-17T00:24+10:00

The user ran the privileged reset manually after `sudo nvidia-smi --gpu-reset -i 1` initially reported the M40 was in use. After unloading Ollama's embedding runner, the reset gate was rechecked locally:

- `nvidia-smi`: M40 visible, `0 MiB`, no compute processes.
- `llama-cpp-router.service`: inactive and disabled before manual start.
- `ollama ps`: no loaded models.
- Kernel journal for the preceding 10 minutes: no new Xid after the user's reset.

One corrected APEX probe was then run:

- Router was manually started, not enabled.
- Runtime env included `LLAMA_SERVER_DISABLE_CUDA_GRAPHS=1`.
- `/v1/models` showed APEX with `--no-mmap`, `--n-gpu-layers 20`, `--ctx-size 16384`, `--batch-size 512`, `--ubatch-size 256`, and `--fit off`.
- Tiny request:

```bash
timeout 220s curl -sS --max-time 210 \
  -H 'Authorization: Bearer local-openai-key' \
  -H 'Content-Type: application/json' \
  http://127.0.0.1:8001/v1/chat/completions \
  -d '{"model":"model:qwen3.5-35b-a3b-apex","messages":[{"role":"user","content":"Reply exactly: ok"}],"temperature":0,"max_tokens":8,"stream":false}'
```

Result:

- APEX loaded metadata and began tensor upload.
- It offloaded `20/41` layers to the M40.
- M40 VRAM reached about `8115 MiB`.
- Failure occurred during tensor upload at `ggml_backend_cuda_device_event_synchronize` / `cudaEventSynchronize`.
- Kernel logged M40 `Xid 32` for `llama-server` at `00:23:18`.
- The request did not return `ok`; it hung behind the crashed child and was killed.
- The router was stopped again with SIGKILL cleanup.
- Final M40 state: `0 MiB`, no compute processes.

Conclusion:

- The privileged reset did not restore APEX on the local M40.
- The corrected historical 20-layer/no-mmap APEX path still fails on a clean reset.
- This is now classified as `M40_CUDA_LLAMACPP_BACKEND_OR_PLATFORM_FAULT`, not a simple Tenn config regression.
- Do not run further APEX loads in this boot.

Next safe diagnostic step:

- Do not continue model-load poking.
- Check BIOS/slot/power/platform settings before another APEX attempt:
  - Above 4G Decoding enabled.
  - Resize BAR disabled or conservative for Maxwell if present.
  - PCIe slot forced Gen3.
  - ASPM disabled.
  - M40 in the most direct CPU-lane slot available.
  - Adequate M40 auxiliary power and cooling.
- If BIOS/platform checks are corrected, repeat only one APEX probe with the same `20` layer/no-mmap preset.

## Return-To-Working-Runtime Attempt - 2026-05-17T00:38+10:00

After web research confirmed CUDA 13 removed Maxwell/Pascal/Volta toolkit support and that M40 should remain on an older/sm_52-targeted stack, the local runtime was checked against the actual installed binary:

- Active llama.cpp CUDA binary: `/mnt/sdb2/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server`.
- Version: `8233 (c5a778891)`.
- Build target: `CMAKE_CUDA_ARCHITECTURES=52`.
- CUDA toolkit available locally: `11.5.119`.
- The earlier b8209/no-VMM rebuild was already recorded in this report and also failed with M40 Xid 69.

An attempt was made to return to the last proven smaller local M40 chat model instead of APEX:

1. Added host-local degraded profile `/home/l4nd0/.config/tenn/cockpit_llm.m40-qwen25-restore.yaml` pointing chat at `model:qwen2.5-14b-instruct`.
2. Started `llama-cpp-router.service` manually; it was not re-enabled.
3. Sent one bounded tiny request to `model:qwen2.5-14b-instruct`.

First result:

- Router spawned qwen2.5 with `--n-gpu-layers 999`, `--ctx-size 8192`, `--no-mmap`.
- It failed during llama.cpp fit/device-memory discovery:
  - `CUDA error: unspecified launch failure`
  - `ggml_backend_cuda_device_get_memory`
  - `cudaMemGetInfo(free, total)`
- Kernel logged M40 `Xid 69` at `00:36:28` for `llama-server`.

Mitigation attempt:

- Added `fit = off` to the qwen2.5 host preset in `/home/l4nd0/.config/tenn/llamacpp-presets.ini`.
- Restarted router manually and ran exactly one more bounded qwen2.5 tiny request.

Second result:

- Router confirmed qwen2.5 was spawned with `--fit off`.
- It still failed at `ggml_backend_cuda_device_get_memory` / `cudaMemGetInfo(free, total)`.
- Kernel logged another M40 `Xid 69` at `00:37:54` for `llama-server`.
- The request did not return `ok`.
- Router was stopped and broken parent/child PIDs were killed.
- Final state after cleanup:
  - `llama-cpp-router.service`: `failed`, disabled.
  - `:8001`: no listener.
  - M40: visible, `0 MiB`, no compute processes.

Conclusion:

- Returning to the known smaller qwen2.5 M40 runtime did not work in this boot.
- This is no longer isolated to APEX/Qwen3.5 size.
- Current classification is now `M40_CUDA_DEVICE_STATE_OR_PLATFORM_FAULT_FOR_LLAMACPP_LOADS`.
- Do not run more llama.cpp model-load probes until the M40 is reset or the host is rebooted and platform settings are checked.

The host-local qwen2.5 `fit = off` preset is intentionally left in place because it avoids the known llama.cpp fit path on any future reset/reboot retry. The degraded Cockpit profile file was created but not activated by restarting the backend, because qwen2.5 failed before backend/Cockpit cutover.

## Manual recovery finding - M40 llama-server restored on conservative config

Confirmed after cold reboot / clean driver state:
- M40 is on CPU-lane topology: 00:03.1-[2d] -> Tesla M40.
- PCIe link is sane: x16 width, ASPM disabled, no AER errors.
- llama-cli works on CUDA0 / Tesla M40:
  - Mistral 7B with ngl 1, 8, and 32.
  - Qwen2.5 14B with ngl 1, 8, 16, and 32.
- llama-server also works on CUDA0 / Tesla M40 with conservative settings:
  - model: /mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf
  - port: 18001
  - n_gpu_layers: 8
  - ctx_size: 512
  - device: CUDA0
  - split_mode: none
  - main_gpu: 0
  - fit: off
  - parallel: 1
  - cache_ram: 0
- Health endpoint returned status ok.
- OpenAI-compatible /v1/chat/completions returned "ok".
- No fresh NVIDIA Xid after the successful server request.

Corrected diagnosis:
- The M40 can run llama.cpp and llama-server.
- The earlier failure was likely caused by unsafe server defaults or wrong device/config path, not fundamental M40 incapability.
- Known risky settings include auto parallelism / n_parallel=4, prompt cache enabled, larger context, automatic fit behaviour, and accidental GT 1030 device selection.

Known-good command saved at:
~/m40_known_good_llama_server_qwen25_14b.sh
