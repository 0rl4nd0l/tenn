---
job_id: extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602.md
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/README.md
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/status.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/validation.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/preflight.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_readiness.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_startup.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/runtime_shutdown.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/broad_sample_stdout.txt
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/bounded_broad_sample_results.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/broad_sample_summary.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/failure_taxonomy.json
  - reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602/side_effect_audit.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User requested this bounded validation rerun on 2026-06-02 after residual filtering and Redis score queue cleanup.
---

# Extraction Residual Candidate Filtering Bounded Sample Rerun V1

## Objective

Rerun exactly one bounded broad extraction sample after residual candidate
filtering commit `2465754a2cf8` and Redis score queue cleanup.

The sample must use the same bounded size and seed as the previous broad sample:
count `8`, seed `20260601`, docs root `/data/asx/docs`.

This is a report-only validation run. It is not full ticker-universe extraction,
broad backfill, real-gold promotion, canonical truth promotion, or parser prompt
change work.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Lane: Evaluation.
- Execution mode: BOUNDED VALIDATION ONLY.
- Intended files: this task card and the report bundle listed in
  `allowed_files`.
- Contested surfaces touched: none by file edit.
- Collision risk: MEDIUM/HIGH by bounded extraction runtime and shared GPU
  usage; resolved only by registry, Redis, process, backend-health, source-path,
  and GPU readiness gates before the sample.
- Decision: proceed only if runtime readiness is clean; otherwise stop before
  the sample and write a blocked report.

## Contract Check

- Target system layers: Evaluation tooling around the Extraction layer.
- Relevant contract rules: backend remains the authority for canonical data;
  extraction must not infer, substitute, fabricate, or promote truth; source
  PDFs are read-only; GPU runtime must use the approved local ports and no rogue
  llama-server processes.
- What must not change: source PDFs, database rows, Qdrant, news, memory,
  extraction prompts, gold labels, canonical truth promotion state, runtime
  model/GPU configuration, backend routes, worker routes, Cockpit UI, or
  unrelated repo files.
- Why safe: the existing broad extraction helper is used for one deterministic,
  bounded sample and writes only report artifacts. Runtime startup is limited to
  the minimal backend/router readiness needed by the existing path.
- GPU process check required: yes. Run `scripts/gpu_process_guard.sh --check`
  before starting or using llama-server.

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
- Run only:
  `financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/broad_extraction_test.py --count 8 --seed 20260601 --docs-root /data/asx/docs`
- Capture stdout, full output JSON, sample inputs/outputs, summary, and failure
  taxonomy in the report bundle.
- Compare the result against the previous baseline `ok=3 failed=5`.
- Do not run full extraction, broad backfill, or any extra canary/sample.

## Required Validation

- JSON validation for report artifacts.
- `git diff --check` and `git diff --cached --check`.
- Task-card `check-diff`, with any pre-existing unrelated dirt explicitly
  reported instead of cleaned.
- Verify no source PDFs are staged.
- Verify queues and unacked keys after the run.
- Release the registry claim and record final `list-active`.
- Final git status.
