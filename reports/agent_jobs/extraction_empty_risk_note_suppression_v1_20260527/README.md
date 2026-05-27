# Empty ASXRiskNote Suppression - 2026-05-27

## Verdict

Status: FIXED FOR THE NARROW PERSISTENCE BUG.

No canary was run. No broad backfill was run. No production DB writes, direct
SQL mutation, Qdrant/news/memory writes, service restart, parser routing change,
prompt change, gold-label mutation, schema migration, source PDF edit, canonical
truth promotion change, runtime/model/GPU config change, or Cockpit UI change
was made.

The active runtime checkout had unrelated PR39/architecture dirt, so this job
used the clean isolated worktree
`/home/l4nd0/tenn-extraction-empty-risk-note-suppression-v1-20260527`.

## Root Cause

Confirmed.

Before this fix, `_upsert_financial_rows()` unconditionally called
`_upsert_risk_note(db, doc, structured, allow_empty=True)` after financial-row
handling. `_upsert_risk_note()` creates a row when `allow_empty=True`, even when
`_has_narrative_content(structured)` is false. `process_document()` separately
reported `risk_note_written` from `_has_narrative_content(structured)`, so an
empty row could be inserted while the summary honestly reported
`risk_note_written: 0`.

The only code change is:

- `financial-engine_v2/backend/app/services/pipeline.py`: the financial-row path
  now calls `_upsert_risk_note(..., allow_empty=False)`.

That makes row creation use the same narrative-content gate as
`risk_note_written`.

## Files Changed

- `docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/tests/test_pipeline_stages.py`
- `reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/README.md`
- `reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/status.json`
- `reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/validation.json`
- `reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/diff-check.json`
- `reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/github_issue_96_comment.md`
- `reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/README.md`
- `reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/status.json`

## Proof

Empty rows are suppressed:

- `test_upsert_financial_rows_suppresses_empty_risk_note` uses an in-memory DB,
  a financial payload with empty narrative fields and `confidence_narrative: 0`,
  and verifies one `ASXPeriodicFinancial` row plus zero `ASXRiskNote` rows.
- `test_process_document_records_reproducibility_for_ok_low_confidence` verifies
  an OK low-confidence no-narrative path reports `risk_note_written: 0`.

Real narrative rows still persist:

- `test_upsert_financial_rows_persists_real_risk_note` verifies a non-empty risk
  summary, bullets, guidance, and confidence are persisted to `ASXRiskNote`.
- `test_process_document_persists_narrative_for_failed_validation_gate` still
  passes, proving failed validation-gate payloads with narrative content continue
  to persist through `_upsert_risk_note(..., allow_empty=False)`.

Financial extraction semantics are unchanged:

- The metric upsert fields, scale validation, parser routing, extraction prompts,
  gold labels, canonical truth promotion, and runtime settings were not changed.
- PLS `validation_gate:scale_unknown` abstention behavior is unchanged.
- BHP native USD/no-FX `ok_low_confidence` behavior is unchanged.

## Validation

- Task-card validation: PASS.
- Registry list-active: PASS; one unrelated Reporting job was active, with no
  overlap on this lane or file set.
- Registry check-overlap: PASS.
- Registry claim: PASS.
- Focused pytest: PASS, 4 passed.
  - `tests/test_pipeline_stages.py::test_process_document_records_reproducibility_for_ok_low_confidence`
  - `tests/test_pipeline_stages.py::test_upsert_financial_rows_suppresses_empty_risk_note`
  - `tests/test_pipeline_stages.py::test_upsert_financial_rows_persists_real_risk_note`
  - `tests/test_pipeline_stages.py::test_process_document_persists_narrative_for_failed_validation_gate`
- `py_compile` touched Python files: PASS.
- Ruff touched Python files: PASS.
- `git diff --check`: PASS.
- JSON validation for report artifacts: PASS after final artifact write.
- Task-card check-diff: PASS after final artifact write.
- Source PDFs staged: none.
- Registry release: PASS after final validation.
- Final registry list-active: PASS after release.

## Second Canary Batch

From this task's scope, the empty-`ASXRiskNote` persistence blocker is fixed and
the second canary batch is safe to request from the risk-note persistence
standpoint.

Remaining conditions are outside this task's mutation scope: the second canary
batch was not run here, orders 3-10 were not audited here, and live canary
results after this patch remain `DATA_MISSING`.

## DATA_MISSING

- No second canary batch was run.
- No broad backfill was run.
- No production DB row cleanup was attempted for the already-created empty BHP
  `ASXRiskNote` row.
- Orders 3-10 were not audited in this task.
- Repo-local `.cursor/rules/` architecture rule files are absent in this
  isolated worktree; architecture review was therefore limited to task-card hard
  stops and touched backend persistence behavior.

## GitHub

Posted a concise issue #96 update:
`https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4553213822`.

The GitHub mutation was comment-only: no close, relabel, assignment, milestone,
or issue-body edit was performed.

## Project Memory Recommendation

Save that the narrow issue #96 empty-`ASXRiskNote` persistence bug was fixed by
changing `_upsert_financial_rows()` to call `_upsert_risk_note(...,
allow_empty=False)`. Focused DB tests now prove empty no-narrative payloads do
not create risk-note rows, while real narrative payloads still persist. No
canary or backfill was run.
