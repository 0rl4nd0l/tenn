---
job_id: extraction_runtime_score_queue_stale_cleanup_v1_20260602
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Runtime
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_runtime_score_queue_stale_cleanup_v1_20260602.md
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/README.md
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/status.json
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/pre_cleanup_score_queue_snapshot.json
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/post_cleanup_score_queue_snapshot.json
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/validation.json
  - reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested controlled cleanup of only stale test-origin thesis_watchdog_check score queue messages on 2026-06-02.
---

# Extraction Runtime Score Queue Stale Cleanup V1

## Objective

Take a pre-cleanup snapshot, remove only the exact stale/test-origin
`thesis_watchdog_check` messages currently blocking the Redis `score` queue,
verify queue readiness, and stop.

This task must not run extraction, backfill, canary execution, bounded broad
sample execution, backend/worker/router startup, source-PDF mutation, DB or
Qdrant mutation, news mutation, memory mutation, service restart, unrelated
cleanup, or Redis `FLUSHDB`.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Query Orchestration

Execution mode: CONTROLLED QUEUE CLEANUP / READINESS ONLY

Intended files: this task card and the report bundle under
`reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/`.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM because Redis queue mutation is involved; file overlap
is expected to be LOW if active jobs do not touch the task-card/report bundle.

Decision: proceed only after task-card validation, active-job inspection, idle
runtime process checks, Redis queue snapshot, and exact stale/test-origin
message validation.

## Contract Check

Target system layers: Query Orchestration and Worker queue control, with
Evaluation readiness reporting.

Relevant contract rules: backend remains the authoritative system; jobs use the
canonical worker queue topology; agents must fail fast on ambiguity; no
parallel implementation, storage mutation, retrieval mutation, extraction
execution, or hidden fallback is allowed; GPU/router/extraction processes must
not be spawned by this task.

What must not change: extraction code, extraction prompts, financial truth,
source PDFs, Postgres, Qdrant, news stores, memory stores, backend services,
workers, router/runtime services, and Redis keys outside the exact validated
stale score messages.

Why safe: this is a bounded operational cleanup of queue entries that are first
snapshotted and validated as stale/test-origin `thesis_watchdog_check` messages.
Non-matching messages are preserved, ambiguity blocks cleanup, and no broad
runtime work is run.

GPU process check required: no GPU process should be spawned, restarted, or
depended on. Process checks are read-only readiness evidence only.

## Required Preflight

- Confirm repo path, branch, HEAD, and git status.
- Run shared registry `list-active` and ensure no overlapping active job owns
  this task-card/report bundle or Redis queue cleanup.
- Validate and claim this task card.
- Confirm no backend, worker, broad extraction, extraction backfill, or sample
  process is running.
- Snapshot Redis queue lengths for `score`, `ingest`, `embed`, `llm_gpu`, and
  `llm_cpu`.
- Snapshot full `score` queue message IDs, task names, and payload/title/source
  fields where available.
- Verify every score message targeted for removal matches the stale/test-origin
  `thesis_watchdog_check` pattern.
- Stop if any score message does not match the expected stale/test-origin
  pattern.

## Cleanup

- Remove only the exact validated stale score messages.
- Do not clear unrelated Redis keys.
- Do not use `FLUSHDB`.
- Prefer exact serialized-payload removal or reconstruction that preserves any
  non-matching score messages.
- Write pre-cleanup and post-cleanup snapshots as report artifacts.

## Post-Cleanup Validation

- `score` queue length is `0` or only non-matching preserved messages remain.
- `ingest`, `embed`, `llm_gpu`, and `llm_cpu` remain `0`.
- No unacked queue keys are present.
- Shared registry active-job state is inspected again.
- Confirm no extraction, backfill, canary execution, or bounded broad sample was
  run.
- Record final git status.

## Report Requirements

Write:

- `reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/README.md`
- `reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/status.json`
- `reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/pre_cleanup_score_queue_snapshot.json`
- `reports/agent_jobs/extraction_runtime_score_queue_stale_cleanup_v1_20260602/post_cleanup_score_queue_snapshot.json`

Final report must include exact messages removed, exact messages preserved if
any, queue lengths before and after, confirmation no broad runtime work was
run, whether the bounded broad sample can now be requested, and remaining
DATA_MISSING.
