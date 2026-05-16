# APEX/M40 Runtime Stability Audit

Generated: 2026-05-16T12:39:00+10:00

## Session Declaration

```text
Lane: Query Orchestration
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: AUDIT ONLY / REPORT ONLY
Intended files: docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md; reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/
Contested surfaces touched: none
Collision risk: LOW-MEDIUM, bounded to task/report files and read-only runtime probes
Decision: audit stopped on hard-stop CUDA/runtime evidence; no fixes implemented
```

## Classification

Runtime state: `UNSTABLE_DO_NOT_RELY_ON_APEX`

Reason: `:8001` is listening and `/health` returns OK, but `/v1/models` reports `model:qwen3.5-35b-a3b-apex` as `loading`, the active llama-server child is defunct, GPU telemetry reports no active compute process and only 3 MiB on the Tesla M40, and `/tmp/llama-server-8001.log` contains a CUDA `unspecified launch failure` while loading APEX. This matches the task hard stop for CUDA errors, so no tiny completion/chat request was run.

APEX current default recommendation: do not treat APEX-on-M40 as a reliable default until a follow-up runtime recovery task proves successful load plus bounded direct and Cockpit chat probes.

Fallback/degraded labeling recommendation: yes. The local APEX route should be labeled degraded/unreliable while this failure mode is present.

Rented GPU recommendation: still justified for APEX-class local chat if the goal is a reliable APEX path and M40 stability remains unresolved.

Follow-up implementation task needed: yes, but outside this audit. The next task should either repair the local APEX/M40 load path or wire/label a degraded fallback path without silently swapping providers.

Project Memory save recommendation: save this result. The important durable fact is that on 2026-05-16 the recovered NVMe runtime still had an APEX/M40 load failure: `/v1/models` stuck at `loading`, defunct child PID 69931, no M40 residency, and CUDA `unspecified launch failure` in `/tmp/llama-server-8001.log`.

## Confirmed Facts

- `pwd` returned `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Branch was `fast/dev-storage-v1-20260513-170304`.
- HEAD short SHA was `2b2197e0def9`.
- Task card validation succeeded with `ok: true` and no issues.
- Initial registry `list-active` returned no active jobs.
- Registry claim succeeded for `apex_m40_runtime_stability_audit_v1_20260516`, with allowed files limited to the task card and report directory.
- The only pre-existing dirty file observed was `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json`; it is unrelated report dirt.
- Ports/listeners: `:8000` listening, `:8001` listening via `llama-server` PID 66831, `:8081` listening via `next-server` PID 69473, `:8002` absent from the filtered `ss` output.
- Backend `/api/health` on `:8000` returned HTTP 200 with `{"status":"ok"}`.
- llama.cpp `/health` on `:8001` returned HTTP 200 with `{"status":"ok"}`.
- llama.cpp `/v1/models` on `:8001` returned HTTP 200; `model:qwen3.5-35b-a3b-apex` status was `loading`.
- `/api/cockpit/home` on `:8000` returned HTTP 404 `{"detail":"Not Found"}`.
- `/api/health` through `:8081` returned HTTP 200 with `{"status":"ok"}`.
- `/api/cockpit/home` through `:8081` timed out under `timeout 8s`.
- `nvidia-smi` completed within timeout; no D-state/hung `nvidia-smi` was observed in the commands run.
- GPU inventory showed GPU 0 `NVIDIA GeForce GT 1030` and GPU 1 `Tesla M40 24GB`, driver `535.288.01`.
- GPU memory before the failed APEX assessment was GT 1030 `1 / 2048 MiB`, Tesla M40 `3 / 24576 MiB`.
- `nvidia-smi --query-compute-apps` returned no active compute rows.
- `financial-engine_v2/scripts/gpu_runtime_status.py` reported active processes: none, total memory `4 / 26624 MiB`.
- `pgrep` showed router PID 66831 and child PID 69931.
- `ps` showed PID 69931 as `Z` defunct with parent 66831.
- `/tmp/llama-server-8001.log` shows APEX load on router child port 37353 and then CUDA `unspecified launch failure`.

## Inferred Facts

- The router process can make health and model-list endpoints look available while the APEX model itself is not usable.
- The M40 is visible to the driver, but the active APEX model is not resident on the M40 in the observed state.
- The `:8001` path is not stable enough for light local chat because the target model is stuck loading after a CUDA failure.

## Speculative Claims

- The CUDA failure may be related to the current M40 plus llama.cpp build/runtime combination, but this audit did not run repairs, alternative models, model reloads, or provider swaps to isolate cause.
- The `:8081` `/api/cockpit/home` timeout may be a proxy/app-route issue or backend route mismatch; this audit did not continue after the hard-stop CUDA evidence.

## DATA_MISSING

- Tiny direct completion/chat result is missing because the audit stopped before running it after the CUDA hard stop.
- Tiny Cockpit chat route probe is missing because the audit stopped before running it after the CUDA hard stop.
- Post-tiny-request GPU status is not applicable because no tiny request was run.
- Exact Cockpit `/api/cockpit/home` body through `:8081` is missing because the request timed out under `timeout 8s`.
- `graphify-out` was not present in this worktree, so graphify architecture context could not be read from this checkout.

## Runtime Health Before/After

Before runtime probes:
- `:8000`: listening; `/api/health` OK.
- `:8001`: listening; `/health` OK; `/v1/models` OK but APEX status `loading`.
- `:8081`: listening; `/api/health` via proxy OK.
- `:8002`: absent.

After bounded endpoint/log probes:
- No restart, reload, or mutation was performed.
- The audit stopped after confirming CUDA failure evidence in `/tmp/llama-server-8001.log`.
- No tiny completion/chat request was run.

## GPU Health Before/After

Before:

```text
0, NVIDIA GeForce GT 1030, GPU-6eb16315-86f1-f22b-5dbb-cd0162cd3660, 535.288.01, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6, 535.288.01, 24576, 3, 24469, 0, 25, P8
```

Compute apps:

```text
<no rows>
```

`gpu_runtime_status.py`:

```text
GPU 0: NVIDIA GeForce GT 1030
  Memory: 1 / 2048 MiB (0.0%)

