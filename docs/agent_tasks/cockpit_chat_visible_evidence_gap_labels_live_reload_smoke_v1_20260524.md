---
job_id: cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524
title: Cockpit chat visible evidence-gap labels live reload smoke
owner: Codex
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524
allowed_files:
  - docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md
  - reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524/
forbidden:
  - source_code_edits
  - frontend_edits
  - qdrant_mutation
  - postgres_mutation
  - news_store_mutation
  - memory_store_mutation
  - state_db_chat_history_writes
  - parser_extraction_or_canonical_financial_truth_changes
  - docker_rebuild
  - cron_systemd_model_gpu_or_runtime_topology_changes
  - unrelated_task_card_cleanup
---

# Cockpit Chat Visible Evidence-Gap Labels Live Reload Smoke

## Objective

Validate that the canonical live Tenn backend is serving commit `0973349937cd` and run one safe stateless CSL chat smoke proving the visible answer surfaces evidence gaps instead of unqualified price, technical, or company-memory claims.

## Scope

- Resolve canonical repo identity, branch, HEAD, recent commits, git status, and commit ancestry.
- Validate this task card before live work.
- Inspect active registry jobs and claim/release this job when allowed by the registry.
- Confirm canonical source contains the visible evidence-gap presentation guard from `0973349937cd`.
- Confirm live backend health and whether it serves canonical `/home/l4nd0/tenn`.
- Perform a backend-only reload/restart only if required to serve canonical code.
- Run exactly one stateless CSL chat smoke using the established stateless harness/header with `X-Tenn-Stateless-Smoke: 1`.
- Inspect metadata and visible answer for evidence-gap presentation.
- Prove the stateless smoke did not write chat history, state, memory-read events, Qdrant, Postgres, news, memory, or canonical financial truth.

## Allowed Runtime Action

- Backend-only reload/restart only if required to serve canonical code.

Do not restart Qdrant, Postgres, news, memory, llama, frontend, cron, workers, Docker infrastructure, or GPU/model services unless current operational docs prove the backend-only reload procedure requires it.

## Forbidden

- No source code edits.
- No frontend edits.
- No Qdrant mutation.
- No Postgres mutation.
- No news store mutation.
- No memory store mutation.
- No `state.db`/chat-history writes except proving the stateless smoke did not write.
- No parser, extraction, or canonical financial truth changes.
- No Docker rebuild.
- No cron, systemd, model, GPU, or runtime topology changes.
- No cleanup of unrelated untracked task cards.

## Deliverables

- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524/status.json`
- Trimmed/redacted smoke response artifact if safe and useful.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md` when overlap checks allow it
- Backend health check before and after reload if reload is required
- Exactly one stateless CSL smoke with `X-Tenn-Stateless-Smoke: 1`
- Mutation checks for state/chat history, `memory_read_events.jsonl`, Qdrant/Postgres/news/memory/canonical truth where supported by existing checks
- JSON validation for `status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md`
- Final registry `list-active`
