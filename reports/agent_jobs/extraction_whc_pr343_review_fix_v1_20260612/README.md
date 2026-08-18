# WHC PR343 Review Fix Closeout

Status: DONE_WITH_RISK until the pushed review-fix commit receives fresh GitHub CI and Sloppy Scan/scan results.

## Scope

This packet addresses two code-review warnings on PR #343 only:

- Openability diagnostics cached for one requested page set must not be reused for a different requested page set.
- Synthetic WHC openability selected tables must ignore malformed `period_phrases` payloads, matching the existing fail-closed period-source guard.

## Files Changed

- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_docling_extract.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- this task card and report artifacts

## Validation

- Focused new tests: 2 passed.
- Modified test files: 219 passed.
- `py_compile`: passed.
- `ruff check`: passed.
- task-card validate: passed.
- registry/list-active read-only: ok, `active_jobs=[]`.
- `git diff --check`: passed.
- task-card check-diff: passed, `disallowed_files=[]`.

## Forbidden Actions Not Run

No count-24/count-32, broad extraction, random sampling, backfill, service routes, production DB/Qdrant/Redis/news/memory/source-PDF mutation, prompt/gold/schema/runtime/model/GPU mutation, PR #318 patch mining, PR #343 merge, or PR #340 close/merge.

## Next

Push the branch update for PR #343, wait for fresh CI and Sloppy Scan/scan, then merge PR #343 only if those checks remain green. PR #340 should be superseded only with explicit operator approval.
