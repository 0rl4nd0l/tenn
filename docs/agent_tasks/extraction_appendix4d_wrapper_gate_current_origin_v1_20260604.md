---
job_id: extraction_appendix4d_wrapper_gate_current_origin_v1_20260604
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604/appendix4d_gate_simulation.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604/validation.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604/diff-check.json
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Appendix 4D/4E Wrapper Gate Current-Origin Rebuild

## Objective

Rebuild the Appendix 4D/4E wrapper metric-minimum gate from current origin
canonical and use the parked branch only as a reference source for narrow logic.

The useful rule is small: structurally identified Appendix 4D/4E wrapper
documents may pass the metric-minimum gate with two canonical metrics only when
required source-bound period, scale, currency, and disclosure/control evidence
is present.

## Lane

Primary lane: Financial Truth.

Supporting lanes: Evaluation and Provenance.

## Execution Mode

SAFE EXTENSION / REPLAY NARROW HUNKS ONLY.

Risk: MEDIUM/HIGH because this changes the financial extraction gate, but only
inside deterministic Appendix 4D/4E wrapper evidence handling.

## Session Declaration

Agent: Codex.

Worktree:
`/home/l4nd0/tenn-extraction-appendix4d-wrapper-gate-current-origin-v1-20260604`.

Branch:
`safe/extraction-appendix4d-wrapper-gate-current-origin-v1-20260604`.

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
`78b111f423ee86fd1fdfc214f1db551576ee14f5`.

Parked reference: `669d0030` only. Do not merge or rebase
`safe/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602`.

Intended files: this task card, this task's report artifacts, the extraction
contract/evaluation docs, `multipass_extraction.py`, and the focused extraction
tests listed in `allowed_files`.

Decision: proceed only after task-card validation, overlap check, and registry
claim in the clean worktree.

## Contract Check

Target system layer: extraction validation gate.

Relevant contract rules: canonical metrics must remain source-bound financial
facts; wrapper-only disclosures may support control evidence but must not be
silently promoted into canonical metrics; ordinary annual and half-year reports
must keep the normal metric-minimum gate.

What must not change: production extraction/backfill, broad sample/canary
execution, DB/Qdrant/news/memory stores, source PDFs, prompts, gold labels,
runtime configuration, persisted schemas, Cockpit UI, and registry files outside
the claim/release mechanism.

Why safe: the exception is limited to Appendix 4D/4E wrappers with explicit
document-class evidence and deterministic source-bound period, scale, currency,
and disclosure/control evidence. NTA, dividends, record date, and associate/JV
rows remain disclosure-only and do not count as canonical metrics.

GPU process check required: no. This task does not spawn, stop, restart, or
depend on `llama-server`.

## Required Behavior

- Appendix 4D/4E wrapper documents may pass with exactly two canonical metrics
  when required wrapper evidence is present.
- Wrapper evidence must include source-bound period end, period type, scale,
  currency, and required disclosure/control signals.
- NTA, dividends/distributions, record date, and associates/JV rows remain
  disclosure-only and must not become canonical metric counts.
- Ordinary annual and half-year reports keep the normal metric minimum.
- Wrapper documents fail if period, scale, currency, or disclosure/control
  evidence is missing.
- The low-confidence bypass remains deterministic and source-bound only.

## Hard Stops

- Do not merge or rebase the parked branch.
- Do not run broad extraction, backfill, sample, or canary jobs.
- Do not mutate DB, Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change prompts, gold labels, runtime config, persisted schemas, or
  parser routing beyond this validation-gate logic.
- Do not delete Cockpit, registry, or unrelated task-card files.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase.
- Stop if the narrow wrapper logic requires a file outside `allowed_files`.

## Required Tests

- Wrapper passes with two canonical metrics plus required disclosures.
- NTA/dividends/record date do not become canonical metrics.
- Ordinary annual/half-year reports keep the normal gate.
- Wrapper fails if period, scale, currency, or disclosure/control evidence is
  missing.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604.md --repo-root .`
- Focused Appendix 4D gate simulation only.
- Focused pytest for touched extraction tests.
- `python3 -m py_compile` for touched Python files.
- Ruff for touched Python files if available.
- JSON validation for report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_appendix4d_wrapper_gate_current_origin_v1_20260604.md --repo-root .`
- Registry release before final report.
- Final git status.

## Final Report Requirements

Report branch and commit, files changed, validation results, targeted Appendix
4D outcome, whether an integration PR is safe, `DATA_MISSING`, and explicit
confirmation that no broad extraction/backfill/sample/canary ran.
