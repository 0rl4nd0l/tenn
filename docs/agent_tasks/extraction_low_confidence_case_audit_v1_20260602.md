---
job_id: extraction_low_confidence_case_audit_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_low_confidence_case_audit_v1_20260602.md
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/README.md
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/status.json
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/validation.json
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/case_audit.json
  - reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602/side_effect_audit.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/preflight.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/runtime_readiness.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/runtime_startup.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/runtime_shutdown.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/broad_sample_summary.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/bounded_broad_sample_results.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/side_effect_audit.json
  - reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/broad_sample_stdout.txt
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/app/services/method_isolated_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - docs/extraction/metric_extraction_contract.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_low_confidence_case_audit_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested audit of the two ok_low_confidence cases from the latest bounded broad extraction sample on 2026-06-02.
---

# Extraction Low Confidence Case Audit V1

## Objective

Audit the two `ok_low_confidence` cases from bounded broad sample commit
`758a2861` before increasing sample size or running broader extraction:

- NSM half-year report.
- WBC 1Q24 update.

For each case, identify the exact low-confidence reason, inspect extracted
metrics/evidence/status, and decide whether the low-confidence status is
acceptable, should abstain, should be filtered, or needs a narrow
source-bound/tested parser or evidence fix.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Financial Truth.
- Execution mode: AUDIT ONLY first; SAFE EXTENSION only for a narrow,
  source-bound, focused-test-covered fix.
- Intended files: this task card and this report bundle first; allowlisted
  extraction/test/contract files only if the case evidence proves a narrow fix.
- Contested surfaces touched: none from AGENTS.md are planned.
- Collision risk: MEDIUM/HIGH because financial-truth extraction behavior is
  sensitive; stop if active registry overlap or same-file edits appear.

## Contract Check

- Target system layers: Extraction, Metric Extraction, and Evaluation report
  artifacts.
- Relevant contract rules: source PDFs are read-only; extraction must extract
  only explicit source values; ambiguous or unsupported metrics must fail
  closed; no hidden fallback, substitution, inference, or parallel system is
  allowed.
- What must not change: source PDFs, prompts, gold labels, database rows,
  Qdrant, news, memory, runtime model/GPU config, service state, broad sample
  size, full extraction/backfill, or unrelated dirty files.
- Why safe: the work reads the latest bounded sample artifacts and source-bound
  extraction evidence, then emits audit artifacts. Any safe extension must be
  deterministic, narrow, source-bound, and covered by focused tests.
- GPU process check required: no. This task must not start llama-server, run
  another sample, or restart services.

## Source Sample

Use the committed bounded sample bundle:

- `reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/bounded_broad_sample_results.json`
- `reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/broad_sample_summary.json`
- `reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602/failure_taxonomy.json`

The committed result was `ok=6`, `ok_low_confidence=2`, `failed=0`. Do not run
another sample.

## Required Execution

- Validate and claim this task card before implementation-capable work.
- Preserve the unrelated dirty file
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.
- Inspect sample outputs and source-bound evidence for NSM and WBC only.
- Decide whether each low-confidence result is correct acceptance, abstention,
  filtering, or narrow fix.
- Do not run full ticker extraction, broad backfill, another random sample,
  service restart, DB/Qdrant/news/memory mutation, source PDF edit, prompt
  change, gold-label change, runtime/model/GPU change, or unrelated cleanup.

## Required Validation

- Focused pytest only if code/tests are touched.
- `py_compile` and `ruff` only if Python is touched.
- JSON validation for report artifacts.
- `git diff --check` and `git diff --cached --check`.
- Task-card `check-diff`, with pre-existing unrelated dirt reported instead of
  cleaned.
- Verify no source PDFs are staged.
- Release the registry claim and record final `list-active`.
- Explicitly report no full extraction/backfill run.
