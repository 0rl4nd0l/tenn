# ASX Document-Type Pure Classifier v1 Report

## Confirmed Facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Starting HEAD: `d1a700d3066b`.
- Starting worktree dirt: clean before task-card creation.
- Task card validated successfully.
- Registry overlap check was clean before claim.
- Registry claim succeeded for `asx_document_type_pure_classifier_v1_20260520`.
- A later `list-active` showed this job plus an unrelated Evaluation audit job, `strategy_lab_quantdinger_fit_audit_v1_20260520`; no parser, extraction, fixture, or Financial Truth overlap was present.
- Production data access was not used.
- No extraction, Docling, OCR, comparator, Qdrant, news, memory, Cockpit, Home, runtime/model/GPU, parser-routing, gold-label, or canonical scorecard jobs were run.

## Inferred Facts

- The fixture contract expects classification from short synthetic `source_text_surrogate` dictionaries only.
- Explicit Appendix form labels are the strongest document-type anchors.
- Conflicting high-confidence Appendix form labels should abstain instead of choosing a likely type.
- Appendix 4C and Appendix 5B classifications are cash-flow metadata only and cannot authorize income-statement metric inference.
- Appendix 4D and Appendix 4E references to EPS, NTA, or dividends remain review-only unsupported context.

## DATA_MISSING

- Final commit hash cannot be embedded in the committed copy of this report without changing the commit hash again. The final response records the post-commit hash.
- Direct persistent-environment rerun of `python3 -m compileall ...` is blocked by a pre-existing root-owned ignored cache directory at `financial-engine_v2/backend/app/services/__pycache__`. The exact compile command passed after temporarily moving that ignored cache out of the way and restoring it afterward.

## Files Added/Modified

- Added `docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`.
- Added `financial-engine_v2/backend/app/services/asx_document_type_classifier.py`.
- Added `financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`.
- Added `reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/README.md`.
- Generated `reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/diff-check.json`.
- No fixture JSON files were modified.
- No production extraction routing files were modified.

## Classifier Design Summary

- Standard-library-only Python module.
- Pure function entrypoint: `classify_asx_document_type(source_text_surrogate)`.
- Returns `AsxDocumentTypeClassification`, a frozen dataclass with `to_dict()`.
- Result fields include `document_type`, `confidence_band`, `expected_abstain`, `abstain`, `canonical_write`, `positive_evidence`, `negative_evidence`, `abstain_reasons`, and `warnings`.
- Evidence is deterministic anchor evidence from normalized surrogate text.
- `canonical_write` is hard-coded to `False` in all result constructors.

## Supported Document Types

- `annual_report`
- `half_year_report`
- `appendix_4c`
- `appendix_4d`
- `appendix_4e`
- `appendix_5b`
- `other_asx_announcement`
- `unknown_or_abstain`

## Abstain Logic

- Abstains on empty or unsupported surrogate inputs.
- Abstains on low-signal inputs with no supported report or Appendix anchor.
- Abstains when multiple supported Appendix form labels fire.
- Abstains instead of guessing when high-confidence non-Appendix report anchors conflict.
- Ambiguous Appendix 4D/4E fixture returns `unknown_or_abstain`.
- Unknown low-signal fixture returns `unknown_or_abstain`.

## Safety Boundary Confirmation

- Production routing imports classifier: no.
- `canonical_write` is always false: yes.
- Fixture contract tests still pass: yes.
- Classifier imports forbidden backend/runtime packages: no.
- Parser routing changed: no.
- Extraction behavior changed: no.
- Canonical writes, DBs, Qdrant, memory, news, Cockpit, Home, runtime/model/GPU config changed: no.

## Validation Commands And Exact Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`
  - Result: passed, `ok=true`, no issues.
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
  - Initial result: passed, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`
  - Result: passed, `ok=true`, no issues.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`
  - Result: passed, active record created.
- `for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done`
  - Result: passed.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
  - Result: `9 passed, 1 warning in 0.02s`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
  - Result: `9 passed, 1 warning in 0.03s`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
  - Result: `18 passed, 1 warning in 0.05s`.
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`
  - First direct result: failed with `PermissionError` writing under pre-existing root-owned ignored `financial-engine_v2/backend/app/services/__pycache__`.
  - Equivalent cache-redirect syntax check: passed with `PYTHONPYCACHEPREFIX=reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/pycache`; generated cache files were removed.
  - Exact command after temporary ignored-cache isolation and restoration: passed, output included `Compiling 'financial-engine_v2/backend/app/services/asx_document_type_classifier.py'...`.
- `git diff --check`
  - Result: passed, no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`
  - Initial result after report write: passed, `ok=true`, no disallowed files.
  - Final result is captured in `reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/diff-check.json`.

Pytest warning in all pytest runs:

- `PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope`

## Production Routing Import Check

- Checked:
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
  - `financial-engine_v2/backend/app/services/pipeline.py`
- Result: no `asx_document_type_classifier` import or reference found.

## Final Git Status

- Pre-commit report-time `git status --short`:
  - `?? docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`
  - `?? financial-engine_v2/backend/app/services/asx_document_type_classifier.py`
  - `?? financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`
- Final post-commit status is recorded in the final response.

## Registry Release Status

- Report-time status: active claim held by this job.
- Final release is performed after commit and recorded in the final response.

## Commit Hash If Committed

- DATA_MISSING in committed report for self-reference reason above.
- Final response records the commit hash if the commit is created.

## Project Memory Save Recommendation

- Save a short Project Memory note that ASX document-type classification is now a pure metadata classifier with `canonical_write=false`, fixture-only tests, no production routing import, and no parser/extraction behavior changes.
