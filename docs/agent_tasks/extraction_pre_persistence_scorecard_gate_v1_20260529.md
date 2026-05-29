---
job_id: extraction_pre_persistence_scorecard_gate_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md
  - reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/README.md
  - reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/status.json
  - reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/pre_persistence_scorecard_gate_sample.json
  - reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/diff-check.json
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 97
---

# Extraction Pre-Persistence Scorecard Gate V1

## Objective

Complete the next bounded metric-extraction hardening slice before any third
#96 canary batch by turning the existing report-local payload scorecard into a
deterministic pre-persistence gate artifact.

The gate must make bad actual payloads explicitly blocking before canary
promotion or any canonical write decision, while preserving the scorecard's
report-local, no-extraction, no-datastore-write boundary.

## Lane

Primary lane: Evaluation.

Supporting lanes: Financial Truth and Provenance.

## Execution Mode

SAFE EXTENSION, report-local/eval-only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Issue: #97

Intended files: this task card, a narrow scorecard gate helper in
`extraction_gold_eval_scorecard.py`, focused synthetic tests, extraction policy
docs, and this task's report artifacts.

Contested surfaces touched: none.

Collision risk: LOW after registry overlap check and claim.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation/reporting around extracted-payload measurement.
It does not alter ingestion, extraction, storage, retrieval, analysis, or client
runtime behavior.

Relevant contract rules: backend extraction truth remains source-bound and
explicit; ambiguous, unsupported, missing-evidence, wrong-period, wrong-scale,
and wrong-value outputs must fail or quarantine instead of being promoted; no
parallel production pipeline, parser route, prompt path, canonical write, or
datastore mutation is introduced.

What must not change: production extraction/backfill, production DB writes,
Qdrant/news/memory mutation, canonical financial truth writes, parser routing,
extraction prompts, gold labels, source PDFs, runtime/model/GPU/service config,
and Cockpit UI.

Why safe: the implementation consumes an already-built report-local scorecard
or pre-supplied actual payload map only, returns JSON-serializable gate
diagnostics, and never invokes production extraction or persistence.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run broad backfill.
- Do not perform production DB writes.
- Do not perform direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing.
- Do not change extraction prompts.
- Do not mutate gold labels.
- Do not change runtime, model, or GPU config.
- Do not restart services.
- Do not implement Cockpit UI.
- Do not add schema migrations.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase
  operations.

## Required Behavior

- Add a deterministic gate artifact for confirmed metric payload scorecards.
- Gate passes only when actual payloads were supplied and every scoreable metric
  is either `present_correct` or a policy-allowed noncanonical abstention.
- Gate fails on wrong value, wrong period, wrong unit/currency/scale, missing
  expected metric, missing evidence, ambiguous/quarantined, or no actual
  payload.
- Gate output must state `canonical_write_allowed: false` and
  `broad_backfill_authorized: false` because this is an evaluation-readiness
  artifact, not a runtime write authorization.
- Preserve source-PDF openability as separate from extraction correctness.
- Preserve the current payload scorecard result classes and avoid weakening
  existing scorecard behavior.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Focused pytest for `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Ruff for touched Python files
- JSON validation for generated artifacts
- `git diff --check`
- Source PDF/new binary staging check
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release <job_id>`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed,
tests run with exact results, generated artifacts, how the gate blocks bad
payloads, confirmation that no third canary/backfill/datastore mutation ran,
remaining blockers before full accurate extraction graduation, and final git
status.
