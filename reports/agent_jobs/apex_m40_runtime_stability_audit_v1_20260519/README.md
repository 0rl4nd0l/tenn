# APEX/M40 Runtime Stability Audit

Job: `apex_m40_runtime_stability_audit_v1_20260519`  
Mode: `AUDIT ONLY`  
Runtime root: `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`  
Verdict: `APEX_M40_DEGRADED`

`model:qwen3.5-35b-a3b-apex` is not merely selected in Cockpit config. It is loaded by the live `:8001` llama.cpp router and resident on the Tesla M40. The tiny direct runtime smoke succeeded with output `ok`, 16 prompt tokens, 2 completion tokens, HTTP 200, and no fresh kernel Xid/CUDA lines in `journalctl -k`.

The degraded classification is because this audit only proves a bounded tiny smoke and because the Cockpit chat route did not return the requested `ok`: the app-level visible-source guard replaced the answer with a missing-evidence refusal and triggered an auto-diagnostic side effect. This is stable enough for "APEX is active on M40 now"; it is not enough to call the M40/APEX path reliable for long Cockpit prompts or heavy workloads.

## Confirmed Facts

- Preflight:
  - `pwd` from `/home/l4nd0/tenn-runtime` resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
  - `readlink -f /home/l4nd0/tenn-runtime` returned `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
  - Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
  - HEAD: `5dd7ee84b49e`.
  - Starting dirty state included this new task card plus unrelated untracked task cards:
    - `docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md`
    - `docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
    - `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md`
  - `python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md` returned `ok: true`.
  - `python3 scripts/agent_job_registry.py list-active` returned `active_jobs: []`.
  - `python3 scripts/agent_job_registry.py check-overlap ...` returned `ok: false` only because the two unrelated task cards above are dirty outside this job's `allowed_files`.
  - No registry claim was taken.

- Live runtime map:
  - `:8000`: Docker host-network backend, container `fe_backend`, root PID `168089`, command `/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - `:8001`: host `llama-server` router, PID `160535`.
  - `:8002`: not listening.
  - `:8081`: Next server, PID `169855`, command `next-server (v16.2.0)`.

- GPU inventory:
  - GPU 0: `NVIDIA GeForce GT 1030`, UUID `GPU-6eb16315-86f1-f22b-5dbb-cd0162cd3660`, bus `00000000:25:00.0`, 2048 MiB total, 1 MiB used.
  - GPU 1: `Tesla M40 24GB`, UUID `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`, bus `00000000:2D:00.0`, 24576 MiB total, 8750-8812 MiB used during the audit.
  - `nvidia-smi pmon -c 1` showed PID `172471` on GPU index `1`.
  - `nvidia-smi --query-compute-apps=...` showed PID `172471`, process `llama-server`, GPU UUID `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`, using about `8731-8793 MiB`.

- `:8001` process proof:
  - Listener PID `160535`:
    - command: `/home/l4nd0/tenn-runtime/tools/llama.cpp/build-cuda/bin/llama-server --main-gpu 0 --threads 4 --host 0.0.0.0 --port 8001 --spec-type ngram-simple --models-dir /mnt/tenn-nvme2/tenn/models --models-max 1 --models-preset /home/l4nd0/.config/tenn/llamacpp-presets.ini --no-mmap --api-key <redacted> --parallel 1`
    - cwd: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
    - relevant environment included `LLAMACPP_URL=http://127.0.0.1:8001`, `LLAMA_SERVER_CUDA_VISIBLE_DEVICES=0`, `CUDA_VISIBLE_DEVICES=0`, `LLAMA_SERVER_ROUTER_MODE=1`, `LLAMA_SERVER_MODELS_DIR=/mnt/tenn-nvme2/tenn/models`, and `LLAMA_SERVER_PORT=8001`.
  - Loaded model child PID `172471`:
    - command: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/tools/llama.cpp/build-cuda/bin/llama-server --chat-template-file /home/l4nd0/.config/tenn/qwen3.5-chat-template.jinja --host 127.0.0.1 --no-mmap --port 59345 --spec-type ngram-simple --alias model:qwen3.5-35b-a3b-apex --batch-size 512 --ctx-size 16384 --fit off --model /mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf --main-gpu 0 --n-gpu-layers 20 --parallel 1 --threads 4 --ubatch-size 256`
    - cwd: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

- APEX model proof:
  - Config-selected model:
    - `financial-engine_v2/config/cockpit.yaml`: `model: model:qwen3.5-35b-a3b-apex`
    - `financial-engine_v2/config/cockpit_llm.yaml`: `model: model:qwen3.5-35b-a3b-apex`
    - `/api/cockpit/config`: `llm_model: model:qwen3.5-35b-a3b-apex`, `llm_endpoint: http://127.0.0.1:8001`, `routing_policy: api_preferred`, `runtime_target: local`, `profile: ops`
  - Runtime-loaded model:
    - `/v1/models` returned `model:qwen3.5-35b-a3b-apex` with `status.value: loaded`.
    - `/api/cockpit/models` returned `active_model: model:qwen3.5-35b-a3b-apex`.
    - The child process command line loaded `/mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`.
  - Open model file:
    - `lsof -p 160535 | rg -i 'gguf|qwen|apex|model'` and `lsof -p 172471 | ...` produced only `lsof` namespace/overlay warnings and no open GGUF line.
    - `/proc/<pid>/fd` symlink inspection also found no open GGUF fd. This is not a contradiction because the child is running with `--no-mmap`; command line and `/v1/models` are the model proof.

