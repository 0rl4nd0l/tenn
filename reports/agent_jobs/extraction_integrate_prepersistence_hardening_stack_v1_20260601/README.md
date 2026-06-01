# Extraction Integrate Prepersistence Hardening Stack V1

Generated: 2026-06-01

## Decision

Integrated `safe/extraction-payload-actuals-coverage-gate-v1-20260531` stack
onto `migration/clean-runtime-baseline-reconstruct-v1` with a clean
`git merge --no-ff --no-commit` pre-commit stage.

The integration is needed before runtime canary execution because the baseline
branch only had the query-orchestration preservation commit and did not yet
contain the latest extraction hardening commits.

## Source Stack

- `f011e2ce` `milestone(extraction): harden metric ontology gate`
- `cf44ca54` `milestone(extraction): expose payload scorecard gate CLI`
- `2eca7194` `milestone(extraction): summarize payload gate blockers`
- `b3c6ae08` `milestone(extraction): gate storage metric contract`
- `20444bd9` `milestone(extraction): block unmatched payload actuals`

## Current Scope

This task performed code/report integration only.

It did not:

- run the third canary
- call `POST /api/process/document/{document_id}`
- start or reload backend, worker, or GPU worker
- perform direct SQL, broad backfill, Qdrant/news/memory writes, source PDF
  mutation, schema changes, prompt/parser changes, or GitHub mutation

## Validation

Passed:

- `git merge-tree ... | rg '<<<<<<<|changed in both|CONFLICT|Auto-merging' || true`
- `git diff --check HEAD...safe/extraction-payload-actuals-coverage-gate-v1-20260531`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --repo-root .`
- `financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/app/services/pipeline.py scripts/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q` (`32 passed`)
- `financial-engine_v2/.venv/bin/python -m pytest scripts/test_extraction_gold_eval_scorecard.py -q` (`5 passed`)
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_pipeline_stages.py -q` (`26 passed`)
- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/app/services/pipeline.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_pipeline_stages.py scripts/extraction_gold_eval_scorecard.py scripts/test_extraction_gold_eval_scorecard.py`

## Next Safe Step

Create or validate `extraction_third_canary_runtime_execution_v1_20260531`,
claim it, prove backend/queue/GPU/loaded-code/source-path state, and only then
run the bounded seven-document canary one document at a time.
