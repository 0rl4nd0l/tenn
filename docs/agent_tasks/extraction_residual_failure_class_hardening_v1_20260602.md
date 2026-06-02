---
job_id: extraction_residual_failure_class_hardening_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_failure_class_hardening_v1_20260602.md
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/case_audit.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/source_classifier_probe.json
  - reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602/side_effect_audit.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/app/services/method_isolated_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_real.py
  - financial-engine_v2/backend/tests/test_extraction_payload_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_source_asset_manifest.py
  - financial-engine_v2/backend/tests/test_extraction_storage_metric_contract.py
  - financial-engine_v2/backend/tests/test_extraction_terminal_state_candidate_manifest.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_failure_class_hardening_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested audit and narrow hardening of four residual bounded-sample failure classes on 2026-06-02.
---

# Extraction Residual Failure Class Hardening V1

## Objective

Audit and harden the four residual bounded-sample extraction failure classes
before any further sample, canary, backfill, or canonical truth promotion.

Latest bounded broad sample reference: commit
`32e39089527137a1197a5a169ab1e8699c9155a8`, result `ok=4`,
`ok_low_confidence=0`, `failed=4`. This is modest improvement, not broad
graduation.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Financial Truth.
- Execution mode: AUDIT FIRST; SAFE EXTENSION only for narrow deterministic
  guards/tests.
- Intended files: this task card, this report bundle, narrow extraction
  classifier/diagnostic files, focused tests, and metric extraction contract
  docs only if needed.
- Contested surfaces touched: none from AGENTS.md.
- Collision risk: MEDIUM/HIGH because extraction truth gates are sensitive;
  proceed only if registry overlap remains non-conflicting.

## Contract Check

- Target system layers: Extraction and Metric Extraction, with Evaluation and
  Provenance report artifacts.
- Relevant contract rules: source PDFs are read-only; extraction must extract
  only explicit source values; ambiguous values return null/fail closed; no
  hidden fallbacks, substitutions, prompt changes, or parallel systems.
- What must not change: source PDFs, prompts, gold labels, canonical truth
  promotion state, database rows, Qdrant, news, memory, workers, runtime model
  or GPU config, service state, unrelated dirty files, random samples, and
  backfills.
- Why safe: the work begins as read-only case classification and only applies
  source-bound deterministic classifier exclusions or report-only diagnostics
  when directly supported by current evidence and focused tests.
- GPU process check required: no. This task must not start llama-server, restart
  services, or run another broad sample/backfill.

## Residual Cases

- AZJ half-year FY2023 results: `insufficient_metrics:1`; real half-year
  results, extraction coverage gap.
- ABE annual report 2022: `scale_unknown`; real annual report, source scale
  evidence unresolved.
- CRS base metals drilling results:
  `non_financial_update_without_formal_statements`; exploration/drill-results
  update admitted then blocked.
- WBC FY2023 notable items: `insufficient_metrics:1`; pre-results notable-items
  notice, not a formal full-year report.

## Allowed Safe Extensions

- Source-title/doc-type exclusions for CRS/WBC-like false positives.
- Report-only diagnostics for AZJ/ABE coverage and scale failures.
- No broad scale inference unless source-bound and already supported.

## Forbidden

- Another random sample, full extraction, broad backfill, source PDF edits,
  prompt/gold-label changes, runtime/model/GPU config changes, service restarts,
  DB/Qdrant/news/memory mutation, or unrelated cleanup.

## Required Validation

- Validate and claim this task card.
- Run focused pytest for any touched extraction behavior.
- Run `py_compile` and `ruff` on touched Python.
- Validate report JSON.
- Run `git diff --check` and `git diff --cached --check`.
- Run task-card `check-diff` and report any pre-existing unrelated dirty-file
  blocker without cleaning it.
- Verify no source PDFs are staged.
- Explicitly report no full extraction/backfill run.
