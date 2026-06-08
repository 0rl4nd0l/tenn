# CTN Quarterly Source-Type Precedence

State: `DONE`

## Objective

Implement the CTN-only safe extension allowed by the preserved period/source
evidence audit: exact quarterly Appendix 5B / `Quarterly Activity Report`
evidence may dominate an isolated body-text `annual_report_title` hit, while
real annual title or annual period-end evidence remains fail-closed.

## Worktree

- Worktree:
  `/home/l4nd0/tenn-ctn-quarterly-source-type-current-v1-20260608`
- Branch:
  `safe/extraction-ctn-quarterly-source-type-precedence-current-v1-20260608`
- Base HEAD:
  `5d5e1e7b29f16ca5d07d9bfafaea8dc8e98c9368`
- Base ref:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Registry:
  `list-active --read-only` returned `ok=true`, `read_only=true`,
  `active_jobs=[]`, `lock_acquired=false`.

The earlier WIP worktree rooted at preserved audit commit `0d4c8925...` was not
rebased, merged, cleaned, or deleted. This branch was recreated from current
origin to satisfy the clean-current-origin requirement.

## Evidence

- Preserved source audit commit:
  `0d4c8925e0513d210edc3dcc8e34c6571f3acdda`
- CTN document:
  `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- Current failure:
  `validation_gate:period_source_mismatch:payload=Q:source=A:annual_report_title`
- Exact quarterly evidence from the audit:
  `Quarterly Activity Report`, `Period ending 31st March 2022`, Appendix 5B
  `quarterly cash flow report`, and `Quarter ended ... 31/03/2022`.
- Annual hit classified as narrative noise:
  `2014 Annual Report to Shareholders`, historical-cost background text.

## Change

- Added Appendix 5B and `Quarterly Activity Report` source-period evidence
  patterns.
- Tracked whether period evidence came from title or source text.
- Added a narrow precedence rule:
  strong Q evidence may win only when every annual hit is
  `annual_report_title` and every annual hit is from `source_text`, not the
  title.
- Kept true mixed annual/quarterly evidence ambiguous.
- Kept explicit annual period-end evidence hard-blocking Q payloads.

## Files Touched

- `docs/agent_tasks/extraction_ctn_quarterly_source_type_precedence_v1_20260608.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/README.md`
- `reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/validation.json`

## Files Intentionally Not Touched

- HUB/LBL code, data, or reports.
- PR #326/news files.
- PR #318 patch content.
- Source PDFs, DB, Qdrant, Redis, news, memory, prompts, gold labels, runtime,
  schema, production data, service routes, model/GPU config.

## Validation

- Task card validate: passed.
- Registry read-only: passed.
- Syntax compile: passed.
- Focused pytest: passed via isolated `uv` environment:
  `19 passed, 1 warning`.
- Direct unstubbed function probe:
  `DATA_MISSING`; system Python cannot import backend dependencies because
  `pydantic_settings` is missing.
- Stubbed-import direct probe: passed for the CTN Q precedence, mixed annual
  ambiguity, Q payload acceptance, and explicit annual period-end rejection.
- CTN-only saved-artifact scorecard replay: passed via isolated `uv`
  environment. The preserved failed CTN payload replayed as `ok`, with observed
  gain of `+1` document and `+6` currently blocked non-null canonical metrics.

Final `git diff --check`, task-card `check-diff`, JSON validation, and
forbidden-surface audit are recorded in `validation.json`.

## Expected vs Observed Gain

- Expected safe-extension impact against the CTN saved artifact:
  CTN-only recovery candidate, `+1` document / `+6` blocked canonical metrics.
- Observed saved-artifact replay gain:
  `+1` document / `+6` blocked canonical metrics.
- Replayed metric names:
  `capex`, `cash_end`, `financing_cf`, `investing_cf`, `operating_cf`,
  `shares_outstanding`.

## Unsafe Actions Avoided

Did not run count-24, count-32, random samples, broad extraction, backfill, full
ticker extraction, service routes, DB/Qdrant/Redis/news writes, source-PDF
mutation, prompt/gold/schema/runtime/model/GPU mutation, GitHub mutation, or
production-data mutation.

## Remaining Risk

The code path is narrow and covered by focused tests plus CTN-only saved-artifact
replay. Remaining `DATA_MISSING` is limited to preserved scorecard row refs and
extraction_run_id; this is not a broad extraction readiness claim.

## Next Recommended Task

Open a draft PR for the CTN-only branch and let CI validate the focused pytest
target in the canonical environment. Keep HUB/LBL follow-up separate.
