---
job_id: chat_context_only_local_news_sufficiency_v1_20260602
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_news_retrieval_eval.py
  - financial-engine_v2/backend/tests/test_chat_route.py
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/README.md
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/STATE.md
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/VALIDATION.md
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/REVIEW.md
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/PR_BODY.md
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/status.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/validation.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/diff-check.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/guard_preflight.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/registry_claim.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/registry_release.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/ledger_claimed.json
  - reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/ledger_started.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
github_mutation_approval: "USER_APPROVED_PROCEED_AFTER_PUBLISH_PATH_2026-06-29"
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - issue #265
docs_changed: []
docs_followup: NONE
reason: "Issue #265 tightens existing backend evidence metadata behavior without changing the public API shape or operator workflow."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend evidence-envelope fix with existing regression coverage."
worker_model_allowed: false
worker_decision_limit: "No workers used; issue is narrow and already evidence-backed."
escalation_needed: false
related_issue: 265
---

# Chat Context-Only Local News Sufficiency

## Objective

Resolve issue #265 by making direct `chat_with_tenn()` keep recent/latest/news
evidence gaps visible when the only local-news source is `context_only`.

## Scope

- Keep context-only local news visible in the source list.
- Mark recent/latest/news/update prompts as `missing_required_evidence` and
  `insufficient_for_recent_news` when no source has both `local_news_context`
  and `claim_verified`.
- Preserve existing valid `claim_verified + local_news_context` behavior.
- Add focused regression coverage for the direct chat response envelope and the
  `/chat` analysis route preserving the envelope returned by `chat_with_tenn()`.

## Forbidden

- Do not mutate DB, Qdrant, Redis, news stores, memory stores, source PDFs,
  canonical financial truth, extraction outputs, prompts, gold labels,
  runtime/model/GPU/service config, or production data.
- Do not move evidence verification into Cockpit/frontend code.
- Do not weaken `chat_evidence_guard.py`.
- Do not turn `context_only`, broad `local_news_context`, no-hit, or degraded
  evidence into `claim_verified`.
- Do not create, edit, close, comment on, or label GitHub issues/PRs except
  opening the approved draft PR for this task branch.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .`
- Focused RED/GREEN pytest for `test_news_retrieval_eval.py`.
- Focused route-envelope pytest for `test_chat_route.py`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .`

## Hard Stops

- Active registry overlap appears for the same files or issue.
- A direct PR already covers issue #265.
- Fix requires production data, runtime services, DB/Qdrant/news/memory writes,
  frontend relabeling, or weakening source/evidence labels.
- Focused validation fails without a source-bounded explanation.
