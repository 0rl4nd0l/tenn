---
job_id: extraction_payload_gate_blocking_summary_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_payload_gate_blocking_summary_v1_20260531.md
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/gate_actionability_sample.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/diff-check.json
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/claude/STATE.md
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Payload Gate Blocking Summary

## Objective

Make `pre_persistence_scorecard_gate_v1` actionable for broader confirmed
metric payload reviews by adding deterministic document-level blocking summaries
and a complete missing-actuals document list.

The existing gate already fails closed, but broad corpus execution needs a
complete list of documents that still need actual payloads or have blocking
metric classes. This slice improves the evaluation artifact only.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-payload-gate-blocking-summary-v1-20260531`.
- Branch: `safe/extraction-payload-gate-blocking-summary-v1-20260531`.
- Base: `cf44ca54` (`milestone(extraction): expose payload scorecard gate CLI`).
- Intended files: this task card, report bundle, scorecard service/tests,
  metric extraction contract doc, and `docs/claude/STATE.md`.
- Contested surfaces touched: none from the AGENTS.md contested list.
- Collision risk: MEDIUM because this touches extraction evaluation artifacts,
  but no runtime, storage, parser, prompt, source-PDF, or UI surface.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target layer: Evaluation around Extraction truth gates.
- Relevant rules: backend remains the authority; metric extraction must not
  infer, substitute, or silently promote unsupported facts; evaluation helpers
  must not become a parallel source of truth.
- What must not change: parser prompts, extraction runtime, DB schema,
  canonical financial rows, Qdrant/embeddings, source PDFs, Cockpit UI,
  GitHub state, runtime service state, and canary execution state.
- Why safe: this slice only enriches a report-local gate artifact with
  blocking summaries derived from existing metric rows. It does not alter pass
  criteria or authorize canonical writes.
- GPU process check required: no. This task does not start or use llama-server.

## Required Implementation

- Add deterministic document-level blocking summaries to
  `build_pre_persistence_scorecard_gate()`.
- Include a complete list/count of documents blocked only because actual
  payloads are missing.
- Preserve existing gate status, blocker counts, and `blocking_examples`
  behavior for compatibility.
- Add focused tests proving broad missing-actuals and mixed blocker summaries
  are complete and stable.

## Forbidden

- Runtime backend startup, route submission, canary execution, broad backfill,
  direct SQL, source-PDF mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, and GitHub mutation.

## Required Validation

- Task card validation and registry claim.
- Focused scorecard service pytest.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- Sample gate artifact under this report directory.
- JSON validation for generated report artifacts.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --cached --check`.
