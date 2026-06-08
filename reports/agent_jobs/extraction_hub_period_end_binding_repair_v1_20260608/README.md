# HUB Period-End Binding Repair

State: `DONE`

## Objective

Implement the HUB-only safe extension allowed by the preserved exact-evidence
audit: explicit source-text half-year period-end evidence may replace a Pass 1
half-year `period_end` only when Pass 1 used the leading ASX announcement title
date.

## Worktree

- Worktree:
  `/home/l4nd0/tenn-hub-period-end-binding-v1-20260608`
- Branch:
  `safe/extraction-hub-period-end-binding-v1-20260608`
- Base HEAD:
  `c5c39d128a6e1ea23415f08803844677add1efdd`
- Base ref:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Registry:
  `list-active --read-only` returned `ok=true`, `read_only=true`,
  `active_jobs=[]`, `lock_acquired=false`.

The dirty checkout at
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` was not used for the
repair. Its pre-existing cockpit-news changes were left untouched.

## Evidence

- Preserved scorecard commit:
  `6e8be73cf5e16f8923d33f60ad7887c70aef1bd9`
- Repair closeout commit:
  `df821df661c1218d8155d6addaf44e3b3b9e6a14`
- Exact evidence audit:
  `/home/l4nd0/tenn-extraction-period-source-exact-evidence-audit-v1-20260608/reports/agent_jobs/extraction_period_source_exact_evidence_audit_v1_20260608/evidence_audit.json`

HUB target:

- Document:
  `419bcca8-213e-4706-8962-8e3bd8adf091`
- Title:
  `2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_419bcca8-213e-4706-8962-8e3bd8adf091.pdf`
- Original gate:
  `validation_gate:announcement_date_period_end:period_type=H:period_end=2024-02-20:title_date=2024-02-20:leading_title_date`
- Exact source-bound period evidence:
  `Half-year ended 31 December 2023`.
- Audit locality:
  page 3 same-page document header plus table-local support.

LBL boundary:

- Document:
  `551c6b84-1053-405c-a833-4ecc018e2045`
- Evidence has `1H FY26` / `Half-Year` labels only.
- Exact source-bound period-end date remains `DATA_MISSING`.
- LBL stays fail-closed.

## Change

- `_detect_source_period_end_evidence` now records each hit source as `title` or
  `source_text`.
- `_has_source_text_period_end_hit` centralizes the source-bound test used by
  period-end binding paths.
- Added `_bind_explicit_source_period_end_over_announcement_date`.
- The binder only fires when:
  - Pass 1/classifier period type is `H`;
  - explicit source period-end evidence type is `H`;
  - the evidence reason is `half_year_ended_explicit_date`;
  - at least one matching hit comes from parsed `source_text`;
  - the current `period_end` differs from the source period end;
  - the title has a half-year hint; and
  - the current `period_end` equals the leading announcement title date.
- Missing Pass 1 `period_end` is now filled only when the explicit period-end
  evidence has a parsed `source_text` hit.
- Appendix wrapper period-end propagation uses the same source-text-hit guard,
  so title-only Appendix 4D evidence cannot re-enter through the wrapper path.
- The reconciled payload surfaces `source_period_end_binding` for traceability.

## Saved-Artifact Replay

Mode: saved artifact replay only, no extraction.

- HUB original: failed on announcement-date period end with 9 non-null canonical
  metrics blocked.
- HUB replay: exact source text bound `period_end=2023-12-31`, gate status `ok`.
- LBL original: failed on announcement-date period end with 6 non-null canonical
  metrics blocked.
- LBL replay: no exact source period-end evidence, override did not apply, gate
  remains `announcement_date_period_end`.

Observed saved-artifact gain:

- `+1` document.
- `+9` currently blocked non-null canonical metrics.

Expected broad HUB/LBL gain is intentionally not claimed because LBL is still
fail-closed.

## Files Touched

- `docs/agent_tasks/extraction_hub_period_end_binding_repair_v1_20260608.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_hub_period_end_binding_repair_v1_20260608/README.md`
- `reports/agent_jobs/extraction_hub_period_end_binding_repair_v1_20260608/validation.json`

## Validation

Recorded in `validation.json`.

Focused checks passed after the PR #336 title-only follow-up:

- Task card validate.
- Registry `list-active --read-only`.
- `py_compile` for `multipass_extraction.py`.
- Focused HUB/LBL/source-period tests: `14 passed`.
- Existing announcement-date and half-year run-path subset: `5 passed`.
- Saved-artifact replay: HUB `+1/+9`, LBL `+0/+0`.

Full `test_extraction_pre_canary_truth_gates.py` under isolated `uv` reported
`23 passed, 1 failed`; the failure is the pre-existing advisory-only test patch
target `app.services.docling_extract`, unrelated to this HUB period binding
change.

Subagent diff review flagged one test gap: the title-only explicit-period
negative needed an end-to-end `_validate_gate` assertion. That assertion was
added, and the focused test set was rerun successfully.

PR #336 follow-up review fix: title-only explicit period-end evidence is also
blocked when Pass 1 misses `period_end` entirely. The negative run-path test
uses `2024-02-20 Half-year ended 31 December 2023 HUB.pdf` as title-only
evidence and verifies `period_end` stays missing; the positive run-path test
uses parsed source text `Appendix 4D. Half-year ended 31 December 2023` and
verifies `period_end=2023-12-31`.

## Unsafe Actions Avoided

Did not run count-24, count-32, random samples, broad extraction, backfill, full
ticker extraction, service routes, DB/Qdrant/Redis/news writes, source-PDF
mutation, prompt/gold/schema/runtime/model/GPU mutation, GitHub mutation, or
production-data mutation.

Did not touch PR #326/news files or use PR #318 as a patch source.

## DATA_MISSING

- LBL exact source-bound half-year period-end date.
- HUB/LBL row refs and extraction run IDs in the preserved scorecard.
- A configured `/workspace/.venv`; focused tests used isolated `uv` instead.

## Next Recommended Task

Open the HUB-only repair PR after final hygiene passes. The next system-level
validation after this repair is a bounded saved-artifact or approved count-bound
validation run, not broad extraction or backfill.
