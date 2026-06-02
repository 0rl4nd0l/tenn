---
job_id: extraction_residual_failure_gate_audit_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_failure_gate_audit_v1_20260602.md
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/case_audit.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/side_effect_audit.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested audit and narrow hardening of remaining broad-sample failure classes on 2026-06-02.
---

# Extraction Residual Failure Gate Audit V1

## Objective

Audit the five remaining failed/degraded documents from the bounded broad sample
after residual candidate filtering and decide, per case, whether the correct
action is candidate exclusion, source-type classification fix, scale/period
guard, confidence gate, report-only diagnostic, or no change.

Safe extension is allowed only for narrow, deterministic, source-bound gates
that are directly testable without running another random sample.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Financial Truth.
- Execution mode: AUDIT FIRST; SAFE EXTENSION only for narrow validated gates.
- Intended files: this task card, this report bundle, and at most the
  allowlisted extraction classifier plus focused tests.
- Contested surfaces touched: none from AGENTS.md.
- Collision risk: MEDIUM/HIGH because extraction truth gates are sensitive;
  proceed only if registry overlap remains non-conflicting.

## Contract Check

- Target system layers: Extraction and Metric Extraction, with Evaluation
  report artifacts.
- Relevant contract rules: source PDFs are read-only; extraction must extract
  explicit source values only; invalid or ambiguous documents must fail closed;
  report artifacts do not promote canonical truth.
- What must not change: source PDFs, prompts, gold labels, canonical truth
  promotion state, database rows, Qdrant, news, memory, workers, runtime model
  or GPU config, service state, unrelated dirty files, and any random
  sample/backfill/canary execution.
- Why safe: the work begins as read-only case classification and only applies a
  deterministic classifier guard when source-title evidence proves a
  non-candidate class.
- GPU process check required: no. This task must not start llama-server or run
  another sample.

## Cases

- CQT webinar postponement: `classifier_low_confidence`.
- AUK preliminary final report: `scale_validation:suspect_overscaled`.
- NCK results teleconference: `scale_unknown`.
- CQT quarterly activities report: `operational_update_without_formal_statements`.
- RMS H1 FY results announcement and facility update: `ok_low_confidence`.

## Required Validation

- Validate and claim this task card.
- Do not run full ticker extraction, broad backfill, another random sample, or
  service restarts.
- Run focused pytest for touched extraction classifier behavior.
- Run `py_compile` and `ruff` on touched Python.
- Validate report JSON.
- Run `git diff --check` and `git diff --cached --check`.
- Run task-card `check-diff` and report any pre-existing unrelated dirty-file
  blocker without cleaning it.
- Verify no source PDFs are staged.
