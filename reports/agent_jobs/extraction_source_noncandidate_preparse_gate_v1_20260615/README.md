# Extraction Source Noncandidate Preparse Gate

## Objective

Make one concrete production-readiness improvement to Tenn financial metric
extraction from the remaining root-cause matrix after PR #346.

## Current State

DONE_WITH_RISK pending PR review. A narrow extraction code/test change blocks
title-only source noncandidates before parser import, parser execution, and
metric extraction work.

## Why This Class

After PR #346 fixed the LBL companion period provenance path, the merged-base
root-cause matrix leaves `document_family_eligibility_noncandidate_prefilter` as
the largest remaining cluster: five documents with zero metric upside but real
sample-quality and operational-cost impact. The other remaining classes were
less suitable for this bounded production change: DXC is desirable fail-closed
metric-label behavior, AZJ did not reproduce in isolated pass3a replay, and LBL
period binding was already handled by PR #346.

## Evidence Used

- Fresh worktree:
  `/home/l4nd0/tenn-source-noncandidate-source-kind-guard-v1-20260615`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
  `107adb03852558d42795b28c3a5ec887e7cd0c64`
- PR #346 live state: merged, merge commit
  `107adb03852558d42795b28c3a5ec887e7cd0c64`.
- Registry read-only: `ok=true`, `read_only=true`, `active_jobs=[]`.
- Matrix handoff:
  `/tmp/tenn_extraction_broad_root_cause_matrix_handoff_20260614.md`.
- Existing reports:
  `reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/`
  and
  `reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/`.

## Files Touched

- `docs/agent_tasks/extraction_source_noncandidate_preparse_gate_v1_20260615.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/README.md`
- `reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/status.json`
- `reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/validation.json`
- `reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/diff-check.json`

## Files Intentionally Not Touched

- Source PDFs, gold labels, prompts, schema, DB, Qdrant, Redis, news stores,
  memory, runtime/service/model/GPU config.
- LBL period-binding logic beyond preserving it as existing code.
- The dirty shared checkout except for removing the task-card file that was
  accidentally created there by this agent.

## Implementation

- Added a focused regression test proving an FCL board-change title is blocked
  before `extract_structured()` is called.
- Updated that regression after Codex review to make `app.services.docling_extract`
  unimportable, proving the source-noncandidate return path no longer depends
  on parser module imports such as PyMuPDF.
- Added a title-only pre-parser source-document classification gate in
  `run_multipass_extraction()`.
- Deferred the `docling_extract` import until after the title-only gate returns.
- Returned the existing `validation_gate:source_noncandidate:*` payload shape
  with `source_document_classification` and `source_document_gate`.

## Commands Run

- `git fetch origin --prune`: exit 0.
- `gh pr view 346 --json number,state,mergedAt,baseRefName,headRefName,mergeCommit,title,url`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only`: exit 0.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_source_noncandidate_preparse_gate_v1_20260615.md`: exit 0.
- RED:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_blocks_title_only_source_noncandidate_before_parser -q`: exit 1, failed because `extract_structured()` was called once.
- GREEN:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_blocks_title_only_source_noncandidate_before_parser financial-engine_v2/backend/tests/test_multipass_extraction.py::test_source_document_classifier_excludes_known_false_positive_classes financial-engine_v2/backend/tests/test_multipass_extraction.py::test_source_document_classifier_preserves_valid_report_candidates -q`: exit 0, 13 passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`: exit 0.
- `git diff --check`: exit 0.
- Review-fix regression:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest pytest financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_blocks_title_only_source_noncandidate_before_parser_import -q`: exit 0, 1 passed.
- Review-fix focused slice:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest pytest financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_blocks_title_only_source_noncandidate_before_parser_import financial-engine_v2/backend/tests/test_multipass_extraction.py::test_source_document_classifier_excludes_known_false_positive_classes financial-engine_v2/backend/tests/test_multipass_extraction.py::test_source_document_classifier_preserves_valid_report_candidates -q`: exit 0, 13 passed.
- Review-fix static checks:
  `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`: exit 0;
  `uv run --with ruff ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`: exit 0;
  `git diff --check`: exit 0.

## Validation Status

Focused validation passed. No broad extraction, sample, count-24, count-32,
backfill, service route, DB/Qdrant/news/memory/source-PDF/gold-label mutation,
or production runtime mutation was run.

## DATA_MISSING

- No fresh broad scorecard run was performed by design.
- The production impact is inferred from the merged-base root-cause matrix and
  focused unit behavior, not from a new corpus-wide measurement.

## Remaining Risk

This improves fail-fast behavior and operational readiness for title-only
source noncandidates. It does not recover canonical metrics, and it does not
solve parser/table coverage or metric coverage gaps.

## Next Recommended Prompt

Review PR for `safe/extraction-source-noncandidate-source-kind-guard-v1-20260615`;
if accepted, merge it and then pick the next non-LBL production-readiness class
from current evidence.
