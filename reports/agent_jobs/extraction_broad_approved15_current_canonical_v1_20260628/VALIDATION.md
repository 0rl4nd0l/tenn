# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_approved15_current_canonical_v1_20260628.md` -> pass
- `uv run --isolated --with-requirements financial-engine_v2/backend/requirements.txt python - <<'PY' ...` full post-SEG approved-15 replay -> PARTIAL, 15 cases, 11 accepted, 4 fail-closed, 0 infrastructure failures, side-effect audit passed
- `uv run --isolated --with-requirements financial-engine_v2/backend/requirements.txt python - <<'PY' ...` scorecard rebuild after full post-SEG replay -> gate blocked
- `uv run --isolated --with-requirements financial-engine_v2/backend/requirements.txt --with 'pytest>=8.3.3' python -m pytest -q financial-engine_v2/backend/tests/test_multipass_extraction.py -k 'statement_text_overlay_replaces_narrative_future_sales_revenue or statement_text_overlay_replaces_ebitda_with_income_statement_profit_before_tax or shares_prose_recovers_split_number_of_shares_on_issue or shares_prose_rejects_split_weighted_average_shares'` -> 4 passed, 251 deselected, 1 warning
- `uv run --isolated --with-requirements financial-engine_v2/backend/requirements.txt python - <<'PY' ...` focused CSL no-write replay -> PASS, 1 accepted, 0 fail-closed, 0 failed, side-effect audit passed
- `uv run --isolated --with-requirements financial-engine_v2/backend/requirements.txt python - <<'PY' ...` final scorecard rebuild from full post-SEG replay plus focused CSL payload -> gate blocked
- `python3 -m json.tool reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/validation.json` and `handoff/LEDGER_ENTRY.json` -> pass
- `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` -> pass
- `git diff --name-status HEAD..origin/migration/clean-runtime-baseline-reconstruct-v1 -- financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py scripts/extraction_no_write_replay.py financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/eval_fixtures financial-engine_v2/backend/tests/eval_source_assets` -> no extraction-scope drift
- `git diff --check` -> pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_approved15_current_canonical_v1_20260628.md --repo-root .` -> pass
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_approved15_current_canonical_v1_20260628.md --repo-root .` -> pass
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/extraction_broad_approved15_current_canonical_v1_20260628.md --repo-root .` -> pass

Final local contract checks are recorded in `task_card_validate.json`, `diff-check.json`, `report_artifacts_check.json`, and the command transcript in `validation.json`.

## Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Report-local approved-15 no-write extraction evidence and one narrow source-proven extractor behavior improvement; no production extraction output was intended or written. |
| live output location | `reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/*`; no DB/API/queue/store production surface was checked for fresh rows. |
| pre-run max timestamp or count | `DATA_MISSING` for production output; full post-SEG report-local replay count 15 cases before the CSL fix. |
| post-run max timestamp or count | `DATA_MISSING` for production output; focused CSL replay count 1 accepted case; final scorecard actual payload document count 12. |
| rows/files inserted or updated after run start | 0 production rows; report-local artifacts only; tracked code/test/task-card files changed. |
| readiness/gate status | Scorecard gate remains blocked: 97 blocking rows; summary `{'ambiguous_quarantined': 73, 'missing_evidence': 0, 'missing_expected_metric': 4, 'not_evaluated_no_actual_payload': 18, 'present_correct': 49, 'present_wrong_value': 2, 'unsupported_correctly_abstained': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0}`. |
| exact command/query used | See command list above and `validation.json`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Pre-persistence scorecard gate remains blocked; RMS, QBE, DXS, and BHP/MIN classes remain separate unresolved blockers; no production output proof was attempted or allowed. |
