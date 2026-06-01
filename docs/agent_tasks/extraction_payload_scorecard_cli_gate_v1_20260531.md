---
job_id: extraction_payload_scorecard_cli_gate_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_payload_scorecard_cli_gate_v1_20260531.md
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_actuals_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_payload_gate_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/diff-check.json
  - scripts/extraction_gold_eval_scorecard.py
  - scripts/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/claude/STATE.md
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Payload Scorecard CLI Gate

## Objective

Expose the report-local confirmed-metric payload scorecard and
`pre_persistence_scorecard_gate_v1` through the existing read-only
`scripts/extraction_gold_eval_scorecard.py` helper so operator runs can produce
repeatable payload-and-gate artifacts from an actual extracted-payload JSON map.

This moves the full metric extraction objective forward by making the
pre-persistence gate usable for broader corpus evidence. It does not run
extraction, approve a canary, write canonical rows, or mutate source data.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-payload-scorecard-cli-gate-v1-20260531`.
- Branch: `safe/extraction-payload-scorecard-cli-gate-v1-20260531`.
- Base: `f011e2ce` (`milestone(extraction): harden metric ontology gate`).
- Intended files: this task card, report bundle, scorecard CLI script/test,
  metric extraction contract doc, and `docs/claude/STATE.md`.
- Contested surfaces touched: none from the AGENTS.md contested list.
- Collision risk: MEDIUM because this touches extraction evaluation tooling,
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
- Why safe: this slice only adds a deterministic CLI path around existing
  report-local scorecard/gate builders and tests it with synthetic actuals.
  The emitted gate must continue to report `canonical_write_allowed: false`
  and `broad_backfill_authorized: false`.
- GPU process check required: no. This task does not start or use llama-server.

## Required Implementation

- Add a CLI mode for confirmed metric payload scoring using an
  `--actuals-json` map keyed by document id or fixture id.
- Emit the pre-persistence gate beside the payload scorecard when requested,
  without requiring runtime services.
- Keep existing `canonical_core`, `expanded_required`, and
  `confirmed_metric_coverage` outputs backward-compatible.
- Add focused tests proving:
  - actuals are required for payload scoring
  - the emitted gate fails on blocking payload score classes
  - existing coverage profile behavior stays dry-run inventory

## Forbidden

- Runtime backend startup, route submission, canary execution, broad backfill,
  direct SQL, source-PDF mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, and GitHub mutation.

## Required Validation

- Task card validation and registry claim.
- Focused script unit tests.
- Focused scorecard service tests if touched indirectly.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- Sample CLI run producing a JSON artifact under this job report directory.
- JSON validation for generated report artifacts.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --cached --check`.
