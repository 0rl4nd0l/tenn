# Extraction Residual Candidate Filtering Broad Sample V1

## Summary

This task added deterministic source-document filters for residual broad-runtime
false positives after the PLS statement-evidence fix. The change is limited to
candidate/source classification before metric extraction.

No full extraction/backfill run was performed.

## Filters Added

- `capital_management_update_without_formal_statements` for buyback notices and
  share/unit/security purchase-plan result or final-issue notices that lack
  formal Appendix, financial-statement, or A/H/Q period-report evidence.
- Extended `meeting_results_notice` matching for titles such as
  `results-of-rio-tinto-plc-agm`.
- Extended `operational_update_without_formal_statements` matching for
  purchase-order, sale-agreement, supply-agreement, customer-agreement, and
  commercial-agreement announcements without formal report evidence.

## Valid-Source Regressions Protected

- Formal annual report incorporating Appendix 4E remains a candidate.
- Half-year financial-report investor presentation remains a candidate.
- Appendix 4C quarterly report and business update remains a candidate.
- FY-results-plus-buyback title remains a candidate rather than being treated as
  a standalone buyback notice.

No extraction prompts, gold labels, source PDFs, canonical truth promotion,
storage, retrieval, vectors, runtime model/GPU config, Cockpit UI, or schema
migrations were changed.

## No-Runtime Candidate Inventory

Source root: `/data/asx/docs`

- Input financial-performance PDFs: `28633`
- Candidate count after filters: `22275`
- Excluded count after filters: `6358`
- Excluded reasons:
  - `advisory_only_document`: `50`
  - `capital_management_update_without_formal_statements`: `123`
  - `meeting_notice`: `1660`
  - `meeting_results_notice`: `2287`
  - `non_financial_update_without_formal_statements`: `1965`
  - `operational_update_without_formal_statements`: `268`
  - `unaudited_financial_update_without_formal_statements`: `5`

Exact residual watch titles were excluded. Protected candidate watch found PLS
annual reports, the MLG half-year financial-report investor presentation, and
AZJ FY-results-plus-buyback titles retained.

## Validation

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q -k "source_document_classifier or derive_period_start"`: `29 passed, 184 deselected`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q`: `6 passed`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/scripts/test_broad_extraction_test.py -q`: `219 passed`
- `financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/scripts/test_broad_extraction_test.py`: passed
- `financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/scripts/test_broad_extraction_test.py`: passed
- `git diff --check`: passed
- `git diff --cached --check`: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_residual_candidate_filtering_broad_sample_v1_20260602.md --repo-root .`: `ok=false` because of pre-existing unrelated dirt in `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`; the task card itself validated and the report-local `diff-check.json` was written.

## Runtime Readiness Verdict

Verdict: not clean. Bounded broad sample skipped.

Evidence:

- Initial `/api/health` check on `:8000` failed with connection refused.
- Minimal canonical backend startup reached `/api/health` in a managed session.
- Running backend process cwd matched this checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`.
- Pre-commit checkout HEAD during readiness: `5ea3b65f0749`.
- Closeout commit: recorded in git history and final agent report; not embedded
  here to avoid a self-referential commit hash.
- Backend `/api/health` payload only exposed `{"status":"ok"}`; API-visible
  loaded commit remains `DATA_MISSING`.
- `/api/cockpit/queue` reported `pending=32`, `active=0`, `completed=0`,
  `failed=0`.
- Read-only Redis queue breakdown showed `score=32`, while `ingest=0`,
  `embed=0`, `llm_gpu=0`, and `llm_cpu=0`.
- GPU activity token was inactive.
- GPU guard passed.
- M40 state before sample decision: `0 / 24576 MiB`, utilization `0%`.
- Source path `/data/asx/docs` was present with `28633`
  financial-performance PDFs.
- llama.cpp on `:8001` was down; it was not started because queue readiness was
  already blocked.

Post-cleanup:

- Managed backend session was stopped.
- `/api/health` returned connection refused after shutdown.
- No `run_local_backend`, `uvicorn`, `llama-server`, or
  `broad_extraction_test` process remained.
- GPU activity token remained inactive.
- GPU guard remained clean.
- M40 returned/stayed at `0 / 24576 MiB`.

## Bounded Sample Outcome

No bounded broad sample was run because runtime readiness was not clean. No
`bounded_broad_sample_results.json` was written.

## Remaining DATA_MISSING

- API-visible loaded commit: `/api/health` does not expose a commit field. The
  running process cwd and local HEAD were verified, but no backend endpoint
  confirmed a loaded commit.
- Queue ownership/source for the 32 pending `score` jobs was not determined;
  queue mutation or clearing was outside this task.
- Task-card `check-diff` clean result is blocked by pre-existing unrelated
  `extraction_contract_parity_guard` report dirt outside this task allowlist.

## Project Memory Save Recommendation

Save that residual capital-management, purchase-order/customer-agreement, and
company-name AGM-result title filters landed, but the post-filter broad sample
was intentionally skipped because runtime queue readiness was blocked by
`score=32`.
