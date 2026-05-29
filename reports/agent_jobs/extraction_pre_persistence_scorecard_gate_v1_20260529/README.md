# Extraction Pre-Persistence Scorecard Gate V1

## Scope

SAFE EXTENSION in the Evaluation lane. This job adds a deterministic
`pre_persistence_scorecard_gate_v1` wrapper around the existing report-local
confirmed metric payload scorecard.

## Implemented

- Added `build_pre_persistence_scorecard_gate()` in
  `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`.
- Gate passes only when actual payloads were supplied and result classes are
  limited to:
  - `present_correct`
  - `unsupported_correctly_abstained`
- Gate fails on:
  - `missing_expected_metric`
  - `present_wrong_value`
  - `wrong_unit_currency_scale`
  - `wrong_period`
  - `missing_evidence`
  - `ambiguous_quarantined`
  - `not_evaluated_no_actual_payload`
- Gate output always reports:
  - `canonical_write_allowed: false`
  - `broad_backfill_authorized: false`
  - `operator_approval_required_for_canary: true`

## Boundaries

- No third canary batch was run.
- No broad backfill was run.
- No production DB or direct SQL mutation was performed.
- No Qdrant, news, memory, source-PDF, parser-routing, prompt, runtime, model,
  GPU, service, schema, or Cockpit UI changes were made.
- Source-PDF openability remains separate from extraction correctness.

## Validation

Completed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q` (`29 passed`)
- `financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_eval_harness.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -q -k 'not test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist'` (`72 passed, 1 deselected`)
- `jq empty reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/status.json reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/pre_persistence_scorecard_gate_sample.json reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/diff-check.json`
- `git diff --check`
- source-PDF/new binary staging check (`no output`)
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pre_persistence_scorecard_gate_v1_20260529.md`
- Post-change code review pass: no critical findings, warnings, or suggestions.

Known unrelated validation gap:

- The full adjacent suite without deselection still fails
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
  because a 10X source PDF is not present at the repo-relative
  `financial-engine_v2/data/asx/docs/...` path. This was not fixed here because
  source-PDF editing/copying/committing is outside the task boundary.

## Remaining Blockers

- Third canary approval remains required before any additional canary run.
- Broad extraction accuracy is still not graduated.
- Non-AUD/Rp trillion policy and global `ok_low_confidence` surfacing remain
  outside this slice.
