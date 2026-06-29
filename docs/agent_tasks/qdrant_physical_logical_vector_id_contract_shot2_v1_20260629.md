---
job_id: qdrant_physical_logical_vector_id_contract_shot2_v1_20260629
lane: Provenance
supporting_lanes:
  - Query Orchestration
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/README.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/STATE.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/DECISIONS.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/NEXT_GOAL.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/ARCHITECTURE_REVIEW.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/VALIDATION.md
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/diff-check.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/guard_preflight.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/registry_claim.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/registry_release.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/status.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/ledger_claimed.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/ledger_started.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/ledger_done.json
  - reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629/issue_snapshot.json
  - docs/architecture/SYSTEM_CONTRACT.md
  - docs/architecture/01_system_overview.md
  - docs/architecture/03_data_model.md
  - docs/architecture/04_ingestion_pipeline.md
  - docs/architecture/06_embeddings_and_vector_store.md
  - docs/architecture/08_backfill_contract.md
  - docs/architecture/11_rebuild_and_recovery.md
  - docs/architecture/22_memory_ownership_map.md
  - financial-engine_v2/backend/app/services/embeddings.py
  - financial-engine_v2/backend/app/services/pipeline_stages.py
  - financial-engine_v2/backend/app/services/commentary_ingest.py
  - financial-engine_v2/backend/tests/test_architecture_invariants.py
  - financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py
  - financial-engine_v2/backend/tests/test_qdrant_resolution.py
  - financial-engine_v2/backend/tests/test_rag_payload_guardrails.py
  - financial-engine_v2/scripts/inspect_qdrant_collection.py
  - financial-engine_v2/scripts/embed_docs_to_qdrant.py
approval_required: true
owner_approval: USER_APPROVED_PROCEED_RETAIN_UUIDV5_PHYSICAL_MAPPING_2026-06-29
publish_approval: USER_APPROVED_REBASE_PUSH_OPEN_DRAFT_PR_2026-06-29
refresh_approval: USER_APPROVED_REFRESH_PR473_ON_CANONICAL_2A4A1C1_2026-06-29
allow_unapproved_safe_extension: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: push_branch_and_open_draft_pr_only
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/00_README.md
  - docs/architecture/SYSTEM_CONTRACT.md
  - docs/architecture/03_data_model.md
  - docs/architecture/04_ingestion_pipeline.md
  - docs/architecture/06_embeddings_and_vector_store.md
  - docs/architecture/08_backfill_contract.md
  - docs/architecture/11_rebuild_and_recovery.md
  - docs/architecture/22_memory_ownership_map.md
docs_changed:
  - docs/architecture/SYSTEM_CONTRACT.md
  - docs/architecture/01_system_overview.md
  - docs/architecture/03_data_model.md
  - docs/architecture/04_ingestion_pipeline.md
  - docs/architecture/06_embeddings_and_vector_store.md
  - docs/architecture/08_backfill_contract.md
  - docs/architecture/11_rebuild_and_recovery.md
  - docs/architecture/22_memory_ownership_map.md
docs_followup: "none"
reason: "Issue #266 has owner approval to retain deterministic UUIDv5 physical Qdrant point IDs while preserving logical vector IDs in payload, docs, and tests; follow-up approvals permit rebasing onto current canonical, pushing the branch, opening draft PR #473, and refreshing that PR onto canonical 2a4a1c1."
task_tier: large
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Vector-store identity policy touches architecture invariants, provenance, rebuild semantics, and tests."
worker_model_allowed: false
worker_decision_limit: "No workers; policy decision remains with owner/orchestrator."
escalation_needed: false
related_issue: 266
---

# Qdrant Physical Versus Logical Vector ID Contract Shot 2

## Objective

Resolve issue #266 under approved policy
`RETAIN_UUIDV5_PHYSICAL_MAPPING`.

The implementation must keep `document_id:chunk_index` as the canonical logical
vector/chunk ID and allow deterministic UUIDv5 only as the physical Qdrant
point ID required by the adapter/storage boundary.

## Allowed Implementation

- Preserve logical vector IDs in `asx_docs` payloads as `logical_vector_id`.
- Preserve commentary logical chunk IDs in staged payloads as
  `logical_vector_id`.
- Centralize deterministic physical point ID mapping in the backend Qdrant
  adapter.
- Update the read-only Qdrant inspector to distinguish physical point IDs from
  logical vector IDs.
- Update docs and focused tests for the logical/physical split.

## Forbidden

- No production Qdrant, Postgres, news, memory, or canonical financial truth
  mutation.
- No live reindexing, rebuild, service restart, runtime/model/GPU config,
  parser prompt, source PDF, or gold-label changes.
- No random UUID vector/chunk IDs.
- No frontend/Cockpit bypass of backend vector-store authority.
- No GitHub writes except pushing this task branch and opening a draft PR under
  the 2026-06-29 follow-up approval.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
- Focused backend pytest for vector ID, Qdrant resolution, architecture, and
  payload guardrail tests.
- `python3 -m py_compile` for changed Python modules/scripts.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
- `git diff --check`

## Hard Stops

- Active duplicate tracker or PR found.
- Validation requires production Qdrant or live reindexing.
- Proposed remediation weakens deterministic identity, provenance, or rebuild
  semantics.
