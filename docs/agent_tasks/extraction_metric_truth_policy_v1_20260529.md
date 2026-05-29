---
job_id: extraction_metric_truth_policy_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_truth_policy_v1_20260529.md
  - reports/agent_jobs/extraction_metric_truth_policy_v1_20260529/README.md
  - reports/agent_jobs/extraction_metric_truth_policy_v1_20260529/status.json
  - reports/agent_jobs/extraction_metric_truth_policy_v1_20260529/diff-check.json
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_eval_harness.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/clv_h_2026-01-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/ctm_a_2025-12-31_canary_regression.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_metric_truth_policy_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Metric Truth Policy V1

## Objective

Complete the next bounded metric-extraction hardening slice before any third
#96 canary batch.

This task formalizes source-document classification, Scale Policy V1, canonical
metric ontology reporting, period-type semantics, and real canary-regression
fixtures using only source-bound evidence. It must prefer failed extraction,
abstention, or quarantine over inferred corrections.

## Required Behavior

- Source-document classification must expose a deterministic policy result and
  preserve the existing advisory-only extraction/candidate guard.
- Scale Policy V1 must treat explicit table units as authoritative, allow plain
  dollar table columns as `units`, keep currency separate, keep `unknown` scale
  blocked, and avoid broad non-AUD verbal-scale normalization.
- Metric ontology reporting must identify the current canonical version and
  keep unsupported, ambiguous, and internal-only families out of canonical use.
- Period semantics must include `period_type` in context validation and
  scorecard period-failure classification.
- Real canary-regression fixtures for CLV/CTM must be source-verified from local
  PDFs and must make the prior bad canary payloads score as non-trusted.

## Hard Stops

- Do not run a third canary batch.
- Do not run broad backfill.
- Do not perform production DB writes.
- Do not perform direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing.
- Do not change extraction prompts.
- Do not mutate existing gold labels outside the new regression fixtures.
- Do not change runtime, model, or GPU config.
- Do not restart services.
- Do not implement Cockpit UI.
- Do not add schema migrations.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase
  operations.

## Validation

- Task-card validation, registry overlap check, claim, diff check, and release.
- Focused pytest for changed extraction/eval/scorecard tests.
- `py_compile` for touched Python modules and tests.
- Ruff for touched Python modules and tests.
- JSON validation for fixtures and report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- Final registry read-only check and git status.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Exact policy changes and canary-failure mapping.
- Validation commands and results.
- Confirmation that no third canary/backfill/datastore mutation ran.
- Remaining blockers before full accurate extraction graduation.
