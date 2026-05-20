---
job_id: cockpit_chat_orchestration_side_effect_audit_v1_20260519
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md
  - reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
allow_audit_code_changes: true
---

# Task

Audit Cockpit `/api/cockpit/chat` orchestration side effects after the NVMe runtime checkpoint and direct APEX/M40 soak.

Do not implement. Do not change runtime, model, GPU, source guard, diagnostics, routing, Home producers, data, memory, Qdrant, news, or financial truth.

# Context

Recent checkpoint commit:

- `2e73de32ac77`
- subject: `milestone(evaluation): checkpoint nvme runtime audit artifacts`

Current established baseline:

- Tenn live stack runs from `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Backend/frontend/data/report mounts are NVMe-backed.
- Route parity is resolved:
  - `/api/cockpit/home` is Next.js BFF-owned.
  - backend direct `/api/cockpit/home` 404 is expected.
  - backend `/api/news/status` 404 is expected/absent.
- APEX/M40 direct runtime is stable for direct local tiny prompts:
  - `APEX_M40_DIRECT_STABLE`
  - 12/12 direct `/v1/chat/completions` prompts passed.
  - M40 VRAM stable.
  - no fresh Xid/CUDA kernel matches.
- Cockpit Home `PARTIAL` is honest missing/deferred producer state.

Known unresolved issue:

A prior tiny Cockpit chat smoke used local APEX but did not return `ok`. It returned an app-level missing-visible-sources refusal and showed extra side-effect activity:

- local model/source: `model:qwen3.5-35b-a3b-apex`, `local`
- runtime target: `local`
- no provider/runtime error
- `grounding_guard: missing_visible_sources`
- `source_coverage_status: missing_required_evidence`
- llama.cpp log showed core Cockpit request around `542` prompt tokens
- separate auto-diagnostic side-effect request around `976` prompt tokens was triggered/canceled

Primary question:

Why does a tiny Cockpit `/api/cockpit/chat` request behave differently from direct `:8001` APEX, and which component owns each side effect?

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md`
- registry/list-active if supported
- registry/check-overlap if supported
- claim only if safe

# Inspect read-only

Inspect the current Cockpit chat route and orchestration path.

Likely files, read-only:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/services/llm.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/tests/*cockpit*chat*`
- `financial-engine_v2/backend/tests/test_chat_route.py`
- `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- any source/grounding guard modules
- any auto-diagnostic / flag-report / response-feedback modules

Search for:

- `grounding_guard`
- `missing_visible_sources`
- `source_coverage_status`
- `missing_required_evidence`
- `auto`
- `diagnostic`
- `flag`
- `feedback`
- `visible sources`
- `required evidence`
- `dbDiagnostics`
- `web_search`
- `rag`
- `runtime_routing_reason`
- `operator_selected`
- `legacy_keyword_local`
- `max_tokens`
- `system prompt`
- `api/cockpit/chat`

# Runtime/API checks

Keep runtime checks tiny and read-only.

Allowed health/config checks:

- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -sS http://127.0.0.1:8000/api/cockpit/config | python3 -m json.tool | head -120`
- `curl -sS http://127.0.0.1:8000/api/cockpit/models | python3 -m json.tool | head -120`
- `curl -sS http://127.0.0.1:8001/v1/models | head -120`

Optional one-shot Cockpit chat smoke:

Only run one tiny non-streaming Cockpit chat smoke if the endpoint/payload is clear from current tests/docs.

Prompt:

`Reply exactly: ok`

Disable optional features if the API supports flags:
- web search off
- RAG off
- db diagnostics off
- streaming off

Capture:

- HTTP status
- elapsed time
- response text
- selected model
- active model
- runtime target
- provider/source
- routing reason
- runtime_routing_reason
- grounding guard fields
- source coverage fields
- whether response contains `ok`
- whether auto-diagnostic/flag/feedback side effects were triggered
- approximate llama.cpp prompt token count from `/tmp/llama-server-8001.log` before/after

Do not run more than one Cockpit chat smoke in this audit.

# Required analysis

Produce a component map answering:

1. Which code path handles `POST /api/cockpit/chat`?
2. Which function builds the prompt sent to local APEX?
3. Where are system/context/source instructions injected?
4. Which flags disable web/RAG/db diagnostics, and do they actually prevent retrieval/diagnostic work?
5. Which component applies `grounding_guard: missing_visible_sources`?
6. Why did the route return a refusal instead of the model output `ok`?
7. Which component sets `source_coverage_status: missing_required_evidence`?
8. What triggered the auto-diagnostic side-effect request?
9. Is the side effect:
   - expected product behavior,
   - debug/diagnostic behavior,
   - test-only behavior leaking into live route,
   - operator flag/reporting behavior,
   - or DATA_MISSING?
10. Is prompt amplification mostly:
   - necessary system prompt/context envelope,
   - source guard instructions,
   - route metadata,
   - diagnostic feedback,
   - legacy routing path,
   - or DATA_MISSING?
11. Does this issue affect only source-free meta/tiny prompts, or could it affect normal financial queries?
12. What smallest safe next step would reduce noise without weakening evidence/source guard safety?

# Classify findings

Classify:

## Direct runtime
- Expected stable
- Not owner of issue unless new evidence appears

## Cockpit route
- prompt envelope:
- source guard:
- retrieval flags:
- diagnostic side effects:
- output replacement:
- route metadata:
- owner files/functions:

## User-visible behavior
- correct safety behavior
- overzealous guard
- route smoke mismatch
- debug side effect leak
- DATA_MISSING

# Hard boundaries

Do not:

- edit code
- patch prompts
- relax grounding/source guards
- disable diagnostics
- change runtime/model/GPU config
- restart services
- run long prompts
- run multiple Cockpit chat smokes
- call deep research
- run Qdrant/news backfills
- mutate DBs, Qdrant, memory, news, data, reports, financial truth, Home producers, extraction/parser code, or runtime config
- commit/stash/clean

# Required output

Write:

`reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/README.md`

Include:

- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- live route map
- direct runtime baseline reference
- Cockpit chat component map
- prompt/token amplification explanation
- visible-source guard explanation
- auto-diagnostic side-effect explanation
- whether direct APEX/M40 stability remains valid
- whether issue is product-correct, overzealous, or bug-like
- recommended next safe task
- proposed allowed files for follow-up safe extension if needed
- tests to add before any patch
- validation commands run
- final git status
- registry release status
- Project Memory save recommendation

# Hard stops

Stop and report if:

- active registry shows overlapping Query Orchestration / Cockpit chat work
- current worktree is dirty beyond expected committed baseline
- the route smoke would mutate data or create persistent diagnostics
- logs/API responses would expose secrets
- source guard behavior cannot be understood without changing code
- follow-up would require weakening evidence/source safety
