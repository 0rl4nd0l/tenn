# APEX M40 Direct Runtime Soak Audit

Job: `apex_m40_direct_runtime_soak_audit_v1_20260519`
Mode: `audit_only`
Started: `2026-05-19T20:39:31+10:00`
Soak window: `2026-05-19T20:41:02+10:00` to `2026-05-19T20:41:29+10:00`

## Final Verdict

`APEX_M40_DIRECT_STABLE`

This upgrades the status only for direct local llama.cpp-compatible `:8001` usage with tiny sequential prompts. It does not upgrade Cockpit chat behavior, long-context behavior, concurrent load behavior, Home producers, extraction, RAG, or any production financial truth surface.

## Confirmed Facts

- Working directory resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch was `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD was `5dd7ee84b49e`.
- Task card validation passed with no issues.
- Registry `list-active` returned no active jobs.
- Registry `check-overlap` returned `ok: false` only because unrelated untracked task cards were already dirty outside this task's allowlist. No active registry job or runtime/GPU overlap was present, so this audit continued report-only and did not claim.
- `:8001` was listening with router PID `160535`.
- `/health` returned `{"status":"ok"}`.
- `/v1/models` showed `model:qwen3.5-35b-a3b-apex` loaded before and after the soak.
- Loaded APEX model path was `/mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`.
- Host GPUs were visible:
  - GPU 0: `NVIDIA GeForce GT 1030`, `2048 MiB`.
  - GPU 1: `Tesla M40 24GB`, `24576 MiB`.
- The resident APEX child process was PID `172471` on M40 UUID `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`.
- M40 memory stayed stable: baseline `8812 MiB`, every request `8812 MiB`, post-soak `8812 MiB`.
- M40 compute-app memory stayed stable: baseline `8793 MiB`, post-soak `8793 MiB`.
- No fresh `journalctl -k` matches for `nvrm|xid|cuda|gpu|nvidia` appeared in the baseline 10-minute check, per-request checks, or post-soak 30-minute check.
- All 12 sequential direct `/v1/chat/completions` requests returned HTTP 200.
- No request exceeded the 60 second timeout.
- Post-soak `tail -120 /tmp/llama-server-8001.log` showed recent `POST /v1/chat/completions` requests completing with HTTP 200 and no CUDA/Xid failure text.

## Inferred Facts

- The GT 1030 being GPU 0 does not mean APEX was using the GT 1030. The runtime child process had compute residency on the M40 UUID.
- For this narrow prompt set, the direct router path and APEX child path remained stable enough to classify direct local use as stable.
- The API key was required for chat completions and was read from the already-running router process without printing it. It is intentionally omitted from this report.

## Speculative Claims

- None needed for the final verdict. The stable classification is limited to the observed direct tiny-prompt soak.

## DATA_MISSING

- No Cockpit `/api/cockpit/chat` request was made by design.
- No long prompt, RAG, extraction, Home producer, benchmark, or concurrency path was exercised.
- No service restart/reload persistence was tested.
- No root-only `dmesg` evidence was collected; `journalctl -k` was the kernel evidence source.
- No production data was accessed.

## Preflight

| Check | Result |
| --- | --- |
| `pwd` | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| `readlink -f /home/l4nd0/tenn-runtime` | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| HEAD | `5dd7ee84b49e` |
| contract validate | `ok: true`, `issues: []` |
| registry list-active | `active_jobs: []`, `ok: true` |
| registry check-overlap | `ok: false`, unrelated dirty task cards outside this allowlist |
| registry claim | Not claimed because check-overlap failed on unrelated dirty task cards; continued report-only because no active conflicting runtime/GPU job existed. |

Initial `git status --short`:

```text
?? docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
?? docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
?? docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
```

## Baseline Runtime Map

| Surface | Evidence |
| --- | --- |
| listener | `0.0.0.0:8001`, `llama-server`, PID `160535` |
| router command | `/home/l4nd0/tenn-runtime/tools/llama.cpp/build-cuda/bin/llama-server --main-gpu 0 --threads 4 --host 0.0.0.0 --port 8001 --spec-type ngram-simple --models-dir /mnt/tenn-nvme2/tenn/models --models-max 1 --models-preset /home/l4nd0/.config/tenn/llamacpp-presets.ini --no-mmap --api-key [REDACTED] --parallel 1` |
| child command | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/tools/llama.cpp/build-cuda/bin/llama-server --chat-template-file /home/l4nd0/.config/tenn/qwen3.5-chat-template.jinja --host 127.0.0.1 --no-mmap --port 59345 --spec-type ngram-simple --alias model:qwen3.5-35b-a3b-apex --batch-size 512 --ctx-size 16384 --fit off --model /mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf --main-gpu 0 --n-gpu-layers 20 --parallel 1 --threads 4 --ubatch-size 256` |
| health | `{"status":"ok"}` |
| loaded model before soak | `model:qwen3.5-35b-a3b-apex`, `status.value: loaded`, child port `59345` |
| loaded model after soak | `model:qwen3.5-35b-a3b-apex`, `status.value: loaded`, child port `59345` |

