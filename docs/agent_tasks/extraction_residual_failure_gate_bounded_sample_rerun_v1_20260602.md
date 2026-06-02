---
job_id: extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602.md
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/preflight.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/runtime_readiness.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/runtime_startup.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/runtime_shutdown.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/broad_sample_summary.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/bounded_broad_sample_results.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/side_effect_audit.json
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/broad_sample_stdout.txt
  - reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602/broad_test_20260602T062634Z.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/case_audit.json
  - reports/agent_jobs/extraction_residual_failure_gate_audit_v1_20260602/side_effect_audit.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/preflight.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_readiness.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_startup.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_shutdown.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/broad_sample_summary.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/bounded_broad_sample_results.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/side_effect_audit.json
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested one bounded same-size broad extraction validation sample on 2026-06-02.
---

# Extraction Residual Failure Gate Bounded Sample Rerun V1

## Objective

Run exactly one bounded broad extraction validation sample of the same size and
seed class as the previous bounded sample after residual failure-gate hardening.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Evaluation.
- Execution mode: BOUNDED VALIDATION ONLY.
- Intended files: this task card and this report bundle. Source/test/script
  files are allowlisted only for read-only validation unless a narrow bug blocks
  the bounded run.
- Contested surfaces touched: none from AGENTS.md.
- Collision risk: MEDIUM/HIGH due runtime validation and extraction path use;
  proceed only when registry and runtime readiness are clean.

## Contract Check

- Target system layers: Evaluation and bounded Extraction runtime path.
- Relevant contract rules: backend remains the authority; extraction must remain
  source-bound and fail closed; evaluation artifacts do not authorize canonical
  writes or broad backfill.
- What must not change: source PDFs, prompts, gold labels, canonical truth,
  database rows outside the approved bounded route behavior, Qdrant, news,
  memory, unrelated dirty files, and runtime/model/GPU config beyond minimal
  readiness/startup.
- Why safe: the run is bounded to count 8 and seed 20260601, records artifacts,
  and does not run full ticker-universe extraction or broad backfill.
- GPU process check required: yes, because the sample depends on llama.cpp.

## Baseline

Previous bounded sample after filtering:

- `ok=3`
- `ok_low_confidence=1`
- `failed=4`

## Required Validation

- Validate and claim this task card.
- Confirm repo path, branch, HEAD, remote, git status, worktrees, and registry.
- Preserve unrelated dirty file
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.
- Verify Redis queues are zero and no unacked keys exist.
- Verify `/api/health`, loaded commit if available, source paths, GPU state, and
  no conflicting jobs before running the sample.
- Run exactly one bounded sample using count 8 and seed 20260601.
- Record sample inputs/outputs and compare to baseline.
- Classify failures and low-confidence cases.
- Confirm no source PDFs staged.
- Validate JSON, run `git diff --check`, release registry, final list-active,
  and final git status.
- Explicitly report no full extraction/backfill run.