- Direct llama.cpp-compatible smoke:
  - `curl http://127.0.0.1:8001/health` returned `{"status":"ok"}`, HTTP 200, elapsed `0.000401s`.
  - `curl http://127.0.0.1:8001/v1/models` returned HTTP 200 and showed `model:qwen3.5-35b-a3b-apex` loaded.
  - Unauthenticated chat returned HTTP 401 `Invalid API Key`; authenticated retry used the API key from the running process without printing it.
  - Authenticated direct chat request:
    - prompt: `Reply exactly: ok`
    - model: `model:qwen3.5-35b-a3b-apex`
    - HTTP status: 200
    - elapsed: `0.748270s`
    - output: `ok`
    - prompt tokens: `16`
    - completion tokens: `2`
    - total tokens: `18`
  - `/tmp/llama-server-8001.log` matched the direct smoke: `task.n_tokens = 16`, prompt eval `652.58 ms`, eval `70.64 ms`, total `723.22 ms`.

- Cockpit/backend smoke:
  - `GET http://127.0.0.1:8000/api/health`: HTTP 200, `{"status":"ok"}`.
  - `GET http://127.0.0.1:8000/api/cockpit/config`: HTTP 200; selected local model and endpoint matched APEX on `:8001`.
  - `GET http://127.0.0.1:8081/api/cockpit/config`: HTTP 200; same config through frontend.
  - `GET http://127.0.0.1:8000/api/cockpit/models`: HTTP 200; `active_model` was `model:qwen3.5-35b-a3b-apex`.
  - One tiny non-streaming Cockpit chat smoke was run against `POST http://127.0.0.1:8000/api/cockpit/chat` with web search, RAG, and db diagnostics disabled.
    - HTTP status: 200
    - elapsed: `5.768926s`
    - returned model/source: `model:qwen3.5-35b-a3b-apex`, `local`
    - runtime target: `local`
    - route metadata: `runtime_routing_reason: operator_selected`, `routing_reason: legacy_keyword_local`
    - returned text was not `ok`; it was the app-level missing-visible-sources refusal.
    - `provider_error`: `null`
    - degraded/runtime error fields: no provider/runtime error, but `grounding_guard: missing_visible_sources`, `source_coverage_status: missing_required_evidence`.
    - llama.cpp log showed the Cockpit request reached APEX with `task.n_tokens = 542`, `2` output tokens, and total runtime `5633.41 ms`.
    - The Cockpit route also triggered an auto-diagnostic flag report and a later llama.cpp request with `task.n_tokens = 976`, which was canceled by the client. This is a side effect of the Cockpit route, not the direct runtime smoke.

- NVIDIA/CUDA stability:
  - `journalctl -k --since "30 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia'` returned no matching lines before the smoke.
  - Post-direct-smoke and post-Cockpit-smoke `journalctl -k` checks also returned no matching lines.
  - `dmesg -T ...` was blocked: `read kernel buffer failed: Operation not permitted`.

- Cockpit GPU reporting:
  - Frontend `/api/cockpit/health` returned both GPUs and the M40 process:
    - `gpus[0]`: GT 1030
    - `gpus[1]`: Tesla M40 24GB
    - `processes[0]`: PID `172471`, GPU name `Tesla M40 24GB`, about `8793 MiB`, command label `llama.cpp runtime`
  - Frontend `/api/cockpit/metrics/gpu` also returned both GPUs and the M40 process.
  - Backend direct `/api/cockpit/metrics/gpu` returned HTTP 200 but `status: unknown`, `error: nvidia-smi not installed`.
  - UI code explains the collapsed GT 1030 summary:
    - `cockpit-ui/components/cockpit/gpu-activity-dialog.tsx` reads `const g = gpus[0]` in `readGpuSummary`.
    - `cockpit-ui/components/cockpit/cockpit-sidebar.tsx` displays that `gpuSummary`.
    - `cockpit-ui/components/cockpit/operations/gpu-workload-card.tsx` also uses `const firstGpu = gpus[0]`.
  - Therefore the observed GT 1030 label is because the collapsed UI summary reports GPU index 0, not because the M40 is invisible or unused.

## Inferred Facts

- `CUDA_VISIBLE_DEVICES=0` inside the llama-server environment maps to the M40 for this process, not the host's physical GPU 0. The inference is confirmed by `nvidia-smi --query-compute-apps`, which maps PID `172471` to the M40 UUID.
- Cockpit config selection, `/api/cockpit/models`, `/v1/models`, process command line, and VRAM residency all agree that APEX is actually active on `:8001`.
- The UI GT 1030 summary is a presentation issue in the collapsed status surface: the health payload contains the M40 and the M40 process, but the summary string selects `gpus[0]`.
- The Cockpit chat route is not a clean "tiny prompt only" path even with RAG/web/db diagnostics disabled. The core chat request expanded to 542 prompt tokens, then the route's auto-flag side effect created a separate 976-token llama.cpp request that was canceled.

