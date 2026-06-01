---
job_id: extraction_metric_ontology_prepersistence_gate_v1_20260531
lane: Financial Truth
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_ontology_prepersistence_gate_v1_20260531.md
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/diff-check.json
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/claude/STATE.md
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Metric Ontology Pre-Persistence Gate

## Objective

Harden the report-local confirmed-metric payload scorecard so unsupported,
persisted-only, planned, ambiguous, and internal-only metric families cannot be
treated as absent merely because the actual payload used a contract alias or
internal field name.

This is a non-runtime Evaluation/Financial Truth hardening slice for the full
metric extraction objective. It does not authorize canary execution, broad
backfill, DB writes, source-PDF mutation, parser/prompt/schema changes, or
GitHub mutation.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-metric-ontology-prepersist-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-prepersist-v1-20260531`.
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at `0320f645`.
- Intended files: only this task card, the report bundle, the scorecard helper,
  its focused tests, and `docs/claude/STATE.md`.
- Contested surfaces touched: none from the AGENTS.md contested list; this
  touches backend extraction-evaluation helper code only.
- Collision risk: MEDIUM because this touches Financial Truth/Evaluation code,
  but it is isolated and has no runtime or datastore mutation.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target layer: Evaluation around backend-owned extraction truth.
- Relevant rules: backend remains the authority; extraction/evaluation must not
  invent, substitute, or promote unsupported values; no parallel truth system;
  fail closed on ambiguity.
- What must not change: extraction parser, prompts, schema, source PDFs,
  Qdrant, embeddings, runtime services, model/GPU config, canonical financial
  rows, Cockpit UI, or GitHub state.
- Why safe: the change is limited to report-local scorecard classification and
  tests. It can only make unsupported actual payload facts more visible to the
  gate; it cannot authorize canonical writes.
- GPU process check required: no. This task does not start or use llama-server.

## Required Implementation

- Add deterministic actual-payload key resolution from the metric contract
  family table.
- Ensure persisted-only/internal-only/planned/ambiguous/unsupported aliases are
  detected in actual payloads and block the pre-persistence gate when present.
- Keep supported aliases such as cash/cash-equivalent family names scoreable
  only when already supported by `METRIC_FIELDS`.
- Add focused tests for:
  - `total_equity`
  - `interest_expense`
  - `finance_costs`
  - `total_assets`
  - planned metrics
  - internal-only aliases such as `debt_borrowings` / `total_debt`

## Forbidden

- Runtime backend startup, route submission, canary execution, broad backfill,
  direct SQL, source-PDF mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, and GitHub mutation.

## Required Validation

- Task card validation and claim.
- Focused pytest for `test_extraction_gold_eval_scorecard.py`.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --cached --check`.
