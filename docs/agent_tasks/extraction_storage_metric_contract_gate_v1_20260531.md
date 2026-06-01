---
job_id: extraction_storage_metric_contract_gate_v1_20260531
lane: Financial Truth
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_storage_metric_contract_gate_v1_20260531.md
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/diff-check.json
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/tests/test_pipeline_stages.py
  - docs/extraction/metric_extraction_contract.md
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Storage Metric Contract Gate V1

## Objective

Align the canonical periodic-financial upsert path with Metric Ontology V1 so
persisted-only metric columns cannot be populated from extraction payloads
until extractor, evaluator, and policy support explicitly allow them.

This is a non-runtime storage-boundary hardening slice for the full metric
extraction objective. It does not authorize canary execution, broad backfill,
DB writes, source-PDF mutation, parser/prompt/schema changes, runtime reloads,
model/GPU config changes, Cockpit UI work, or GitHub mutation.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-storage-metric-contract-gate-v1-20260531`.
- Branch: `safe/extraction-storage-metric-contract-gate-v1-20260531`.
- Base: `safe/extraction-payload-gate-blocking-summary-v1-20260531` at
  `2eca7194`.
- Intended files: only this task card, the report bundle, the backend storage
  upsert helper, focused pipeline-stage tests, the metric extraction contract,
  and `docs/claude/STATE.md`.
- Contested surfaces touched: none from the AGENTS.md contested list.
- Collision risk: HIGH by financial-truth surface, resolved by isolated
  worktree, active-registry non-overlap, and exact allowlist.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target system layer: Storage boundary for backend-owned extraction truth.
- Relevant rules: backend remains the source of truth; extraction metrics must
  be explicit, source-bound, and fail closed; unsupported or persisted-only
  metric families must not be promoted into canonical rows.
- What must not change: ingestion, parser routing, prompts, schema migrations,
  source PDFs, Qdrant, embeddings, runtime services, model/GPU config, Cockpit
  UI, GitHub state, or production data stores.
- Why safe: the change only narrows which metric keys `_upsert_financial_rows`
  accepts from extractor payloads. It does not add new metrics, derive values,
  or grant write authorization; it prevents unsupported payload keys from being
  written into existing persisted-only columns.
- GPU process check required: no. This task does not start, restart, or depend
  on llama-server.

## Required Implementation

- Make `_upsert_financial_rows()` write only Metric Ontology V1 supported
  extraction output fields.
- Keep `total_equity` and `interest_expense` as persisted-only columns, but do
  not populate them from extraction payloads until a separate policy promotes
  them.
- Add a focused regression test proving payload-supplied persisted-only fields
  do not populate canonical periodic financial rows.
- Preserve existing risk-note behavior and canonical metric writes.

## Forbidden

- Runtime backend startup, route submission, canary execution, broad backfill,
  direct SQL, source-PDF mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, GitHub mutation, service restart, and
  schema migration.

## Required Validation

- Task card validation and registry claim.
- Focused pytest for the new pipeline-stage regression.
- Relevant pipeline-stage pytest.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --cached --check`.
- Registry release.
