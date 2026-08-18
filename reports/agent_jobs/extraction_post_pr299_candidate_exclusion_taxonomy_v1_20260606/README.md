# Post-PR299 Candidate Exclusion Taxonomy

Status: validated, commit pending.

Timestamp: 2026-06-06T13:06:17+10:00

Worktree:
`/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606`

Branch:
`safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`

HEAD:
`9436d1d32de0da5423b8edcfc7efc883ccac3fd6`

## Scope

This phase adds narrow deterministic noncandidate source-class rules for five
known post-PR297 false-positive classes:

- `meeting_or_proxy_notice`
- `board_change_notice`
- `operational_project_update`
- `share_sale_or_gross_proceeds_announcement`
- `pre_results_segment_re_presentation`

The gate reason emitted for these classes is
`source_noncandidate:<document_class>`. The broad extraction scorecard now
preserves that reason rather than collapsing it to a generic validation class.

## Audited Source Classes

The five representative documents were inspected read-only from the live corpus
path. No source PDFs were edited, moved, staged, or committed.

- EQR notice/proxy material: first page identifies an upcoming general meeting,
  annual general meeting material, notice of meeting, explanatory memorandum,
  and proxy-style material.
- MAH operational project update: first page identifies an update in relation to
  the Mt Morgans Gold Project and operational mining-status content.
- FCL board-change notice: first page identifies FINEOS board changes and
  director appointment/approval material.
- HRZ share-sale/gross-proceeds announcement: first page identifies VOX shares
  sold and gross proceeds.
- MPL pre-results segment re-presentation: first page identifies segment-result
  re-presentation, terminology changes, planned half-year results announcement,
  and no change to statutory financial results.

Detailed source paths and classifier outputs are in
`source_classification_audit.json`.

## Files Touched

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `docs/extraction/metric_extraction_contract.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- Phase 1 report artifacts under this directory

## Unsafe Actions Avoided

No broad sample, count-24/count-32, broad backfill, full ticker-universe
extraction, source-PDF mutation, DB/Qdrant/news/memory mutation, service
restart, direct SQL mutation, prompt/gold-label/schema/runtime change, stash,
reset, cleanup, merge, or rebase has run in this phase.

## Validation

Passed so far:

- `pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -k 'source_document_classifier' -q`
  passed: 9 passed, 166 deselected.
- `pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q`
  passed: 2 passed.
- `python -m py_compile` passed for touched Python files.
- `ruff check` passed for touched Python files.
- `python -m json.tool` passed for JSON report artifacts.
- `git diff --check` passed.
- `agent_job_contract.py check-diff ... --no-write-report` passed after the
  parent preflight artifacts were split into parent commit `85b05a92`.
- Source-PDF staging audit passed: no `*.pdf` paths are staged.
- Registry/list-active returned `active_jobs: []`, `ok: true`, `read_only:
  false`, `lock_acquired: true`; this is limited evidence, not a safe read-only
  registry proof.

Remaining before commit:

- write and stage `diff-check.json`;
- final staged `check-diff`.

## Phase 2 Gate

Phase 2 must not start until this phase commits cleanly.