## Baseline GPU/Process Map

| GPU | UUID | Total | Baseline Used | Post Used | Temp Post | Util Post |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| GPU 0 `NVIDIA GeForce GT 1030` | `GPU-6eb16315-86f1-f22b-5dbb-cd0162cd3660` | `2048 MiB` | `1 MiB` | `1 MiB` | `25 C` | `0 %` |
| GPU 1 `Tesla M40 24GB` | `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6` | `24576 MiB` | `8812 MiB` | `8812 MiB` | `37 C` | `0 %` |

Compute apps:

| Phase | PID | Process | GPU UUID | Used Memory |
| --- | ---: | --- | --- | ---: |
| baseline | `172471` | `.../tools/llama.cpp/build-cuda/bin/llama-server` | `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6` | `8793 MiB` |
| post-soak | `172471` | `.../tools/llama.cpp/build-cuda/bin/llama-server` | `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6` | `8793 MiB` |

## Per-Request Results

All requests were sequential, direct local `POST /v1/chat/completions`, `temperature: 0.1`, `max_tokens: 32`, model `model:qwen3.5-35b-a3b-apex`.

| ID | HTTP | Elapsed s | Shape | Prompt Tokens | Completion Tokens | Total Tokens | M40 MiB After | Kernel Check | Response |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 200 | 0.872734 | PASS | 16 | 2 | 18 | 8812 | none | `ok` |
| 2 | 200 | 0.845060 | PASS | 19 | 2 | 21 | 8812 | none | `stable` |
| 3 | 200 | 1.142231 | PASS | 22 | 6 | 28 | 8812 | none | `{"ok":true}` |
| 4 | 200 | 1.200845 | PASS | 23 | 6 | 29 | 8812 | none | `The runtime is responding.` |
| 5 | 200 | 0.929015 | PASS | 21 | 3 | 24 | 8812 | none | `42` |
| 6 | 200 | 0.746959 | PASS | 16 | 2 | 18 | 8812 | none | `done` |
| 7 | 200 | 0.963043 | PASS | 19 | 4 | 23 | 8812 | none | `APEX_READY` |
| 8 | 200 | 0.982839 | PASS | 21 | 4 | 25 | 8812 | none | `local runtime ready` |
| 9 | 200 | 2.934051 | PASS | 23 | 32 | 55 | 8812 | none | `Deterministic evidence matters because it provides absolute, non-probabilistic certainty that conclusively validates or refutes a claim without the ambiguity inherent in statistical likelihoods` |
| 10 | 200 | 0.986348 | PASS | 21 | 4 | 25 | 8812 | none | `status,ok` |
| 11 | 200 | 1.006439 | PASS | 20 | 3 | 23 | 8812 | none | `Smoke passed` |
| 12 | 200 | 0.772856 | PASS | 16 | 2 | 18 | 8812 | none | `END` |

