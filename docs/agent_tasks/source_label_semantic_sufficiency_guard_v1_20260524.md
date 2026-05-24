---
job_id: source_label_semantic_sufficiency_guard_v1_20260524
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/source_label_semantic_sufficiency_guard_v1_20260524.md
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/README.md
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/status.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/validation.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/diff-check.json
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Source Label Semantic Sufficiency Guard

## Objective

Implement a deterministic guard so raw `claim_verified` / `supports_claim` payload fields, price-only recent-update evidence, and numeric financial truth context cannot overstate claim-level support.

## Allowed Implementation

- Add or tighten backend helper logic for semantic evidence sufficiency.
- Add focused regression tests for raw flag pass-through, recent-news price-only insufficiency, financial truth numeric context, and an existing valid claim-verified case.
- Change only the narrow chat UI wording that currently renders `financial_truth` as verified sources.

## Forbidden

- No retrieval ranking changes, Qdrant/news/memory writes, source-label deletion, DATA_MISSING weakening, broad UI rewrite, parser route changes, extraction changes, or runtime changes.

## Validation

- Validate this task card.
- Run registry list/overlap checks.
- Run focused backend tests.
- Run focused Cockpit UI test if frontend wording changes.
- Run `git diff --check`.
- Run `check-diff` and record unrelated pre-existing dirt if it blocks a clean result.
