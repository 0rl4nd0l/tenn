# Extraction Real-Gold Source Path CI Portability V1

## Summary

Made the real-gold corpus source-path test portable for GitHub-hosted CI without
dropping strict local source-asset validation.

The PR #127 `lint-and-test` run showed the relevant extraction failure:

`FAILED financial-engine_v2/backend/tests/test_extraction_gold_eval.py::test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist - FileNotFoundError: DATA_MISSING: source PDF not found`

That failure happens because GitHub Actions does not have host-mounted
`/data/asx/docs` source PDFs. The test now separates:

- source-path safety and allowlist validation, which always runs; from
- source-file openability, which is required only when
  `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Implemented

- Renamed the corpus test to
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_source_paths`.
- Imported `os` and added `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS`.
- Default mode:
  - loads the real-gold corpus;
  - preserves the operating-cash-flow alias regression;
  - resolves each `source_file` through the existing allowlisted resolver;
  - records resolver `FileNotFoundError` as environment `DATA_MISSING`.
- Strict mode:
  - fails if any corpus source file is missing from the allowlisted source
    roots.

The test still does not catch `ValueError` or `PermissionError`, so malformed,
remote, non-PDF, or outside-allowlist paths continue to fail.

## Boundaries

- No runtime reload, extraction, canary, or backfill.
- No production DB, direct SQL, Qdrant, news, memory, source-PDF, or
  canonical-truth mutation.
- No parser-routing, extraction-prompt, schema, runtime/model/GPU/service, or
  Cockpit UI change.
- No GitHub issue comment, close, label, milestone, or body mutation.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - `24 passed, 5 warnings`
- `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - `24 passed, 5 warnings`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - passed

## Remaining Notes

PR #128 still needs GitHub Actions to rerun after this branch update. PR #127
has many unrelated broad-suite failures in the same CI run; the relevant
extraction source-path failure is addressed here and can be propagated to the
BHP branch if needed before merge.
