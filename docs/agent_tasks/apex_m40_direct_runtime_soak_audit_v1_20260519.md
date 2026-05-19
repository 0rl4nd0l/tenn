---
job_id: apex_m40_direct_runtime_soak_audit_v1_20260519
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md
  - reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
---

# Task

Run a bounded direct-runtime APEX/M40 soak audit against the already-running llama.cpp router on `:8001`.

Do not restart, reconfigure, relaunch, or mutate anything. This task only sends a tiny fixed set of direct local llama.cpp-compatible requests and checks GPU/runtime/kernel evidence between requests.

# Context

Recent APEX/M40 audit classified:

- `model:qwen3.5-35b-a3b-apex` is actually loaded on `:8001`.
- Model file:
  `/mnt/tenn-nvme2/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`
- Tesla M40 is in use by the APEX child process.
- Direct tiny smoke succeeded:
  - prompt: `Reply exactly: ok`
  - output: `ok`
  - HTTP 200
  - elapsed about `0.748s`
  - 16 prompt tokens / 2 completion tokens
  - no fresh `journalctl -k` Xid/CUDA lines.
- Verdict was `APEX_M40_DEGRADED`, not fully reliable, because only a tiny direct smoke was proven and Cockpit chat route still has visible-source guard/prompt-expansion side effects.

Recent Home audit classified Cockpit Home as honestly `PARTIAL`, with missing producers being empty/deferred data rather than runtime failure. Do not use Home producer work in this task.

# Goal

Answer:

1. Does the direct `:8001` APEX runtime remain stable across 8-12 tiny local prompts?
2. Do any requests fail, hang, return malformed content, or exceed timeout?
3. Does M40 VRAM remain stable before/during/after?
4. Do fresh NVIDIA Xid/CUDA/kernel errors appear during the soak?
5. Does llama.cpp remain loaded on APEX after the soak?
6. Should status remain `APEX_M40_DEGRADED`, upgrade to `APEX_M40_DIRECT_STABLE`, or downgrade?

# Hard boundaries

Do not:

- restart services
- stop services
- launch a new model
- change model selection
- change CUDA_VISIBLE_DEVICES
- edit scripts
- edit Docker Compose
- edit systemd
- edit `.env`
- mutate data, reports, DBs, Qdrant, news, memory, models, embeddings, Home producers, parser/extraction surfaces, or financial truth
- use Cockpit `/api/cockpit/chat`
- run web/RAG/deep research
- run extraction
- benchmark heavily
- use long prompts
- commit/stash/clean

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md`
- registry/list-active if supported
- registry/check-overlap if supported
- claim only if safe; otherwise continue report-only if no active conflicting runtime/GPU job exists

# Baseline runtime/GPU proof

Before requests, run and report:

- `ss -ltnp | rg ':8001' || true`
- `ps -ef | rg 'llama|qwen|apex|8001' | rg -v rg || true`
- `curl -sS http://127.0.0.1:8001/health || true`
- `curl -sS http://127.0.0.1:8001/v1/models | head -200 || true`
- `nvidia-smi -L`
- `nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv`
- `nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv || true`
- `journalctl -k --since "10 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia' || true`

# Direct soak requirements

Use direct llama.cpp-compatible `/v1/chat/completions` only.

Use the already-running API key from the process environment if required, but do not print the key.

Model:
- Use the loaded model returned by `/v1/models`, expected `model:qwen3.5-35b-a3b-apex`.

Requests:
- 8 to 12 total.
- Sequential only.
- No concurrency.
- `max_tokens <= 32`.
- `temperature <= 0.2`.
- Per-request timeout max 60 seconds.
- Stop the soak if any single request exceeds 60 seconds, returns non-200, or fresh Xid/CUDA errors appear.

Prompt set:

1. `Reply exactly: ok`
2. `Reply with exactly one word: stable`
3. `Return exactly this JSON: {"ok":true}`
4. `In one short sentence, say the runtime is responding.`
5. `Reply with the number 42 only.`
6. `Reply exactly: done`
7. `Return exactly: APEX_READY`
8. `Reply with exactly three words: local runtime ready`

Optional prompts 9-12 only if the first 8 are clean and fast:
9. `Summarize in one sentence: deterministic evidence matters.`
10. `Return exactly this CSV row: status,ok`
11. `Reply with exactly two words: smoke passed`
12. `Return exactly: END`

For each request, capture:

- prompt id
- HTTP status
- elapsed time
- response text
- prompt tokens if available
- completion tokens if available
- total tokens if available
- pass/fail against expected shape
- post-request `journalctl -k` Xid/CUDA check result
- M40 memory used after request

# Post-soak checks

After the request loop, run and report:

- `curl -sS http://127.0.0.1:8001/v1/models | head -200 || true`
- `nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv`
- `nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv || true`
- `journalctl -k --since "30 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia' || true`
- `tail -120 /tmp/llama-server-8001.log || true`

# Required output

Write:

`reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/README.md`

Include:

- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- baseline runtime map
- baseline GPU/process map
- per-request results table
- pass/fail summary
- latency summary
- token summary
- M40 VRAM before/after
- any CUDA/Xid evidence
- whether the loaded APEX model remained loaded
- final verdict:
  - `APEX_M40_DIRECT_STABLE`
  - `APEX_M40_DEGRADED`
  - `APEX_M40_UNSTABLE`
  - `DATA_MISSING`
- what this proves
- what this does not prove
- recommended next safe step
- final git status
- registry release status if claimed
- Project Memory save recommendation

# Verdict rules

Use `APEX_M40_DIRECT_STABLE` only if:

- all 8 required prompts pass or reasonably satisfy expected shape;
- no HTTP failures;
- no request exceeds 60 seconds;
- no fresh Xid/CUDA/kernel errors appear;
- M40 remains visible and has llama/APEX process memory allocated;
- model remains loaded after soak.

Keep `APEX_M40_DEGRADED` if:

- direct runtime works but outputs are inconsistent with simple shape expectations;
- latency is inconsistent but not failing;
- model/GPU proof is partial;
- logs are partially unavailable.

Use `APEX_M40_UNSTABLE` if:

- request fails/hangs;
- fresh Xid/CUDA errors appear;
- model unloads/crashes;
- M40 disappears;
- process dies.

# Hard stops

Stop and report if:

- active registry shows overlapping runtime/model/GPU work
- `:8001` is not listening
- `/v1/models` does not show APEX loaded
- M40 is not visible
- no llama/APEX process is resident on M40
- API key cannot be obtained without printing secrets
- any request exceeds 60 seconds
- fresh Xid/CUDA error appears
