# ASX Comparator Artifact Schema v1 Report

## Confirmed Facts

- Repo root symlink resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch at preflight: `migration/clean-runtime-baseline-reconstruct-v1`.
- Pre-implementation HEAD: `f425ebc144e1`.
- HEAD at preflight: `f425ebc1 milestone(evaluation): checkpoint route parity audit`.
- Task card validated successfully after adding required YAML frontmatter and safe-extension metadata.
- Registry overlap check passed for `asx_comparator_artifact_schema_v1_20260521`.
- Registry claim succeeded for this Financial Truth safe-extension job.
- A separate active Strategy Lab Evaluation job appeared later. It does not overlap this task's allowed files or lane.
- No production data access was used.
- No extraction, Docling, OCR, comparator tools, Qdrant, news jobs, memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, parser routing, gold-label updates, canonical scorecard updates, DB writes, or canonical writes were run.

## Inferred Facts

- The repo's task-card checker requires YAML frontmatter plus `approval_required` and `timeout_seconds`.
- This safe-extension card also needed `allow_unapproved_safe_extension: true`, matching nearby Tenn task-card patterns.
- `rg` returning exit code `1` with no output for the production routing import check means no matching import string was found.
- Embedding/vector/RAG architecture invariants are unaffected because the new module imports only Python standard library modules and is not wired into backend startup or routing.

## DATA_MISSING

- The exact final commit hash cannot be embedded into the same committed report without changing the commit hash again. The post-commit hash is recorded in the final assistant closeout.
- No live production ASX PDFs or production extraction outputs were inspected by design.
- No parser prototype behavior is proven by this task; this task defines only the artifact schema and validation helpers.

## Files Added Or Modified

- `docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
- `docs/asx_comparator_artifact_schema.md`
- `financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py`
- `financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py`
- `reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521/README.md`
- `reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521/diff-check.json` after final diff check

## Artifact Schema Summary

- Artifact type is fixed to `asx_comparator_artifact_v1`.
- Schema version is fixed to `1`.
- Artifact-level `canonical_write` must be literal `false`.
- Artifacts require document identity, ticker, document type, source reference or PDF path, source checksum or SHA256, parser identity/version, generated timestamp, period metadata, currency/scale, tables, metric candidates, unsupported metric candidates, abstain reasons, warnings, provenance, and validation summary.
- The helper function `stable_artifact_checksum()` produces a deterministic SHA256 over canonical JSON, excluding self-checksum fields.

## Metric Candidate Schema Summary

- Metric candidates carry metric name, raw/candidate/normalized values, unit, currency, scale, period, table/page/row/column evidence, line item, evidence text, confidence, status, `canonical_write=false`, abstain reasons, and warnings.
- Supported statuses are `candidate`, `review_only`, `abstain`, and `unsupported`.
- Non-abstain metric candidates must include table, page, row, column, and evidence text.
- Abstain candidates may omit table/page/row/column evidence but must include `abstain_reasons`.

## Unsupported Metric Policy

- EPS, NTA, dividends, EBITDA, and total debt are review-only metrics in this schema.
- Any entry under `unsupported_metric_candidates` must use `status=review_only` or `status=unsupported`.
- Unsupported metrics must never validate as `status=candidate`.
- Appendix 4D/4E artifacts may include EPS, NTA, and dividends only as `review_only` or `unsupported`.

## Abstain Policy

- Missing, ambiguous, conflicting, or unsupported evidence should use `status=abstain`.
- Abstain candidates do not need page/table/row/column evidence.
- Abstain candidates must include an explicit abstain reason.

## `canonical_write=false` Confirmation

- `build_comparator_artifact()` always sets artifact-level `canonical_write` to `false`.
- `validate_comparator_artifact()` rejects artifact-level `canonical_write=true`.
- `validate_metric_candidate()` rejects metric-level `canonical_write=true`.
- `assert_no_canonical_write()` checks artifact, `metric_candidates`, and `unsupported_metric_candidates`.
- No canonical write path exists in the new module.

## Production-Boundary Import Check

- Checked files:
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
  - `financial-engine_v2/backend/app/services/pipeline.py`
  - `financial-engine_v2/backend/app/services/docling_extract.py`
- Command: `rg -n "asx_comparator_artifact_schema" financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/app/services/method_isolated_extraction.py financial-engine_v2/backend/app/services/pipeline.py financial-engine_v2/backend/app/services/docling_extract.py`
- Result: exit code `1`, no output, meaning no import/reference was found.
- Parser routing imports schema: no.

## Validation Commands And Exact Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
  - Result: `ok: true`, `issues: []`.
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
  - Initial result before claim: `active_jobs: []`, `ok: true`.
  - Later result while claimed: active self job plus non-overlapping Strategy Lab Evaluation job, `ok: true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md --repo-root /home/l4nd0/tenn-runtime`
  - Result: `ok: true`, `issues: []`.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md --repo-root /home/l4nd0/tenn-runtime`
  - Result: `ok: true`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
  - Final result: `13 passed, 1 warning in 0.05s`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
  - Final result: `29 passed, 1 warning in 0.24s`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
  - Final result: `42 passed, 1 warning in 0.28s`.
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py`
  - Result: compiled both files successfully.
- `git diff --check`
  - Result: exit code `0`, no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
  - Result: `ok: true`, `issues: []`, `disallowed_files: []`.
  - Changed files covered by the diff gate: task card, schema doc, schema module, schema tests, report README, and report `diff-check.json`.

## Canonical Writes Possible

- No. The schema module is pure standard-library validation/build logic and contains no persistence, routing, extraction, DB, Qdrant, memory, news, runtime, or canonical truth writes.

## What This Enables Next

- Future deterministic Appendix 5B, Appendix 4C, Appendix 4D, Appendix 4E, annual, half-year, and external table comparator prototypes can target one report-only artifact shape.
- Future parser prototypes can be evaluated for evidence quality, abstention behavior, unsupported metric handling, and production-boundary isolation before any routing work is proposed.

## What Remains Blocked

- Parser routing remains blocked.
- Extraction behavior changes remain blocked.
- Canonical financial truth writes remain blocked.
- Gold-label and scorecard updates remain blocked.
- Production ASX data runs remain blocked.

## Final Git Status

- At report write before final staging/commit: four intent-to-add files were visible:
  - `A docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
  - `A docs/asx_comparator_artifact_schema.md`
  - `A financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py`
  - `A financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py`
- Final post-commit status is recorded in the final assistant closeout.

## Registry Release Status

- At report write: claimed and active.
- Final release status is recorded in the final assistant closeout.

## Commit Hash If Committed

- DATA_MISSING in this committed report for self-reference reasons. The final assistant closeout records the post-commit hash.

## Project Memory Save Recommendation

- Save that the ASX comparator artifact schema v1 is a report-only, standard-library schema on the Financial Truth lane with `canonical_write=false`, no production routing imports, and tests covering Appendix 5B/4C cash-flow metric blocks plus Appendix 4D/4E review-only EPS/NTA/dividend policy.
