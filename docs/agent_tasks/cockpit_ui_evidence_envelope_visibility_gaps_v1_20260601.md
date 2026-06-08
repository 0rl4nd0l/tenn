---
job_id: cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601
title: Cockpit UI evidence envelope visibility gaps
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601
allowed_files:
  - docs/agent_tasks/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601.md
  - reports/agent_jobs/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601/README.md
  - reports/agent_jobs/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601/status.json
  - reports/agent_jobs/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601/diff-check.json
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/lib/cockpit-chat-actionability.ts
  - cockpit-ui/lib/cockpit-types.ts
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/lib/cockpit-news-actionability.ts
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
  - cockpit-ui/lib/cockpit-chat-actionability.test.ts
  - cockpit-ui/lib/cockpit-news-actionability.test.ts
forbidden:
  - db_qdrant_news_or_memory_mutation
  - canonical_financial_truth_changes
  - backend_source_label_relaxation
  - parser_routing_changes
  - extraction_prompt_changes
  - gold_label_changes
  - runtime_model_gpu_or_service_config_changes
  - broad_ui_redesign
  - treating_context_only_no_hit_degraded_or_data_missing_evidence_as_claim_verified
  - unrelated_route_rewrites
---

# Cockpit UI Evidence Envelope Visibility Gaps

## Objective

Resolve GitHub issue #175 by making the Cockpit chat and standalone News UI
show the available evidence-envelope vocabulary instead of hiding material
weak, degraded, no-hit, context-only, or `DATA_MISSING` states behind one
primary label.

## Scope

- Surface `local_news_context` in the chat analyst shell when metadata provides
  it.
- Preserve and display secondary `evidenceLabels` in chat source details
  without upgrading those labels to claim-verified evidence.
- Surface shared evidence-envelope fields in standalone News when the backend
  supplies them.
- Show explicit `DATA_MISSING` where the standalone News envelope is absent.
- Keep #83 and #87 ownership boundaries intact: no backend route parity,
  projection, retrieval, or A2M-specific remediation in this task.

## Boundaries

- Do not mutate DB, Qdrant, news stores, memory stores, or production data.
- Do not change backend source-label semantics, evidence guards, ranking,
  retrieval, BFF contracts, parser routing, extraction prompts, or gold labels.
- Do not claim context-only, no-hit, degraded, duplicate, snippet-only, or
  `DATA_MISSING` evidence as claim-verified.
- Do not start, stop, reload, rebuild, or reconfigure runtime, model, GPU, or
  service surfaces.
- Do not touch unrelated shared checkout dirt or active Financial Truth files.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601.md`
- Focused frontend unit tests for chat and News evidence-envelope presentation.
- Focused eslint/type checks where available.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_evidence_envelope_visibility_gaps_v1_20260601.md`
- Release the registry claim before final closeout.
