# Validation

## Preflight

- stale worktree guard: block, STALE_PATH
- fresh worktree tenn_dev_status: pass, VALID_TASK_WORKTREE
- fresh portable guard: pass
- task ledger validation: pass
- active registry read-only check: pass, active_jobs=[]
- task card validation: pass
- task-card diff check: pass, disallowed_files=[]

## Final Guard And Status

- final task-card validation: pass
- final task-card diff check: pass, disallowed_files=[]
- final task ledger validation: pass, 291 entries checked
- final active registry read-only check: pass, active_jobs=[]
- final `python3 scripts/tenn_dev_status.py`: GUARD_RESULT pass,
  GUARD_PATH_CLASSIFICATION DIRTY_UNRELATED_WORKTREE, STATE DIRTY
- final portable guard JSON: final_decision block,
  path_ownership.classification DIRTY_RELATED_WORKTREE,
  stop_reimplementation true

The final portable guard block is the expected stop condition after this task's
owned implementation edits. No further implementation should continue in this
worktree until the owner approves the next class or reviews/parks this patch.
For the QBE continuation, the owner explicitly approved continuing despite the
same `DIRTY_RELATED_WORKTREE` block because this dirty worktree is the active
approved15 lane and task-card `check-diff` is clean.

For the BHP/CSL NPAT continuation, the owner explicitly approved continuing
despite the same `DIRTY_RELATED_WORKTREE` block because this dirty worktree is
the active approved15 lane and task-card `check-diff` is clean.

For the CSL revenue continuation, the owner approved proceeding with the
previously recommended single class. The same `DIRTY_RELATED_WORKTREE` owner
override applies only to this active approved15 lane and this one class.

## Unit Tests

Command:

```bash
uv run --with pytest==8.3.3 --with pytest-asyncio==0.24.0 --with python-dateutil==2.9.0.post0 --with pydantic-settings==2.6.1 --with pymupdf==1.24.10 python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -k "net_debt or total_debt or non_aud or source_bound_native_currency" -q
```

Result:

```text
48 passed, 217 deselected in 0.51s
```

QBE continuation command:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py -k "auditor_review_report_cannot_claim_balance_sheet or pymupdf_blank_value_rows or pass2_cf_disqualification_blocks_5b_from_balance_sheet or pass2_cross_guarantee_note_cannot_claim_income_statement or pass3a_recovers_total_debt_from_current_and_noncurrent_borrowings or pass3a_recovers_total_debt_from_multiline_balance_sheet_groups or pass3a_recovers_explicit_net_debt_from_balance_sheet_row or pass4_reconciler_accepts_borrowings_and_finance_lease_liabilities"
```

Result:

```text
8 passed, 259 deselected, 1 warning in 0.97s
```

BHP/CSL NPAT red command before the row-selection patch:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py -k "bhp_shareholder_attributable_row or csl_shareholder_split_row"
```

Result:

```text
2 failed, proving the generic-profit NPAT row-selection bug.
```

BHP/CSL NPAT focused green command:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py -k "bhp_shareholder_attributable_row or csl_shareholder_split_row or income_source_overlay or income_statement_recovers_operations_and_owner_attributable_rows or auditor_review_report_cannot_claim_balance_sheet or pymupdf_blank_value_rows"
```

Result:

```text
12 passed, 257 deselected, 1 warning in 1.00s
```

Full-file attempt:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py
```

Result:

```text
264 passed, 5 failed.
```

The full-file failures were outside this class: four dependency/import failures
from missing optional env packages (`sqlalchemy`, `httpx`) and one pre-existing
parallel/mock row-ref mismatch involving `net_debt`. No broad fix was attempted.

