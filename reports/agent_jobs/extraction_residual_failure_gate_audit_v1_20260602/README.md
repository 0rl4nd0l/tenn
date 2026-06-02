# Extraction Residual Failure Gate Audit V1

## Verdict

Runtime/sample scope was not widened. No broad sample, canary, full extraction,
backfill, service restart, DB write, Qdrant write, news write, or memory write was
run in this task.

Three residual sample cases were non-candidate source documents that can be
handled by deterministic source-title gates:

| Case | Prior result | Root cause | Decision |
| --- | --- | --- | --- |
| CQT postponement of quarterly results webinar | `classifier_low_confidence` | webinar scheduling notice, no formal financial statements | candidate exclusion as `non_financial_update_without_formal_statements` |
| NCK FY21 results teleconference | `scale_unknown` | teleconference registration notice before results release, no formal statements | candidate exclusion as `non_financial_update_without_formal_statements` |
| CQT March quarterly activities report | `operational_update_without_formal_statements` | operational quarter update selected as a financial report by broad quarterly wording | candidate exclusion as `operational_update_without_formal_statements` |
| AUK preliminary final report | `scale_validation:suspect_overscaled` | real Appendix 4E with explicit values; extraction over-scaled some rows | no classifier exclusion; keep existing scale validation hard gate |
| RMS H1 results announcement and facility update | `ok_low_confidence` | real H1 result announcement with Appendix 4D/Financial Statements references and mixed facility/update prose | no classifier exclusion; keep low-confidence/report-only diagnostic |

## Guard Added

- Extended the existing results-notice exclusion pattern to include
  `results webinar` and `results teleconference` titles.
- Added a standalone quarterly activities report title guard that excludes
  titles like `march-quarterly-activities-report_<uuid>.pdf` only when title
  plus first-page text lacks formal statement markers such as Appendix
  4C/4D/4E/5B or quarterly cash-flow wording.

This preserves formal candidates such as Appendix 4C business updates, Appendix
5B cash-flow reports, Appendix 4E preliminary final reports, and period reports
with additional operational/drilling content.

## Validation Summary

- Focused pytest: `28 passed, 189 deselected`.
- Direct classifier spot-checks:
  - CQT webinar -> `non_financial_update_without_formal_statements`, excluded.
  - NCK teleconference -> `non_financial_update_without_formal_statements`, excluded.
  - CQT standalone quarterly activities report -> `operational_update_without_formal_statements`, excluded.
  - CQT standalone quarterly title with Appendix 4C first-page text -> `financial_report`, allowed.
  - AUK preliminary final report -> `financial_report`, allowed.
  - RMS H1 result announcement -> `financial_report`, allowed.
- `py_compile`: passed for touched Python.
- `ruff check`: passed for touched Python.

Final diff/check-diff status is recorded in `validation.json` and
`diff-check.json`.

## Next Sampling Verdict

Another random broad sample remains premature. A bounded, same-size validation
rerun can be requested after fresh runtime readiness if the operator wants to
verify that these deterministic source gates remove the residual non-candidate
classes. This audit does not authorize broad backfill or broad graduation.

## DATA_MISSING

- The prompt allowlist mentions `scripts/broad_extraction_test.py`, but this
  checkout contains `financial-engine_v2/scripts/broad_extraction_test.py`.
  The existing script was read-only inspected; no script file was edited.
- No new bounded sample was run by design, so current post-fix sample counts are
  intentionally DATA_MISSING.
