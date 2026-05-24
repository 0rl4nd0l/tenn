---
job_id: source_label_semantic_sufficiency_live_smoke_v1_20260524
title: Source label semantic sufficiency live stateless smoke
owner: Codex
lane: Provenance
supporting_lanes:
  - Query Orchestration
  - Evaluation
  - Reporting
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524
allowed_files:
  - docs/agent_tasks/source_label_semantic_sufficiency_live_smoke_v1_20260524.md
  - reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/README.md
  - reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/status.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/diff-check.json
forbidden:
  - source_code_edits
  - frontend_edits
  - qdrant_mutation
  - postgres_mutation
  - news_store_mutation
  - memory_store_mutation
  - chat_history_or_state_writes
  - memory_read_events_writes
  - parser_extraction_or_canonical_financial_truth_changes
  - docker_rebuild
  - broad_runtime_restart
  - cron_systemd_model_gpu_or_worker_changes
  - unrelated_task_card_cleanup
---

# Source Label Semantic Sufficiency Live Stateless Smoke

## Objective

Validate that the canonical live Tenn backend is serving commit
`a6db9760621e274c4621e98eee338a7b7ba34010` and run narrow stateless live
smokes proving source-label semantic sufficiency is visible in user-facing chat
answers and metadata.

## Scope

- Confirm canonical repo identity, branch, HEAD, recent commits, dirty state, and
  worktrees.
- Confirm commit `a6db9760621e274c4621e98eee338a7b7ba34010` is `HEAD` or an
  ancestor of `HEAD`.
- Inspect active registry jobs, validate this task card, check overlap, claim the
  job only if no unsafe active overlap exists, and release the claim before
  closeout.
- Locate the existing stateless Cockpit chat smoke harness and use only that
  harness for live prompt validation.
- Confirm backend health and whether the live backend is serving canonical code
  where safely inspectable.
- Perform a backend-only reload only if the backend is not serving canonical code.
- Run exactly two stateless live smokes when the harness is safe:
  - Smoke A: recent-news/update question with price-only insufficiency.
  - Smoke B: financial-truth numeric context must not verify event/news claims.
- Prove each smoke did not write chat history, state, memory read events, Qdrant,
  Postgres, news, memory, or canonical financial truth where safe checks exist.
- Record confirmed facts, inferred facts, DATA_MISSING, smoke evidence, mutation
  proof, final verdict, final registry state, and final git status.

## Allowed Runtime Action

- Backend-only reload/restart if required to serve canonical commit `a6db976`.

Do not restart Qdrant, Postgres, workers, frontend, llama, Ollama, cron, GPU, or
model services unless current operational docs prove the backend-only reload
requires it.

## Forbidden

- No source code edits.
- No frontend edits.
- No backend implementation edits.
- No Qdrant mutation.
- No Postgres mutation.
- No news store mutation.
- No memory store mutation.
- No chat history or state writes.
- No `memory_read_events.jsonl` writes.
- No parser, extraction, or canonical financial truth changes.
- No Docker rebuild.
- No broad runtime restart.
- No cron, systemd, model, GPU, worker, or topology changes.
- No cleanup of unrelated untracked task cards.

## Deliverables

- `reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/README.md`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/status.json`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/source_label_semantic_sufficiency_live_smoke_v1_20260524.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/source_label_semantic_sufficiency_live_smoke_v1_20260524.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/source_label_semantic_sufficiency_live_smoke_v1_20260524.md` when overlap checks allow it
- Backend health before and after reload if reload is required
- Exactly two stateless smokes with `X-Tenn-Stateless-Smoke: 1` if the safe
  harness exists
- Mutation checks for chat state, `memory_read_events.jsonl`, Qdrant, Postgres,
  news, memory, and canonical financial truth where safe checks exist
- `jq empty reports/agent_jobs/source_label_semantic_sufficiency_live_smoke_v1_20260524/status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/source_label_semantic_sufficiency_live_smoke_v1_20260524.md`
- Final registry `list-active`