CSL revenue red command before the row-selection patch:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py -k "csl_total_operating_revenue_split_row"
```

Result:

```text
1 failed, proving `revenue` was absent from the payload for the split CSL row.
```

CSL revenue focused green command:

```bash
uv run --with pytest==8.3.4 --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 pytest tests/test_multipass_extraction.py -k "csl_total_operating_revenue_split_row or bhp_shareholder_attributable_row or csl_shareholder_split_row or income_source_overlay or income_statement_recovers_operations_and_owner_attributable_rows or auditor_review_report_cannot_claim_balance_sheet or pymupdf_blank_value_rows"
```

Result:

```text
13 passed, 257 deselected, 1 warning in 0.52s
```

Code review:

```text
No critical or warning findings for the CSL revenue helper/test change.
```

## QBE Source-Selection Proof

Command:

```bash
uv run --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 python - <<'PY'
from app.services.docling_extract import _extract_pymupdf
from app.services.multipass_extraction import _run_pass2_locator, _recover_total_debt_from_balance_sheet_table
pdf = "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/QBE/financial_performance/2025-08-08_2025-half-year-results-and-financial-statements_e7387eb3-3667-4148-82a0-e86cd9975440.pdf"
doc = _extract_pymupdf(pdf)
for i, table in enumerate(doc.tables):
    table.index_in_doc = i
bs = _run_pass2_locator(doc.tables).get("balance_sheet")
print("balance_sheet_index", getattr(bs, "index_in_doc", None))
print("balance_sheet_page", getattr(bs, "page_number", None))
print("total_debt_recovery", _recover_total_debt_from_balance_sheet_table(bs, "millions"))
PY
```

Result:

```text
balance_sheet_index 20
balance_sheet_page 19
total_debt_recovery (3679000000.0, 'Borrowings 4.1')
```

## BHP/CSL NPAT Source-Selection Proof

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 python - <<'PY'
from app.services.docling_extract import _extract_pymupdf
from app.services.multipass_extraction import _recover_income_statement_metrics_from_table
cases = {
    'BHP': ('/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/BHP/financial_performance/2021-08-17_preliminary-final-report_37ba70c7-2724-4142-83a9-b55106f78907.pdf', 43),
    'CSL': ('/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CSL/financial_performance/2026-02-11_csl-statutory-accounts-for-the-half-year-ended-31-december_68834fe5-e2af-4373-a2cb-08f7ad8c0465.pdf', 15),
}
for name, (pdf, table_index) in cases.items():
    doc = _extract_pymupdf(pdf)
    table = doc.tables[table_index]
    recovered = _recover_income_statement_metrics_from_table(table, 'millions')
    print(name, 'table', table_index, 'page', table.page_number, recovered.get('np_attributable'))
PY
```

Result:

```text
BHP table 43 page 44 (11304000000.0, 'Attributable to BHP shareholders')
CSL table 15 page 11 (401000000.0, '- Shareholders of CSL Limited')
```

## CSL Revenue Source-Selection Proof

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with pymupdf==1.24.10 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with PyYAML==6.0.2 python - <<'PY'
from app.services.docling_extract import _extract_pymupdf
from app.services.multipass_extraction import _run_pass2_locator, _recover_income_statement_metrics_from_table
pdf='/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CSL/financial_performance/2026-02-11_csl-statutory-accounts-for-the-half-year-ended-31-december_68834fe5-e2af-4373-a2cb-08f7ad8c0465.pdf'
doc=_extract_pymupdf(pdf)
for i,t in enumerate(doc.tables):
    t.index_in_doc=i
