---
job_id: rag_query_commentary_hybrid_source_contract_current_base_v1_20260627
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/tests/test_rag_query_route_contract.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/README.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/status.json
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/validation.json
  - reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #252
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #252 changes the public /rag/query source contract, so the API surface doc must match."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend API contract and route-test change."
worker_model_allowed: false
worker_decision_limit: "No workers used; scope is narrow and source-local."
escalation_needed: false
related_issue: 252
---

# RAG Query Commentary Hybrid Source Contract

## Objective

Close issue #252 by making `/rag/query` truthful about supported `source`
values. In this slice, unsupported `commentary` and `hybrid` values are removed
from the request schema instead of being accepted and returning a 501 stub.

## Scope

- Narrow `RagQueryRequest.source` to implemented backend-owned sources:
  `asx_docs` and `news`.
- Remove unreachable commentary/hybrid 501 branches from `/rag/query`.
- Add focused route-contract tests for accepted sources and rejected unsupported
  sources.
- Update the backend API surface doc so clients see the same contract.

## Hard Stops

- Do not implement commentary/hybrid retrieval in this slice.
- Do not add a client-side fallback or bypass backend retrieval authority.
- Do not mutate DB, Qdrant, news stores, memory stores, source PDFs,
  extraction outputs, prompts, gold labels, runtime/model/GPU/service config,
  or production data.
- Do not weaken source/evidence labels.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Focused backend route-contract tests for `/rag/query`.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff` and `check-report-artifacts`.
