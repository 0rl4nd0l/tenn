---
job_id: recent_news_positive_claim_verified_fixture_v1_20260524
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/recent_news_positive_claim_verified_fixture_v1_20260524.md
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/README.md
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/status.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/validation.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/diff-check.json
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Recent News Positive Claim-verified Fixture

## Objective

Add focused regression coverage proving deterministic `recent_news_event` evidence can still verify recent-news/update claims after the stricter source-label sufficiency guard in `a71a4fbeb447`.

## Required Audit

- Locate the stricter recent-news/source-label guard.
- Locate existing chat-evidence guard tests and fixture style.
- Locate an existing valid `recent_news_event` construction path.
- Determine whether tests are enough or a narrow helper adjustment is needed.

## Required Behavior

- Deterministic `recent_news_event` evidence may satisfy recent-news/update intent.
- `claim_verified_source_count` increments only for sufficient role/type/recency evidence.
- `context_only`, `local_news_context`, price-only, and `financial_truth` numeric context remain insufficient.
- Raw `supports_claim` / `claim_verified` booleans cannot self-promote without sufficient labels/role.

## Forbidden

- No retrieval ranking rewrite, Qdrant/news/memory mutation, prompt-only fake verification, broad UI work, parser changes, or source-label weakening.

## Validation

- Focused backend pytest for chat evidence/source-label tests.
- Focused Ruff if Python changed.
- `git diff --check`.
- Task-card `check-diff`.
