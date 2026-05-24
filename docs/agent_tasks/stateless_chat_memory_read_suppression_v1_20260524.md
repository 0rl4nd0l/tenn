---
job_id: stateless_chat_memory_read_suppression_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/stateless_chat_memory_read_suppression_v1_20260524.md
  - financial-engine_v2/backend/app/services/memory_events.py
  - financial-engine_v2/backend/app/services/cockpit_service.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/README.md
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/status.json
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/validation.json
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/runtime_proof.json
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/no_mutation_attestation.json
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/csl_stateless_smoke_response.json
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/csl_stateless_smoke_summary.md
  - reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/stateless_chat_memory_read_suppression_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Stateless Chat Memory Read Suppression

## Objective

Suppress memory read-event file writes only while `/api/cockpit/chat` is running through the explicit stateless smoke harness, then run one CSL stateless smoke with no chat-history or memory-event mutation.

## Scope

- Preserve normal chat behavior by default.
- Preserve normal memory read-event observability when chat persistence is enabled.
- For `persist_chat=False`, suppress `memory_read_events.jsonl` appends during the chat turn.
- Keep the existing stateless route/header gate intact.
- Add focused tests proving normal memory read events still write and stateless chat suppresses them.
- Reload only the backend after canonical integration if source/runtime gates pass.
- Run exactly one CSL stateless smoke after the live backend exposes the suppression-capable code.

## Forbidden

- Do not mutate Qdrant, Postgres, news stores, memory stores, financial truth, extraction, parser routing, model/GPU config, Docker topology, cron, systemd, frontend UI, or old worktrees.
- Do not change retrieval ranking, source selection, embedding configuration, vector IDs, or financial metric logic.
- Do not run extra live chat prompts beyond the minimum CSL stateless smoke needed for verification.

## Deliverables

- Minimal backend safe-extension.
- Focused tests.
- Runtime/no-mutation proof and CSL response artifacts under the report directory.
