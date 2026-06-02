---
job_id: extraction_residual_candidate_filtering_broad_sample_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_candidate_filtering_broad_sample_v1_20260602.md
  - reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/bounded_broad_sample_results.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/app/services/method_isolated_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_eval.py
  - financial-engine_v2/backend/tests/test_extraction_eval_harness.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_llm_separation.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/test_extraction_review_service.py
  - financial-engine_v2/backend/tests/test_extraction_run_observability.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested this bounded residual candidate/source filtering and one same-size broad sample only if runtime readiness is clean on 2026-06-02.
---

# Extraction Residual Candidate Filtering Broad Sample V1

## Objective

Add narrow deterministic filters for the residual false-positive document
classes found in the latest bounded broad extraction sample after the PLS
statement-evidence fix:

- buyback announcements
- share-purchase-plan and unit-purchase-plan result/final-issue notices
- purchase-order and customer-agreement announcements
- AGM result title variants
- presentation/update/commercial-announcement classes that lack formal
  Appendix, financial-statement, or explicit A/H/Q period-report evidence

Then rerun exactly one bounded broad sample of the same size as the previous
sample only if runtime readiness is clean.

This is not a full ticker-universe extraction, broad backfill, canonical truth
promotion, source-PDF mutation, extraction prompt/gold-label change, runtime
model/GPU config change, Cockpit UI change, schema migration, or unrelated
cleanup.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION + BOUNDED VALIDATION

Intended files: this task card, the report bundle, multipass extraction
service, focused extraction tests, and the broad extraction helper only if
required by validation.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM by financial-truth semantics and bounded runtime
validation; resolved by exact allowlist, shared-registry claim, no active job
overlap, deterministic classification only, and no canonical data-store
mutation.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layers: Extraction and Evaluation runtime.

Relevant contract rules: backend remains the sole authority; extraction must
only structure explicit source evidence; metric extraction may not infer,
substitute, or fabricate; source-document gates must fail closed; no fallback,
parallel implementation, storage mutation, retrieval mutation, or vector
behavior change is allowed.

What must not change: prompts, gold labels, source PDFs, DB/Qdrant/news/memory
stores, canonical truth promotion, schema/migrations, Cockpit UI, backend route
semantics, full backfill authorization, runtime/model/GPU config, and existing
valid annual, half-year, Appendix 4C/4D/4E/5B, and financial-statement
candidates.

Why safe: the implementation is limited to deterministic source-document
classification before metric extraction. It excludes source classes that are
not formal financial-report candidates unless explicit formal Appendix,
financial-statement, or A/H/Q period-report evidence is present. Ambiguous
cases remain fail-closed.

GPU process check required: yes only for the optional bounded sample. Do not
spawn or restart llama-server unless runtime readiness gates are clean and only
the canonical route is used.

## Required Preflight

- Confirm repo path, branch, HEAD, and remote.
- Run `git status`, `git worktree list`, and shared registry `list-active`.
- Validate and claim this task card.
- Read the latest broad-runtime report from the corrected hyphenated worktree
  path if the underscore path is absent.
- Before any runtime sample, verify `/api/health`, loaded commit, queue idle,
  GPU state, source paths, and no conflicting jobs.

## Validation

- Focused pytest for candidate-filter tests.
- `py_compile` and Ruff on touched Python.
- `git diff --check`.
- Task-card `check-diff`.
- JSON validation for report artifacts.
- Verify no source PDFs are staged.
- If runtime readiness is clean, rerun only one bounded broad sample with
  count `8`, seed `20260601`, and `/data/asx/docs`; no full
  extraction/backfill.

## Report Requirements

Write:

- `reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/README.md`
- `reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/status.json`
- `reports/agent_jobs/extraction_residual_candidate_filtering_broad_sample_v1_20260602/bounded_broad_sample_results.json` if sampled

Include filters added, valid-source regressions protected, tests/results,
runtime readiness verdict, bounded sample outcome, remaining DATA_MISSING,
explicit "no full extraction/backfill run", and Project Memory save
recommendation.
