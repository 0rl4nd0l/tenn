---
job_id: extraction_metric_ontology_gate_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/metric_ontology_bridge.py
  - financial-engine_v2/backend/tests/test_metric_ontology_bridge.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Metric Ontology Gate

## Objective

Implement the next non-runtime metric ontology hardening slice from
`/tmp/tenn_metric_extraction_handoff_2026-05-31.md`: make persisted-only,
internal-only, unsupported, planned, and ambiguous metric families unable to
count as successful pre-persistence payload facts unless policy explicitly
allows them.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-metric-ontology-gate-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- Intended files: this task card, eval-only scorecard/ontology helpers, focused
  backend tests, report artifacts under this output directory, and
  `docs/claude/STATE.md`.
- Contested surfaces touched: none.
- Collision risk: LOW; isolated worktree, no active overlapping registry job,
  no runtime/service/data-store mutation.
- Decision: proceed after task-card validation, registry check, overlap check,
  and claim.

## Contract Check

- Target system layer: Evaluation tooling around Metric Extraction.
- Relevant contract rules: backend remains authoritative for canonical
  financial truth; extraction may only extract explicit values; unsupported or
  ambiguous metrics must not be inferred, substituted, or silently promoted;
  fail-fast boundaries must remain visible.
- What must not change: live extraction prompts, parser routing, runtime
  services, model/GPU config, source PDFs, DB schema, persisted financial rows,
  Qdrant/news/memory stores, Cockpit UI, GitHub PR state, and canonical write
  permission.
- Why safe: the change is confined to eval-only ontology projection and tests.
  It adds no runtime execution path and keeps pre-persistence scorecard gates
  report-local with `canonical_write_allowed=false`.
- GPU process check required: no; this task does not start or depend on
  llama-server.

## Required Behavior

- Keep `interest_expense` visible as a known non-target metric family without
  making it extractor-target or auto-collapse safe.
- Keep ambiguous `finance_costs` labels out of canonical success.
- Prove `total_equity`, `interest_expense`, `finance_costs`, `total_assets`,
  planned metrics (`eps`, `dividends`), and internal-only aliases
  (`debt_borrowings`) cannot pass as successful pre-persistence payload facts.
- Block unexpected actual-payload metrics that are outside the fixture
  expectation set instead of silently ignoring them.
- Preserve the current supported canonical metric set.
- Preserve `canonical_write_allowed=false` and `broad_backfill_authorized=false`
  in gate artifacts.

## Forbidden

- Starting/stopping backend, workers, llama.cpp, Docker, or GPU services.
- Running canary, runtime extraction, backfill, queue submission, or document
  processing.
- DB/Qdrant/source-PDF/memory/canonical-truth mutation.
- Parser, prompt, schema, model/GPU config, frontend, or GitHub mutation.
- Treating evaluation tests as full extraction graduation evidence.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/app/services/metric_ontology_bridge.py financial-engine_v2/backend/tests/test_metric_ontology_bridge.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Focused pytest for the touched backend tests.
- Targeted Ruff for touched files.
- JSON validation for report artifacts.
- Raw PDF/database/archive staging scan.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md --repo-root .`
- Registry release and final list-active.
- Final `git status --short --untracked-files=all`.

## Final Report Requirements

- Branch, HEAD, worktree, and task card path.
- Files changed.
- Summary of ontology/gate behavior proven.
- Validation commands and results.
- Remaining blockers for third canary and full extraction graduation.
