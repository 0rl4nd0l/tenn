---
job_id: extraction_third_canary_runtime_readiness_refresh_v2_20260529
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md
  - reports/agent_jobs/extraction_third_canary_runtime_readiness_refresh_v2_20260529/README.md
  - reports/agent_jobs/extraction_third_canary_runtime_readiness_refresh_v2_20260529/status.json
  - reports/agent_jobs/extraction_third_canary_runtime_readiness_refresh_v2_20260529/runtime_readiness_packet.json
  - reports/agent_jobs/extraction_third_canary_runtime_readiness_refresh_v2_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_third_canary_runtime_readiness_refresh_v2_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Third Canary Runtime Readiness Refresh V2

## Objective

Refresh current #96 runtime readiness evidence after the approved third-canary
phrase was already blocked by the live-runtime preflight.

This task must not restart services, submit documents, run a canary, run broad
extraction, mutate storage, or change extraction logic. It records whether the
current runtime state is safe enough for a later approved execution task.

## Lane

Primary lane: Evaluation.

## Execution Mode

SAFE EXTENSION, report-local readiness evidence only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-runtime-readiness-refresh-v2-20260529`

Branch: `audit/extraction-runtime-readiness-refresh-v2-20260529`

Issue: #96

Intended files: this task card, one report bundle under this task's output
directory, and `docs/claude/STATE.md`.

Contested surfaces touched: none from the explicit contested-surface list.

Collision risk: MEDIUM because this report gates a future Financial Truth
runtime action, but this task performs no runtime, datastore, source, parser,
prompt, schema, or UI mutation.

Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

Target system layer: Evaluation/Provenance around a future Extraction execution
gate. This task does not invoke extraction, storage, retrieval, analysis, or
client surfaces.

Relevant contract rules: backend remains the sole authority; metric extraction
must use explicit source values only; failures must fail fast; GPU-exclusive
extraction must not run while runtime/GPU state is not cleanly verifiable.

What must not change: production extraction/backfill, production DB writes,
direct SQL mutation, Qdrant/news/memory mutation, source PDFs, parser routing,
extraction prompts, gold labels, schemas/migrations, runtime/model/GPU/service
config, Cockpit UI, issue tracker state, or canary execution.

Why safe: the task only records current evidence and blocks execution while the
runtime gates are unsafe. It does not create a new fallback, parallel pipeline,
or approximation.

GPU process check required: yes, because this readiness decision concerns a
future llama/GPU-dependent extraction run. The check is read-only for this task.
If GPU health cannot be cleanly verified, the report must keep the canary
blocked.

## Hard Stops

- Do not run a third canary batch.
- Do not call `POST /api/process/document/{document_id}`.
- Do not restart, stop, start, rebuild, or reload any service.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not change parser routing, extraction prompts, gold labels, or source
  fixture labels.
- Do not change runtime, model, GPU, service, schema, migration, or Cockpit UI
  files.
- Do not post GitHub comments, close issues, relabel, assign, or edit issue
  bodies.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Re-check current branch, HEAD, registry state, API health, queue state, GPU
  guard output, direct `nvidia-smi`, and backend/worker/gpu_worker start times.
- Record the previous approved third-canary phrase as received, but do not treat
  it as authorization for a service reload.
- Keep current execution blocked if GPU health is not cleanly verifiable or if
  current loaded worker code cannot be proven without a reload.
- Keep the seven-document packet from
  `extraction_third_canary_approval_packet_refresh_v1_20260529` intact and
  unexecuted.
- State exact next safe gates without issuing a fresh executable approval packet
  while GPU health is failing.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- `curl -m 5 -sS http://127.0.0.1:8000/api/health`
- `curl -m 5 -sS http://127.0.0.1:8000/api/queue/status`
- `scripts/gpu_process_guard.sh --check`
- `nvidia-smi`
- Docker container start-time inspection for `fe_backend`, `fe_worker`, and
  `fe_gpu_worker`.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff.
- `python3 scripts/agent_job_registry.py release extraction_third_canary_runtime_readiness_refresh_v2_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed,
validation run with exact results, current runtime verdict, exact blockers, no
canary/backfill/datastore/source/runtime mutation confirmation, remaining
blockers before full accurate extraction graduation, and final git status.