GPU 1: Tesla M40 24GB
  Memory: 3 / 24576 MiB (0.0%)

Active processes: none
Total memory: 4 / 26624 MiB (0.0%)
```

After:
- No post-request GPU status exists because no request was run after the hard stop.
- The timeout-bounded `nvidia-smi` commands used before the hard stop completed successfully.

## Endpoint Observations

`curl http://127.0.0.1:8000/api/health`:

```text
HTTP/1.1 200 OK
{"status":"ok"}
```

`curl http://127.0.0.1:8001/health`:

```text
HTTP/1.1 200 OK
{"status":"ok"}
```

`curl http://127.0.0.1:8001/v1/models`:

```text
HTTP/1.1 200 OK
...
model:qwen3.5-35b-a3b-apex status.value = loading
args include:
  --model /mnt/nvme/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf
  --main-gpu 0
  --n-gpu-layers 999
  --ctx-size 16384
```

`curl http://127.0.0.1:8000/api/cockpit/home`:

```text
HTTP/1.1 404 Not Found
{"detail":"Not Found"}
```

`curl http://127.0.0.1:8081/api/health`:

```text
HTTP/1.1 200 OK
{"status":"ok"}
```

`curl http://127.0.0.1:8081/api/cockpit/home`:

```text
timeout 8s expired; exit code 124
```

## CUDA / Process Evidence

Active process summary:

```text
66831 /mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server --main-gpu 0 --threads 4 --host 0.0.0.0 --port 8001 --spec-type ngram-simple --models-dir /mnt/nvme/tenn/models --models-max 1 --models-preset /home/l4nd0/.config/tenn/llamacpp-presets.ini --api-key local-openai-key --parallel 1
69931 llama-server
```

`ps -o pid,ppid,stat,etime,cmd -p 66831,69931`:

```text
66831 1 Ssl ... llama-server --main-gpu 0 ... --port 8001 ...
69931 66831 Z ... [llama-server] <defunct>
```

Relevant log summary from `/tmp/llama-server-8001.log`:

```text
srv load: spawning server instance with name=model:qwen3.5-35b-a3b-apex on port 37353
Device 0: Tesla M40 24GB, compute capability 5.2
main: loading model
srv load_model: loading model '/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf'
CUDA error: unspecified launch failure
current device: 0, in function ggml_backend_cuda_device_get_memory
srv ensure_model: waiting until model name=model:qwen3.5-35b-a3b-apex is fully loaded...
```

## Concurrent Jobs Observed

Before claim:

```json
{
  "active_jobs": [],
  "ok": true,
  "registry_scope": "shared"
}
```

After claim:

```json
{
  "active_jobs": [
    {
      "job_id": "apex_m40_runtime_stability_audit_v1_20260516",
      "lane": "Query Orchestration",
      "mutation_mode": "audit_only",
      "allowed_files": [
        "docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md",
        "reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516"
      ]
    }
  ],
  "ok": true
}
```

Overlap assessment: no active jobs overlapped this audit before claim. After claim, the only active job observed was this audit.

## Collision Risks

- Runtime mutation risk: avoided. No services were restarted and no model reload was requested.
- Source mutation risk: avoided. No source files were edited.
- Report dirt risk: one unrelated modified report status file existed before the audit and remained unrelated.
- Contested surface risk: no contested runtime/query source files were edited.

