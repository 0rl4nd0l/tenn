---
job_id: backend_chat_evidence_guard_canonical_integrate_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/backend_chat_evidence_guard_canonical_integrate_v1_20260524.md
  - docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/
  - reports/agent_jobs/backend_chat_evidence_guard_canonical_integrate_v1_20260524/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/backend_chat_evidence_guard_canonical_integrate_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Backend Chat Evidence Guard Canonical Integration

Canonical integration task for source commit
`4021a1a981b8f9b47b83ee34012a5187ad405dcb` from
`/home/l4nd0/tenn-backend-chat-evidence-guard-v1-20260524`.

## Scope

- Verify whether the backend chat evidence guard commit is already present in
  canonical `/home/l4nd0/tenn`.
- Integrate only the already validated isolated commit if it is not already
  present or patch-equivalent.
- Run focused validation only.

## Boundaries

- Do not start new backend chat implementation.
- Do not touch Qdrant, news, memory, DB, extraction, parser routing, runtime,
  Docker, cron, model, GPU, or frontend UI files.
- Do not clean unrelated task-card dirt.
