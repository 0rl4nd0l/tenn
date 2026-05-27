# Extraction Contract Parity Guard

Job: `extraction_contract_parity_guard_v1_20260526`
Issue focus: #98
Mode: SAFE EXTENSION, report-local/test-only

## Session

- Worktree: `/home/l4nd0/tenn-extraction-contract-parity-guard-v1-20260526`
- Branch: `safe/extraction-contract-parity-guard-v1-20260526`
- HEAD at report write: `3725591cf76ec1a56428a476e23dbd1ebc4050fc`
- Task card: `docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md`
- Registry: shared registry validated; `list-active --read-only` returned no active jobs before claim; overlap check passed; claim succeeded; release succeeded after validation.
- Collision handling: isolated worktree was created from the baseline checkout so unrelated untracked task-card dirt in `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` stayed out of this job.

## What Changed

- Added `build_metric_contract_parity_matrix()` in `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`.
- Added `MetricContractStatus` classes: `supported`, `extractor_supported`, `evaluator_supported`, `persisted_only`, `gold_only`, `planned`, `internal_only`, `unsupported`, and `ambiguous_requires_policy`.
- Added focused synthetic tests in `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`.
- Generated `metric_contract_parity_matrix.json` under this report directory.

## Boundary

The guard is diagnostic only. It does not run extraction, mutate labels, write canonical financial truth, write DB/Qdrant/news/memory, move source PDFs, change parser routing, change prompts, change persisted schema, or touch runtime/model/GPU/service config.

## Matrix Summary

`metric_contract_parity_matrix.json` emitted:

```json
{
  "artifact_type": "metric_contract_parity_matrix_v1",
  "metric_family_count": 17,
  "status_counts": {
    "ambiguous_requires_policy": 1,
    "evaluator_supported": 0,
    "extractor_supported": 0,
    "gold_only": 0,
    "internal_only": 1,
    "persisted_only": 2,
    "planned": 2,
    "supported": 10,
    "unsupported": 1
  },
  "policy_assertions": {
    "broad_catalogue_not_automatically_canonical": true,
    "interest_expense_not_promoted": true,
    "total_equity_not_promoted": true
  }
}
```

Required families are explicitly classified:

- `supported`: `revenue`, `operating_cash_flow` -> `operating_cf`, `net_debt`, `cash` -> `cash_end`, `capex`, `np_attributable`.
- `persisted_only`: `total_equity`, `interest_expense`.
- `ambiguous_requires_policy`: `finance_costs`.
- `internal_only`: `debt_borrowings` -> internal `total_debt`.
- `planned`: `eps`, `dividends`.
- `unsupported`: `total_assets`.

## Confirmed

- #98 is valid and now has an executable report-local guard instead of an audit-only statement.
- `total_equity` and `interest_expense` are not silently promoted: both are persisted fields, but they are not final extractor output fields and are not evaluator-supported.
- `total_debt`/borrowings is internal-only: it can support guarded `net_debt` derivation but is not a canonical extracted metric.
- Broad metric catalogue entries are not automatically canonical; planned/unsupported/ambiguous families remain non-canonical until source, extractor, evaluator, and policy gates exist.
- #97 can use this guard as a prerequisite before broader extracted-payload scorecards include expanded metric families.

## Inferred

- The correct next #98 step after this is to decide policy and fixture requirements for any persisted-only or planned family before wiring it into extractor output or evaluator support.
- The current confirmed/gold fixtures exercise supported families only; unsupported future fixture labels would be classified as `gold_only` by the guard and blocked from scoring.

## Speculative

- `finance_costs` may eventually map to `interest_expense`, but only after a semantic policy resolves whether finance costs include non-interest items for each filing style.

## DATA_MISSING

- Approved policy for `total_equity` source labels and null cases.
- Approved policy for `interest_expense` versus `finance_costs`.
- Approved EPS/dividend source/evaluator contracts.
- Approved actual extracted payloads for broad confirmed metric coverage scoring.
- Durable source asset manifest/resolver from #99.
- Architecture-check `.cursor/rules/*` files were absent in this checkout, so the architecture-check skill could only validate against `SYSTEM_CONTRACT.md` and current code evidence.
- `graphify-out/GRAPH_REPORT.md` was absent in this checkout.

## #97 Interaction

#97 added a report-local extracted-payload scorecard builder. This task does not change that scoring path; it adds the contract parity gate that #97 needs before expanded metric-family actuals can be scored without accidentally treating persisted-only fields as supported.

## #98 Advancement

#98 advances from read-only audit finding to enforceable report-local/test-only diagnostics. The guard now fails tests if persisted-only metrics are treated as extractor-supported without explicit contract support.

## #99 Status

#99 is still required before source reviewability is complete. This task separates metric contract parity from durable source PDF/asset resolution and does not inspect, move, or validate source PDFs.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md`: PASS.
- `python3 scripts/agent_job_registry.py list-active --read-only`: PASS, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md --repo-root .`: PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md --repo-root .`: PASS.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q`: FAIL, 5 failed / 5 passed because the ephemeral environment lacked SQLAlchemy for model introspection.
- `uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 --with sqlalchemy python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q`: PASS, `10 passed, 1 warning in 0.75s`.
- `uv run --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with pydantic-settings==2.6.1 --with pydantic==2.9.2 --with sqlalchemy python -c "<generate matrix>"`: PASS.
- `python3 -m json.tool reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/metric_contract_parity_matrix.json`: PASS.
- `git diff --check`: PASS before final report write; rerun required after report artifacts are added.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md --write-report`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md --repo-root .`: PASS, no disallowed files.
- `git diff --cached --check`: PASS after force-adding report artifacts.
- `python3 -m json.tool reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/status.json`: PASS.
- `python3 -m json.tool reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`: PASS.
- `python3 scripts/agent_job_registry.py release extraction_contract_parity_guard_v1_20260526 --repo-root .`: PASS.

## Files Changed

- `docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/README.md`
- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/status.json`
- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/metric_contract_parity_matrix.json`
- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/validation.json`
- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`

## Files Intentionally Not Touched

- Production extraction/backfill paths.
- Production DB/Qdrant/news/memory/canonical truth stores.
- Parser routing and extraction prompts.
- Gold-label fixtures and source PDFs.
- Runtime/model/GPU/service configuration.
- Cockpit UI.
- Persisted database schema and Alembic migrations.

## Remaining Blockers

- Policy for `total_equity` and `interest_expense`/`finance_costs`.
- Source-evidenced fixtures, including expected-null cases, for any expanded metric family.
- Evaluator mapping and payload scorecard thresholds for expanded families.
- Approved actual extracted payloads for broad confirmed coverage.
- #99 source asset manifest/resolver for reviewability.

## Final Git Status

At report write time, reports are ignored until force-added for final `check-diff`. Final git status is recorded in the assistant closeout after validation and registry release.

## Project Memory Recommendation

Save a memory note after closeout: #98 now has a report-local metric contract parity guard in `extraction_gold_eval_scorecard.py`; `total_equity` and `interest_expense` are persisted-only, `total_debt`/borrowings is internal-only, EPS/dividends remain planned, and #97 broader payload scoring remains blocked on this guard plus approved actual payloads and #99 source reviewability.