## Repo Status

Initial observed status after task-card creation:

```text
 M reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
```

The worktree did not stay clean because this audit intentionally added the task card and report files, and the pre-existing unrelated report status file was already modified.

## Check-Diff Result

`python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md` was run after writing the report. It returned `ok: false`.

Reported issues:

```text
reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json is outside allowed_files
audit_only jobs may not include code changes unless allow_audit_code_changes=true
```

Assessment:

- The first issue is pre-existing unrelated report dirt and was not modified by this audit.
- The second issue appears to be the validator treating the newly created task-card/report artifacts as changes under an `audit_only` card that does not include `allow_audit_code_changes: true`.
- The task card content was intentionally not broadened because the user required exact task-card content.
- The check-diff artifact was written by the validator at `reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/diff-check.json`.

## Commands Run

```bash
pwd
git branch --show-current
git rev-parse --short=12 HEAD
test -f docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md && sed -n '1,120p' docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md || true
python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
python3 scripts/agent_job_registry.py list-active
git status --short --untracked-files=all
git log --oneline -8
git worktree list
python3 scripts/agent_job_registry.py claim docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
timeout 15s env GPU_GUARD_NVIDIA_SMI_TIMEOUT_SECONDS=5 scripts/gpu_process_guard.sh --check
timeout 8s nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,pstate --format=csv,noheader,nounits
timeout 8s nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv,noheader,nounits
ss -ltnp '( sport = :8000 or sport = :8001 or sport = :8081 or sport = :8002 )'
pgrep -af 'llama-server|llama.cpp|run_llama_server|uvicorn|next-server|next dev'
timeout 12s python3 financial-engine_v2/scripts/gpu_runtime_status.py
find graphify-out -maxdepth 2 -type f | sort | head -20
timeout 5s curl -sS -i http://127.0.0.1:8000/api/health
timeout 5s curl -sS -i http://127.0.0.1:8001/health
timeout 5s curl -sS -i http://127.0.0.1:8001/v1/models
timeout 8s curl -sS -i http://127.0.0.1:8000/api/cockpit/home
timeout 8s curl -sS -i http://127.0.0.1:8081/api/cockpit/home
timeout 8s curl -sS -i http://127.0.0.1:8081/api/health
ps -o pid,ppid,stat,etime,cmd -p 66831,69931
ls -lah /tmp/llama-server-8001.log /tmp/llama*.log 2>/dev/null || true
tail -n 160 /tmp/llama-server-8001.log 2>/dev/null || true
date -Is
python3 scripts/agent_job_registry.py list-active
git status --short --untracked-files=all
mkdir -p reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516
```

## Probe Failures, Hangs, Timeouts

- `git worktree list` took more than one second but completed normally after polling.
- `curl http://127.0.0.1:8081/api/cockpit/home` timed out after 8 seconds.
- No `nvidia-smi` timeout occurred.
- No tiny prompt was run because the CUDA error was a hard stop.

## Recommended Next Safe Step

Open a separate implementation-capable task card to recover or demote the local APEX route. The task should start from the confirmed state here: router health is insufficient; require proof that the target model reaches `loaded`, M40 VRAM/process telemetry reflects residency, a tiny direct request returns quickly and coherently, and a lightweight Cockpit route probe does not time out.

## Final Report Template

```text
Files changed:
- docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
- reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/README.md
- reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/status.json

Files inspected:
- CLAUDE.md
- docs/architecture/SYSTEM_CONTRACT.md
- /home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md
- /mnt/hdd-data/home/l4nd0/tenn/.codex/skills/performance-check/SKILL.md
- /tmp/llama-server-8001.log

Lane: Query Orchestration
Execution mode: AUDIT ONLY / REPORT ONLY
Collision risk: LOW-MEDIUM
Validation run:
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
- python3 scripts/agent_job_registry.py list-active
- timeout-bounded GPU/runtime endpoint probes listed above
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260516.md
Validation result: task card OK; registry no overlap; runtime classified UNSTABLE_DO_NOT_RELY_ON_APEX due CUDA hard stop; check-diff blocked by pre-existing unrelated report dirt and audit_only artifact rule
Files intentionally not touched:
- source code
- runtime configuration
- model aliases
- databases, Qdrant, news stores, memory stores
- contested Query Orchestration/runtime source surfaces
Remaining blockers:
- APEX model stuck loading after CUDA unspecified launch failure
- defunct llama-server child under router PID 66831
- no active M40 compute process or meaningful M40 residency
- /api/cockpit/home via :8081 timed out in bounded probe
- check-diff failed for reasons listed in Check-Diff Result
Next safe step:
- separate implementation task to repair or demote APEX route, with no silent provider/model swap
```
