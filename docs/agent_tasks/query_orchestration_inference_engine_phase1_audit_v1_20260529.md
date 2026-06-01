---
job_id: query_orchestration_inference_engine_phase1_audit_v1_20260529
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Evaluation
owner: Gemini/Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_v1_20260529
allowed_files:
  - docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_v1_20260529.md
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_v1_20260529/status.json
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_v1_20260529/diff-check.json
inspect_only_surfaces:
  - financial-engine_v2/backend/app/services/llm.py
  - financial-engine_v2/backend/app/services/router.py
  - financial-engine_v2/backend/app/services/llamacpp_runtime.py
  - financial-engine_v2/backend/app/celery_app.py
  - financial-engine_v2/backend/app/services/**
---
# Task Card: query_orchestration_inference_engine_phase1_audit_v1_20260529

## Objective
Produce a detailed call-site and duplication audit for the Unified Inference Engine proposal. This is Phase 1 of the Inference Engine deepening project.

## Execution Posture
- **Phase 1 remains AUDIT ONLY / report-only.**
- Do NOT mutate: `llm.py`, `router.py`, `llamacpp_runtime.py`, `celery_app.py`, `inference_engine.py`, or `inference_schema.py`.
- Final output must be a detailed audit report under `reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_v1_20260529/`.

## Phase 1 Requirements
1. Map all direct call sites for `generate_json`, `embed_texts`, `route_request`, `llm_fn`.
2. Document metadata keys and runtime override paths currently used.
3. Identify fallback logic locations and responsibilities.
4. Document queue/runtime/provider leakage points.
5. Identify safe migration seams.
6. Assess backwards-compatibility risks.
7. Propose `InferenceRequest` / `InferenceResult` schema (report-only).
8. Propose a staged implementation plan for Phase 2+.
9. List files for Phase 2 changes (do not change now).
10. Document `DATA_MISSING` and validation gaps.

## Constraints
- Stop on invalid task card.
- Stop on active registry conflict.
- Stop if production data access is required.
- Stop if code mutation is required.
- Stop if service/runtime restart is required.
- Stop if DB/Qdrant/canonical truth touch is required.

## Status
- [ ] Detailed call-site mapping
- [ ] Metadata override documentation
- [ ] Fallback logic identification
- [ ] Interface leakage audit
- [ ] Proposed schemas and implementation plan
- [ ] Final report generation
