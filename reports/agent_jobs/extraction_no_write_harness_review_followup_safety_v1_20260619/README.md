# No-Write Harness Review Follow-Up Safety

State: DONE

This focused PR #379 follow-up addresses fresh no-write harness safety review
findings raised after the portable-path and pre-clear validation repair.

## Changes

- Preserve `DATA_ROOT` and `DOCS_ROOT` through `docling-no-write` profile
  re-exec so portable source roots survive into the selected approved venv.
- Force selected `docling-no-write` cases to `parser_backend=docling` and
  `strict_parser=true` before replay so PyMuPDF fallback cannot certify a
  docling profile pass.
- Snapshot content hashes for repo files that were already dirty before replay,
  so writes to an already-dirty prompt/config/source file still fail the
  no-write side-effect audit.
- Snapshot whole normal parser cache roots, including unpredicted cache files,
  instead of checking only predicted per-PDF cache filenames.
- Treat unexpected per-case extraction exceptions as `FAIL`; only explicit
  infrastructure failures and missing LLM/docling prerequisites remain
  `DATA_MISSING`.

## Validation

- Task-card validate: PASS
- Focused no-write replay unit tests: PASS, 26 tests
- `py_compile`: PASS
- `git diff --check`: PASS
- Task-card `check-diff`: PASS
- Report artifact check: PASS
- Report JSON validation: PASS
- Baseline certified no-write preflight: PASS, 6 cases, side_effect_pass=true

## Docs Impact Check

- docs_impact: DOCS_UPDATED
- docs_checked:
  - `docs/agent_tasks/extraction_no_write_harness_review_followup_safety_v1_20260619.md`
- docs_changed:
  - `docs/agent_tasks/extraction_no_write_harness_review_followup_safety_v1_20260619.md`
- docs_followup: NONE
- reason: task card documents the PR #379 safety follow-up scope and hard
  boundaries.

## Worker Context

The Phase 3 board workers remained report-only. Their results are under:

- `reports/agent_jobs/extraction_metric_extraction_review_board_v1_20260619/worker_results/matrix_refresh/WORKER_RESULT.md`
- `reports/agent_jobs/extraction_metric_extraction_review_board_v1_20260619/worker_results/whc_period_source/WORKER_RESULT.md`
- `reports/agent_jobs/extraction_metric_extraction_review_board_v1_20260619/worker_results/hub_period_source/WORKER_RESULT.md`
- `reports/agent_jobs/extraction_metric_extraction_review_board_v1_20260619/worker_results/docling_readiness/WORKER_RESULT.md`

Only this no-write harness safety follow-up is integrated in code. The WHC
exact-case period/source proof is not integrated in this commit.

## Unsafe Actions Avoided

No broad extraction, count-24/count-32, random sample, backfill, full-universe
extraction, services, DB, Qdrant, Redis, news, memory, source-PDF, prompt,
gold-label, schema, runtime, model, GPU, production-data, merge, rebase,
cherry-pick, reset, stash, clean, or unrelated GitHub/issue mutation was
performed.
