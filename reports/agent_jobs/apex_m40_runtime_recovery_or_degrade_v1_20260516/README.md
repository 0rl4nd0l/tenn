# APEX/M40 Runtime Recovery Or Degrade

Generated: 2026-05-16T12:49:46+10:00

## Session Declaration

```text
Lane: Query Orchestration
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: SAFE EXTENSION, bounded process-level runtime recovery only
Intended files: docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md; reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/
Contested surfaces touched: none
Collision risk: LOW-MEDIUM, bounded to local :8001 llama.cpp process recovery and report/task-card files
Decision: recovery attempted once; APEX remains unstable
```

## Result

Classification: `UNSTABLE_DO_NOT_RELY_ON_APEX`

One targeted recovery was attempted because the existing `:8001` runtime was already unhealthy: APEX was stuck `loading`, the child process was defunct, and the M40 had no active compute process.

The stale `:8001` llama process group was terminated, the router was restarted through `scripts/run_llama_server.sh` using the same existing CUDA llama.cpp binary path that the prior process used, and one tiny APEX chat request was attempted.

The tiny request timed out after 90 seconds. The recovery log reproduced the same CUDA failure:

```text
CUDA error: unspecified launch failure
current device: 0, in function ggml_backend_cuda_device_get_memory
cudaMemGetInfo(free, total)
```

APEX should not remain trusted as the current default for local chat. Degraded/fallback labeling is recommended. Rented GPU remains justified if reliable APEX-class chat is the requirement.

## Confirmed Facts

- Task card validation succeeded.
- Registry claim initially failed because the prior audit task card was dirty outside this task's allowed files.
- The task card was widened only to include the prior audit task/report paths, then validation and claim succeeded.
- Initial active registry jobs before claim: none.
- Existing `:8001` process before cleanup: PID 66831, process group 66831, with defunct child PID 69931.
- Initial `:8001` `/v1/models` showed `model:qwen3.5-35b-a3b-apex` status `loading`.
- Initial GPU status showed Tesla M40 visible, 3 MiB used, no compute apps.
- `scripts/run_llama_server.sh` from this fast worktree fails without an override because `/home/l4nd0/tenn-fast-dev-storage-v1/tools/llama.cpp/build-cuda/bin` does not exist.
- The previous live server binary path was `/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server`.
- Restarting with `LLAMA_SERVER_BIN=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server` started router PID 127293 on `:8001`.
- The restarted router reported CUDA-visible `Device 0: Tesla M40 24GB`.
- Before the tiny request, `/v1/models` showed APEX as `unloaded`.
- The one tiny request to `model:qwen3.5-35b-a3b-apex` timed out after 90 seconds.
- During that request, the log showed CUDA `unspecified launch failure` while loading `/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`.
- After the failed request, `/v1/models` again showed APEX status `loading`.
- After the failed request, child PID 129004 was defunct under router PID 127293.
- After the failed request, M40 memory remained 3 MiB and compute-app query returned no rows.
- Backend `/api/health` on `:8000` returned HTTP 200 `{"status":"ok"}`.
- Cockpit `/api/health` through `:8081` returned HTTP 200 `{"status":"ok"}`.

## Runtime Health

Before recovery:

```text
:8000 listening
:8001 listening via llama-server PID 66831
:8081 listening via next-server PID 69473
:8002 absent
APEX status: loading
APEX child: PID 69931 defunct
```

Cleanup:

```text
kill -TERM -- -66831
kill -KILL -- -66831
```

TERM removed the listener but left the process alive. KILL removed the process group.

Restart:

```text
setsid env LLAMA_SERVER_BIN=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server scripts/run_llama_server.sh </dev/null >/tmp/llama-server-8001-recovery-20260516.log 2>&1 &
```

After restart, before APEX load:

```text
:8001 listening via llama-server PID 127293
/health returned HTTP 200 {"status":"ok"}
APEX status: unloaded
```

After APEX load attempt:

```text
/v1/chat/completions timed out after 90 seconds
APEX status: loading
APEX child: PID 129004 defunct
```

## GPU Health

Before recovery:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 25, P8
compute apps: no rows
```

After restart, before APEX request:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 25, P8
compute apps: no rows
```

After failed APEX request:

```text
0, NVIDIA GeForce GT 1030, 2048, 1, 1998, 0, 24, P8
1, Tesla M40 24GB, 24576, 3, 24469, 0, 25, P8
compute apps: no rows
```

No `nvidia-smi` timeout was observed in this task.

## Endpoint Observations

Tiny request:

```bash
timeout 90s curl -sS -w '\nHTTP_CODE=%{http_code}\nTIME_TOTAL=%{time_total}\nSIZE_DOWNLOAD=%{size_download}\n' \
  -o /tmp/apex_m40_tiny_response.json \
  http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer local-openai-key' \
  -d '{"model":"model:qwen3.5-35b-a3b-apex","messages":[{"role":"user","content":"Reply exactly: ok"}],"temperature":0,"max_tokens":8,"stream":false}'
```

