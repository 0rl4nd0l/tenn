---
job_id: extraction_residual_failure_class_bounded_sample_rerun_v1_20260602
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602.md
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
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested one bounded same-size broad extraction validation sample on 2026-06-02 after residual failure-class hardening commit 902d03b4aa43.
---

# Extraction Residual Failure Class Bounded Sample Rerun V1

## Objective

Run exactly one bounded broad extraction validation sample of the same size and
seed class as the previous sample after residual failure-class hardening commit
`902d03b4aa43`.

This is bounded validation only. It is not full ticker-universe extraction,
broad backfill, canary graduation, real-gold promotion, canonical truth
promotion, parser prompt/gold-label change work, or source-PDF mutation.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Evaluation.
- Execution mode: BOUNDED VALIDATION ONLY.
- Intended files: this task card and this report bundle only.
- Contested surfaces touched: none from AGENTS.md.
- Collision risk: MEDIUM/HIGH due bounded extraction runtime and shared GPU
  use; proceed only when registry, Redis, backend-health, source-path, and GPU
  gates are clean.

## Contract Check

- Target system layers: Evaluation tooling around the Extraction runtime path.
- Relevant contract rules: backend remains the authority for canonical data;
  extraction must be source-bound and fail closed; no hidden fallback,
  inference, substitution, prompt change, parser change, source mutation, or
  canonical truth promotion is allowed.
- What must not change: source PDFs, database rows, Qdrant, news, memory,
  extraction prompts, gold labels, runtime model/GPU config beyond minimal
  readiness/startup, backend routes, worker routes, Cockpit UI, or unrelated
  dirty files.
- Why safe: the run uses the existing broad extraction helper for one
  deterministic count-8 sample with seed `20260601`, writes report artifacts,
  and does not enqueue worker jobs or run a full universe/backfill path.
- GPU process check required: yes. Run `scripts/gpu_process_guard.sh --check`
  before starting or using llama-server.

## Baseline

Previous bounded result before residual failure-class hardening:

- `ok=4`
- `ok_low_confidence=0`
- `failed=4`

## Required Preflight

- Confirm repo path, branch, HEAD, remote, git status, worktree list, and active
  registry jobs.
- Preserve the unrelated dirty file
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.
- Confirm Redis queue lengths are zero for `score`, `ingest`, `embed`,
  `llm_gpu`, and `llm_cpu`.
- Confirm no Redis unacked keys.
- Confirm `/api/health`, loaded commit if API-visible, `/data/asx/docs` source
  path availability, GPU state, and no conflicting jobs or broad runtime
  processes.
- Stop before the sample if runtime readiness is not clean.

## Required Execution

- Validate and claim this task card.
- Run exactly one bounded sample using count `8`, seed `20260601`, docs root
  `/data/asx/docs`, and local llama.cpp on canonical router port `8001`.
- Capture stdout, full output JSON, sample inputs/outputs, summary, and failure
  taxonomy in this report bundle.
- Compare against the previous baseline `ok=4`, `ok_low_confidence=0`,
  `failed=4`.
- Do not run full extraction, broad backfill, canary, or any extra random
  sample.

## Required Validation

- JSON validation for report artifacts.
- `git diff --check` and `git diff --cached --check`.
- Task-card `check-diff`, with pre-existing unrelated dirt reported instead of
  cleaned.
- Verify no source PDFs are staged.
- Verify queues and unacked keys after the run.
- Release the registry claim and record final `list-active`.
- Final git status.
- Explicitly report no full extraction/backfill run.