income=_run_pass2_locator(doc.tables).get('income_statement')
print('selected_table', getattr(income,'index_in_doc',None), getattr(income,'page_number',None), getattr(income,'caption',None))
print('recovered', _recover_income_statement_metrics_from_table(income, 'millions'))
PY
```

Result:

```text
selected_table 15 11 Consolidated Statement of Comprehensive Income
recovered {'revenue': (8332000000.0, 'Total operating revenue'), 'ebit': (577000000.0, 'Operating profit (EBIT)'), 'np_attributable': (401000000.0, '- Shareholders of CSL Limited')}
```

## Whitespace And Allowlist

Commands:

```bash
git diff --check
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/approved15_native_currency_metric_blocker_remediation_v1_20260707.md
```

Results:

- `git diff --check`: pass
- `check-diff`: pass, disallowed_files=[]

## Four-Case No-Write Replay

Command:

```bash
uv run --with httpx==0.27.2 --with qdrant-client==1.12.1 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with python-dateutil==2.9.0.post0 --with pymupdf==1.24.10 --with PyYAML==6.0.2 python scripts/extraction_no_write_replay.py --case-manifest financial-engine_v2/data/extraction_no_write_cases/approved15_current_origin_cases_v1.json --case BHP_A_2021-06-30 --case CSL_H_2025-12-31 --case FMG_H_2025-12-31 --case QBE_H_2025-06-30 --report-dir reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green --profile baseline-no-write --case-timeout-seconds 900
```

Result:

```json
{
  "case_count": 4,
  "preflight_only": false,
  "profile": "baseline-no-write",
  "report_dir": "reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green",
  "side_effect_pass": true,
  "status": "PASS"
}
```

Scorecard artifacts:

- `actual_payload_map_green.json`
- `payload_scorecard_green.json`
- `scorecard_gate_green.json`
- `failure_classes_green.json`

Final scorecard after FMG shares continuation:

```json
{
  "gate_status": "pass",
  "total_metric_expectations": 40,
  "scored_metric_expectations": 40,
  "result_class_summary": {
    "present_correct": 40,
    "present_wrong_value": 0,
    "missing_expected_metric": 0,
    "missing_evidence": 0,
    "not_evaluated_no_actual_payload": 0,
    "ambiguous_quarantined": 0,
    "wrong_period": 0,
    "wrong_unit_currency_scale": 0,
    "unsupported_correctly_abstained": 0
  },
  "blocking_result_class_summary": {},
  "failure_count": 0
}
```

Remaining failure classes:

```text
none
```

FMG source-bound payload evidence:

```json
{
  "shares_outstanding": 3078964918,
  "row_ref": "At 31 December 2025",
  "provenance": "share_capital:page_30:At 31 December 2025"
}
```

## Runtime Functionality Proof

| Field | Evidence |
| --- | --- |
| intended output | Four-case no-write replay payloads and report-local scorecard for approved15 native-currency blocker slice |
| live output location | `reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/replay_results.json`, `scorecard_gate_green.json`, `failure_classes_green.json` |
| pre-run max timestamp or count | prior green scorecard after CSL revenue: 40 expectations, 39 present_correct, 1 blocker |
| post-run max timestamp or count | final green scorecard after FMG shares: 40 expectations, 40 present_correct, 0 blockers |
| rows/files inserted or updated after run start | report-local replay and scorecard artifacts only; production rows updated: 0 |
| readiness/gate status | replay PASS, side_effect_pass true, scorecard gate pass |
| exact command/query used | four-case no-write replay command above plus report-local scorecard builder |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | WORKING |
| remaining blocker | none in the approved four-case blocker slice |

## Final Status

Final checks after the FMG shares continuation:

- `git diff --check`: pass
- task-card `validate`: pass, issues=[]
- task-card `check-diff`: pass, disallowed_files=[]
- task ledger validate: pass, 291 entries checked
- active registry read-only check: pass, active_jobs=[]
- focused pytest selection after final code cleanup: 19 passed, 252 deselected
- full `tests/test_multipass_extraction.py` exploratory run: not used as the
  focused gate; after validation-only deps were added it still had
  `test_upsert_financial_rows_smoke` blocked by additional missing pipeline
  dependency `qdrant_client`, and
  `test_pass3a_parallel_matches_sequential` failed on an unrelated row_refs
  mismatch outside the FMG shares class
- `python3 scripts/tenn_dev_status.py`: pass, `DIRTY_UNRELATED_WORKTREE`, `stop_reimplementation=false`
- portable guard: block, `DIRTY_RELATED_WORKTREE`, `stop_reimplementation=true`; owner-approved override applies only to this active approved15 lane

Approved worktree status:

```text
 M financial-engine_v2/backend/app/services/multipass_extraction.py
 M financial-engine_v2/backend/tests/test_multipass_extraction.py
?? docs/agent_tasks/approved15_native_currency_metric_blocker_remediation_v1_20260707.md
```

Launch checkout status preserved:

```text
?? docs/agent_tasks/cockpit_router_import_hardening_v1_20260707.md
?? docs/agent_tasks/opencode_deepseek_scout_delegation_v1_20260707.md
```
