---
job_id: query_orchestration_inference_engine_phase1_audit_closeout_v1
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1
allowed_files:
  - docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/README.md
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/call_site_inventory.md
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/call_site_inventory.json
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/phase2_plan.md
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/status.json
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/validation.json
  - reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_closeout_v1/diff-check.json
inspect_only_surfaces:
  - financial-engine_v2/backend/app/services/llm.py
  - financial-engine_v2/backend/app/services/router.py
  - financial-engine_v2/backend/app/services/llamacpp_runtime.py
  - financial-engine_v2/backend/app/services/embeddings.py
  - financial-engine_v2/backend/app/services/llamacpp_embeddings.py
  - financial-engine_v2/backend/app/celery_app.py
  - financial-engine_v2/backend/app/worker_tasks.py
  - financial-engine_v2/backend/app/services/**
  - financial-engine_v2/backend/app/modules/**
  - scripts/**
---

# Task

Close out GitHub issue #138 by producing the missing read-only Phase 1 inference-engine audit report from current repository evidence.

# GitHub tracking

- Issue: https://github.com/0rl4nd0l/tenn/issues/138
- PR link policy: use `Refs #138`; this is audit evidence, not product remediation.

# Target layer and contract

- Target layer: Query Orchestration inference/runtime call-site map.
- Relevant contract rules: backend owns authoritative retrieval and model-facing data paths; no alternate financial truth; no hidden fallback masking; no runtime/model/GPU/service config mutation.
- What must not change: `llm.py`, `router.py`, `llamacpp_runtime.py`, embeddings, Celery routing, Cockpit chat, financial truth, memory, DB, Qdrant, news, parser routing, prompts, gold labels, or runtime services.
- Safety basis: report-only writes are limited to this task card and the listed closeout report artifacts.

# Required analysis

1. Verify the released Phase 1 artifact state.
2. Map direct call sites for `generate_json`, `embed_texts`, `route_request`, and `llm_fn`.
3. Document metadata keys and runtime override paths.
4. Identify fallback logic and responsibilities.
5. Document queue/runtime/provider leakage points.
6. Identify safe migration seams.
7. Assess backwards compatibility risks.
8. Propose report-only `InferenceRequest` and `InferenceResult` schemas.
9. Propose Phase 2+ implementation stages.
10. List `DATA_MISSING` and validation gaps.

# Hard stops

Stop and report only if:
- a duplicate PR already covers #138
- task-card validation fails
- registry overlap is active on this write set
- product code changes are required
- runtime/service restart is required
- production data access is required
- DB/Qdrant/news/memory/financial truth mutation is required

# Validation

Run:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- registry claim/release
- read-only `rg` call-site map checks
- JSON parse checks for generated JSON artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `git diff --check`
- `git diff --cached --check`

# Definition of done

- Missing Phase 1 evidence is recorded in the report bundle.
- Call-site, metadata, fallback, leakage, migration, schema, and Phase 2 planning sections are complete or explicitly `DATA_MISSING`.
- No product code or forbidden surface is changed.
- Draft PR links #138 with `Refs #138`.