Result:

```text
exit code 124
response file empty
```

Backend/Cockpit after recovery attempt:

```text
http://127.0.0.1:8000/api/health -> HTTP 200 {"status":"ok"}
http://127.0.0.1:8081/api/health -> HTTP 200 {"status":"ok"}
```

## Commands Run

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
python3 scripts/agent_job_registry.py list-active
python3 scripts/agent_job_registry.py claim docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
timeout 15s env GPU_GUARD_NVIDIA_SMI_TIMEOUT_SECONDS=5 scripts/gpu_process_guard.sh --check
timeout 8s nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,pstate --format=csv,noheader,nounits
ss -ltnp '( sport = :8000 or sport = :8001 or sport = :8081 or sport = :8002 )'
pgrep -af 'llama-server|llama.cpp|run_llama_server|uvicorn|next-server|next dev'
timeout 5s curl -sS -i http://127.0.0.1:8001/v1/models
ps -o pid,ppid,pgid,sid,stat,etime,cmd -p 66831,69931
kill -TERM -- -66831
kill -KILL -- -66831
timeout 12s scripts/run_llama_server.sh
timeout 12s env LLAMA_SERVER_BIN=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server scripts/run_llama_server.sh
setsid env LLAMA_SERVER_BIN=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server scripts/run_llama_server.sh </dev/null >/tmp/llama-server-8001-recovery-20260516.log 2>&1 &
timeout 5s curl -sS -i http://127.0.0.1:8001/health
timeout 5s curl -sS -i http://127.0.0.1:8001/v1/models
timeout 90s curl ... /v1/chat/completions
tail -n 80 /tmp/llama-server-8001-recovery-20260516.log
timeout 5s curl -sS -i http://127.0.0.1:8000/api/health
timeout 8s curl -sS -i http://127.0.0.1:8081/api/health
git status --short --untracked-files=all
```

## DATA_MISSING

- No successful tiny APEX response exists because the request timed out after CUDA failure.
- No Cockpit chat route probe was run because the direct APEX request hit the hard stop.
- No root-cause code/config repair was attempted; this task was bounded to one runtime recovery attempt.

## Collision / Repo Hygiene

- Active registry jobs before claim: none.
- Active registry job during work: this task only.
- Source/config files touched: none.
- Contested source surfaces touched: none.
- Runtime process mutation: targeted to `:8001` llama-server process group only.
- Pre-existing unrelated dirty file remained: `reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json`.
- Current untracked task cards include the prior audit task card and this recovery task card.

## Check-Diff Result

`python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md` returned `ok: false`.

The only disallowed file was pre-existing unrelated report dirt:

```text
reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json is outside allowed_files
```

The recovery task card and prior audit card were inside allowed files. The validator wrote `reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/diff-check.json`.

## Recommendations

- APEX should not remain trusted as the current local default.
- UI/API status should not treat `:8001` router `/health` as proof that APEX is usable.
- Degraded/fallback labeling is recommended immediately for local APEX-on-M40.
- Rented GPU remains justified for reliable APEX-class chat.
- The next implementation task should avoid another blind restart and instead choose one explicit path:
  - demote local APEX default to a smaller verified local model, with clear degraded labeling; or
  - change the APEX runtime parameters/build path with a controlled validation matrix; or
  - route APEX-class workloads to a verified rented GPU endpoint.

## Final Report Template

```text
Files changed:
- docs/agent_tasks/apex_m40_runtime_recovery_or_degrade_v1_20260516.md
- reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/README.md
- reports/agent_jobs/apex_m40_runtime_recovery_or_degrade_v1_20260516/status.json

Files inspected:
- scripts/run_llama_server.sh
- /home/l4nd0/.config/tenn/llama-server.env (secrets redacted in output)
- /tmp/llama-server-8001-recovery-20260516.log
- reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260516/README.md

Lane: Query Orchestration
Execution mode: SAFE EXTENSION
Collision risk: LOW-MEDIUM
Validation run:
- task-card validate
- registry list/claim
- timeout-safe GPU checks
- targeted :8001 cleanup and restart
- one tiny APEX direct request
Validation result: recovery failed; APEX remains UNSTABLE_DO_NOT_RELY_ON_APEX
Check-diff result: failed only on pre-existing unrelated report dirt
Files intentionally not touched:
- source code
- runtime config/model aliases/service units
- backend/Cockpit processes
- databases/Qdrant/news/memory stores
Remaining blockers:
- APEX load reproduces CUDA unspecified launch failure
- request times out after failed load
- router health remains misleading while APEX is stuck loading
- fast worktree launcher lacks local llama.cpp build path without LLAMA_SERVER_BIN override
- check-diff blocked by unrelated pre-existing report status dirt
Next safe step:
- demote/label local APEX or run a controlled runtime-parameter/build investigation under a new explicit task
```
