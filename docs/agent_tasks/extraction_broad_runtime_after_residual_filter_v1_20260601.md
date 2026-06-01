---
job_id: extraction_broad_runtime_after_residual_filter_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_runtime_after_residual_filter_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/runtime-control.json
  - reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601/broad_test_20260601T140000Z.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_runtime_after_residual_filter_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User approved launch and full necessary runtime for the continuing extraction hardening goal on 2026-06-01.
---

# Extraction Broad Runtime After Residual Filter V1

## Objective

Run one fresh bounded broad extraction robustness sample after commit
`63e844b1` to measure whether the residual non-candidate filter changes the
failure distribution.

This is a runtime evaluation sample, not canonical datastore repair, broad
backfill, real-gold accuracy proof, GitHub mutation, or full ticker-universe
extraction graduation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Evaluation

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `docs/claude/STATE.md`, and this report
bundle only.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM by shared GPU/runtime usage; resolved by active-job
check, no overlapping allowed files with the active Reporting task, explicit
GPU-exclusive activity token, bounded sample size, and post-run cleanup.

Decision: proceed after task-card validation, registry/overlap checks, runtime
preflight, llama.cpp launch/load gates, and report-only output setup.

## Contract Check

Target system layers: Evaluation runtime and Extraction execution path.

Relevant contract rules: backend remains the sole authority for canonical
stores; this task uses the existing broad robustness script as report-only
evaluation; LLM outputs are diagnostic evidence only; source PDFs and data
stores remain read-only.

What must not change: extraction code, prompts, schema, database rows, Qdrant,
news/memory stores, source PDFs, Cockpit UI, GitHub state, and backend/worker
routes. The broad script may write only the allowlisted report JSON.

Why safe: the run uses `/data/asx/docs` read-only, count `8`, seed `20260601`,
and the existing llama.cpp extraction path. The output is an ignored report
artifact committed only for auditability.

GPU process check required: yes. Start a GPU-exclusive token before launcher
startup, launch only the canonical router on `:8001`, verify health/models, run
the sample, then stop runtime and clear the token.

## Validation

- Validate this task card.
- List active jobs and check overlap before claim.
- Claim this task in the shared registry.
- Verify worktree starts clean.
- Verify no conflicting GPU-exclusive token before taking ownership.
- Verify GPU/process topology before runtime launch.
- Launch llama.cpp router only if needed.
- Verify `/health` or `/v1/models` before extraction.
- Run `broad_extraction_test.py --count 8 --seed 20260601 --docs-root /data/asx/docs --resume` with output dir under this report bundle.
- Record runtime command, result summary, output file, cleanup, and final GPU/process state in `validation.json`.
- Update `docs/claude/STATE.md` with bounded runtime sample result and limits.
- `check-diff` for this task card.
- `git diff --check` and `git diff --cached --check`.
- Commit with milestone message.
- Release registry claim and amend released status.
