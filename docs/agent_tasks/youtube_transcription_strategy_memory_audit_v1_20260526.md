---
job_id: youtube_transcription_strategy_memory_audit_v1_20260526
lane: Memory
supporting_lanes:
  - Query Orchestration
  - Reporting
  - Provenance
  - Runtime
owner: Codex
allowed_files:
  - docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/README.md
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/architecture_map.md
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/followups.md
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/runtime_probes.json
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/status.json
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/validation.json
  - reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/youtube_transcription_strategy_memory_audit_v1_20260526
mutation_mode: audit_only
production_data_access: false
---

# YouTube Transcription Strategy Memory Audit

Issue: https://github.com/0rl4nd0l/tenn/issues/100

## Objective

Audit the current YouTube/commentary-to-memory architecture and define the safe
implementation path for provenance-bound, confirmation-gated YouTube-derived
memory candidates.

## Allowed Scope

- Write only this task card and the report bundle.
- Inspect commentary, YouTube transcript, Home, and Memory code read-only.
- Run read-only process/status probes that do not mutate stores or register
  channels.

## Forbidden Scope

- No production DB, Qdrant, news, or memory writes.
- No transcript ingestion, channel registration, staged transcript approval, or
  memory mutation during this audit.
- No financial-truth writes, parser routing changes, extraction prompt changes,
  gold-label changes, runtime/model/GPU/service config mutation, or frontend or
  backend product implementation.

## Acceptance Criteria

- Distinguish implemented code, documented plans, live runtime evidence, and
  `DATA_MISSING`.
- Reconcile stale YouTube channel-watch docs against current daemon code and
  runtime evidence.
- Define routing policy for factual, speculative, and strategy-mutating YouTube
  takeaways.
- Define how Home should display pending memory-commit candidates and how the
  user can confirm, reject, edit, downgrade, or apply them.
- Preserve System Contract boundaries: backend owns ingestion/retrieval/memory
  APIs; Cockpit remains client/orchestrator; financial truth is not written from
  YouTube commentary; user thesis memory remains confirmation-gated.
- Produce small follow-up task cards/issues by lane with validation gates.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md --repo-root .`
- Read-only repo and runtime probes recorded in the report.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md`
