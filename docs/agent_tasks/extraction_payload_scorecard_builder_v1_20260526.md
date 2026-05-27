---
job_id: extraction_payload_scorecard_builder_v1_20260526
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/README.md
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/status.json
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/payload_scorecard_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/diff-check.json
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Extraction Payload Scorecard Builder

## Scope

Implement the first #97 safe-extension step: a report-local confirmed metric coverage scorecard builder that compares confirmed expectations with pre-supplied actual extracted payloads.

## Lane

Primary lane: Evaluation.

Supporting lanes: Financial Truth, Provenance.

## Execution Mode

SAFE EXTENSION, report-local/eval-only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-payload-scorecard-builder-v1-20260526`

Branch: `safe/extraction-payload-scorecard-builder-v1-20260526`

Issue: #97

Intended files: this task card, a narrow scorecard helper in `extraction_gold_eval_scorecard.py`, focused synthetic unit tests, and this task's report artifacts.

Contested surfaces touched: none.

Collision risk: LOW after isolated worktree creation and registry overlap check.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation/reporting around extracted-payload measurement. It does not alter ingestion, extraction, storage, retrieval, analysis, or client runtime behavior.

Relevant contract rules: backend remains source of truth; metric extraction must not infer, substitute, or fabricate; no duplicate production pipeline, parser route, prompt path, canonical write, or datastore mutation is introduced.

What must not change: production extraction/backfill, production DB writes, Qdrant/news/memory mutation, canonical financial truth writes, parser routing, extraction prompts, gold labels, source PDFs, runtime/model/GPU/service config, and Cockpit UI.

Why safe: the implementation consumes synthetic fixture labels and pre-supplied actual payload maps only, returns report-local JSON-serializable artifacts, and never invokes production extraction or persistence.

GPU process check required: no. This task does not spawn, restart, stop, or depend on `llama-server`.

## Hard Stops

- Stop if implementation requires production extraction or backfill.
- Stop if implementation requires production DB, Qdrant, news, memory, or canonical financial truth writes.
- Stop if implementation requires parser routing, extraction prompt, gold-label, source-PDF, runtime/model/GPU/service config, or Cockpit UI changes.
- Stop if active registry jobs overlap the allowed files.
- Stop if generated diffs escape this allowlist.

## Required Behavior

- Accept confirmed metric expectations.
- Accept actual extracted payloads from fixture/report-local JSON structures.
- Compare expected vs actual by document and metric.
- Preserve source-PDF openability as separate from extraction correctness.
- Emit result classes for present/correct, missing expected metric, present wrong value, wrong unit/currency/scale, wrong period, missing evidence, unsupported correctly abstained, ambiguous/quarantined, and not evaluated when no actual payload exists.
- Keep `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` conceptually separate.
- State that the narrow core is a no-regression baseline, not the final broad-metric product goal.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- Focused pytest for `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- JSON validation for generated artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md`

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed, tests run with exact results, generated artifacts, Confirmed/Inferred/Speculative/DATA_MISSING, how #97 is advanced, remaining blockers, whether #98 or #99 must happen before broader use, final git status, and Project Memory save recommendation.