## Pass/Fail Summary

- Required prompts 1-8: `8/8 PASS`.
- Optional prompts 9-12: `4/4 PASS`.
- HTTP failures: `0`.
- Curl/runtime failures: `0`.
- Requests over 60 seconds: `0`.
- Fresh kernel/CUDA/Xid matches: `0`.
- Model unload/crash: `0`.
- M40 disappearance: `0`.
- Process death: `0`.

## Latency Summary

| Scope | Count | Min s | Max s | Average s |
| --- | ---: | ---: | ---: | ---: |
| Required 1-8 | 8 | 0.746959 | 1.200845 | 0.960341 |
| All 1-12 | 12 | 0.746959 | 2.934051 | 1.115202 |

The optional request 9 consumed the full `32` completion-token cap and was the only request above 2 seconds.

## Token Summary

| Scope | Prompt Tokens | Completion Tokens | Total Tokens |
| --- | ---: | ---: | ---: |
| Required 1-8 | 157 | 29 | 186 |
| All 1-12 | 237 | 70 | 307 |

## CUDA/Xid/Kernel Evidence

- Baseline `journalctl -k --since "10 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia' || true`: no output.
- Per-request kernel check from soak start: `none` after every request.
- Post-soak `journalctl -k --since "30 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia' || true`: no output.
- Post-soak llama log tail showed HTTP 200 request completion and timing lines, not CUDA/Xid failure lines.

## Loaded APEX Model Remained Loaded

Yes. `/v1/models` showed `model:qwen3.5-35b-a3b-apex` with `status.value: loaded` before and after the 12-request soak, with the same model path and child port `59345`.

## What This Proves

- The already-running local llama.cpp router on `:8001` can serve 12 tiny sequential direct chat completions against loaded APEX on the Tesla M40.
- The M40 stayed visible and resident for the APEX child process through the soak.
- M40 VRAM did not drift in the observed window.
- No fresh NVIDIA/CUDA/Xid/kernel evidence appeared in the observed window.
- The direct `:8001` path is stable enough to use as `APEX_M40_DIRECT_STABLE` for tiny local direct requests.

## What This Does Not Prove

- It does not prove Cockpit `/api/cockpit/chat` is stable.
- It does not prove prompt-expansion guard behavior is fixed.
- It does not prove long-context, RAG, extraction, parser, Home producer, benchmark, or concurrent behavior.
- It does not prove stability across service restart, reboot, or model reload.
- It does not prove financial-data correctness.

## Recommended Next Safe Step

Keep the status split: record `APEX_M40_DIRECT_STABLE` for direct local `:8001` tiny prompts, while preserving `APEX_M40_DEGRADED` for wider Cockpit chat usage until a separate bounded Cockpit-route audit proves that route without prompt amplification, long waits, or source-guard side effects.

## Final Git Status

Final `git status --short`:

```text
?? docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
?? docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
?? docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
```

`git status --ignored --short` for this task's paths:

```text
?? docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md
!! reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/
```

Final task-card validation still passed with `ok: true`.

`python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md` returned `ok: false` because the worktree already contains unrelated dirty task cards outside this task's `allowed_files`, and because the local audit-only diff gate flags dirty files without `allow_audit_code_changes=true`. The diff-check artifact was written to `reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/diff-check.json`.

## Registry Release Status

No registry claim was made. There is nothing to release.

## Project Memory Save Recommendation

Save a project memory note that on `2026-05-19` the NVMe runtime root `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` passed a 12-request direct local `:8001` APEX/M40 tiny soak with stable M40 residency, no fresh kernel/CUDA/Xid matches, and final verdict `APEX_M40_DIRECT_STABLE` scoped only to direct local llama.cpp-compatible usage.