## Speculative Claims

- None needed for the core verdict.
- A longer soak or repeated prompts may still expose the prior M40/CUDA instability. This audit intentionally did not run long prompts or heavy benchmarks.

## DATA_MISSING

- `dmesg -T` output is unavailable without elevated kernel-buffer permissions.
- Backend container process environment for PID `168089` was not readable from the host shell: `/proc/168089/environ: Permission denied`.
- `lsof` did not expose an open GGUF model file for the loaded child process. The loaded model is proven by `/v1/models` and process command line instead.
- No direct token count was returned by the Cockpit `/api/cockpit/chat` response; prompt-token count came from `/tmp/llama-server-8001.log`.

## Required Questions

1. Is the M40 visible to the host?  
   Yes. `nvidia-smi -L` lists GPU 1 as `Tesla M40 24GB`.

2. Is the M40 visible to the llama.cpp/APEX runtime process?  
   Yes. PID `172471` is the loaded APEX child process and `nvidia-smi` maps it to the M40 UUID with about `8.7-8.8 GiB` VRAM allocated.

3. Which process is serving `:8001`?  
   PID `160535`, host `llama-server` router, serving `0.0.0.0:8001`.

4. What model file is actually loaded by the `:8001` runtime?  
   `/mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`, loaded by child PID `172471`.

5. Is the loaded model actually `qwen3.5-35b-a3b-apex`, or only selected in Cockpit config?  
   It is actually loaded. `/v1/models` reports `model:qwen3.5-35b-a3b-apex` as `loaded`, `/api/cockpit/models` reports it as `active_model`, and the child process alias is `model:qwen3.5-35b-a3b-apex`.

6. Which GPU has VRAM allocated to the llama/APEX process?  
   The Tesla M40, host GPU index `1`, UUID `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`.

7. Why is Cockpit reporting GT 1030?  
   The collapsed UI summary reports the first GPU row, `gpus[0]`, and host GPU 0 is the GT 1030. The M40 is visible and in use, and the full frontend health/metrics payload includes both GPUs plus the M40 process. Backend container GPU metrics are `DATA_MISSING` because that route cannot run `nvidia-smi` inside the container.

8. Does a small direct runtime smoke succeed?  
   Yes. Authenticated direct `/v1/chat/completions` returned HTTP 200, elapsed `0.748270s`, output `ok`, 16 prompt tokens, 2 completion tokens.

9. Does a Cockpit chat/API smoke succeed without massive prompt amplification?  
   Partially. The route succeeded through local APEX with HTTP 200 and no provider/runtime error, but it did not return `ok`; it returned the visible-source refusal. The llama.cpp log showed 542 prompt tokens for the core Cockpit request, which is much larger than the 16-token direct smoke but not the prior multi-thousand-token failure pattern. The auto-diagnostic side effect added a separate 976-token request.

10. Are fresh NVIDIA Xid/CUDA errors present after the audit?  
    No fresh matching lines appeared in `journalctl -k` after the direct and Cockpit smokes. `dmesg` is `DATA_MISSING` due permissions.

11. Should APEX/M40 be classified as reliable, degraded, or not trusted yet?  
    `APEX_M40_DEGRADED`: active and stable for the bounded tiny direct smoke, but not proven reliable for long Cockpit prompts or broader workloads.

## Recommended Next Safe Step

Run a follow-up audit-only soak that sends a small fixed set of local direct prompts to `:8001` with a hard token cap and kernel-log checks between prompts. Keep Cockpit route testing separate, or disable/avoid auto-flag side effects for smoke tests if the code supports an existing test-only path. Do not change model/CUDA config as part of that follow-up.

## Registry Status

- `list-active`: no active jobs.
- `check-overlap`: failed because unrelated dirty task cards exist outside this job's allowed files.
- Claim: skipped.
- Release: not applicable.
- Final `list-active`: still no active jobs.

## Final Git Status

Actual final `git status --short`:

```text
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
?? docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
```

`reports/` is ignored in this checkout. `git status --short --ignored` shows:

```text
!! reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/
```

Report files present:

```text
README.md
diff-check.json
```

`python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md` returned `ok: false` because the two unrelated task cards are dirty outside allowed files, and because this audit-only card does not include `allow_audit_code_changes=true`. The task-card validation itself remains `ok: true`.

The two `nvme2...` and `route_parity...` task cards were pre-existing unrelated dirt and were not modified.

## Project Memory Save Recommendation

Save this result to Project Memory: on the NVMe runtime baseline, `:8001` is a llama.cpp router with APEX actually loaded on the M40 child process, direct tiny APEX smoke is stable with no fresh Xid/CUDA logs, Cockpit's collapsed GPU summary can show GT 1030 because it uses `gpus[0]`, and Cockpit chat smoke may trigger visible-source refusal plus auto-diagnostic prompt side effects even when local APEX routing succeeds.
