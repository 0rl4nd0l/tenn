---
job_id: cockpit_chat_visible_evidence_gap_labels_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/README.md
  - reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/status.json
  - reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/validation.json
  - reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Chat Visible Evidence Gap Labels

## Objective

When Cockpit chat response metadata includes `market_data_missing`,
`unsupported_or_not_verified`, `metric_extraction_missing`, or
`missing_required_evidence`, the visible answer text must surface those gaps
clearly and must not present price, technical, or company-memory lines as
verified conclusions.

## Scope

- Add a post-synthesis response-presentation guard for the existing
  `/api/cockpit/chat` response envelope.
- Preserve existing evidence labels and source envelope behavior.
- Keep the change metadata/text-only after visible sources are built.
- Cover non-streaming, streaming, and stateless smoke response paths with
  focused tests.

## Forbidden

- Do not touch Qdrant, news stores, memory stores, extraction, parser routing,
  canonical financial truth, retrieval ranking, source selection, runtime
  topology, Docker, cron, systemd, model, or GPU configuration.
- Do not install dependencies or run unrelated broad validation.
- Do not change old TUI behavior unless it is already part of the backend
  response envelope under test.

## Deliverables

- Backend presentation guard.
- Focused backend tests.
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/status.json`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/validation.json`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/diff-check.json`

## Validation

- Validate this task card.
- Run registry `list-active`, `check-overlap`, claim, and release.
- Run focused compile, pytest, and ruff.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Validate JSON report artifacts.
