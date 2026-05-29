# Extraction BHP Real-Gold Source Path CI Portability

## Summary

- Job: `extraction_bhp_real_gold_source_path_ci_portability_v1_20260529`
- Related issue: #96
- PR: https://github.com/0rl4nd0l/tenn/pull/127
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`
- Mode: SAFE EXTENSION
- Runtime/canary/backfill run: no
- DB/Qdrant/news/memory/source-PDF mutation: no

PR #127 failed GitHub Actions on the real-gold corpus source-path test because
GitHub-hosted CI does not have the host-local `/data/asx/docs` source PDFs.
PR #128 already proved the same CI-portability shape removes this specific
extraction failure while leaving the unrelated broad CI failures visible.

## Change

`test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
was renamed to
`test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_source_paths`.
The test now:

- resolves every `source_file` through the allowlisted source resolver;
- catches only `FileNotFoundError` as environment `DATA_MISSING` in default CI
  mode;
- keeps malformed paths, disallowed paths, and permission failures uncaught;
- enforces actual source-file presence when
  `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py` (`25 passed, 5 warnings`)
- `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py` (`25 passed, 5 warnings`)
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`

## Remaining CI Context

PR #128 no longer has the extraction source-path failure and still fails broad
CI on unrelated Cockpit, marketplace, Redis, subprocess, query-orchestration,
and subagent tests. PR #127 has the same unrelated broad CI failures plus the
source-path failure addressed here; a new PR #127 CI run is needed after push to
confirm this branch also drops that extraction-specific failure.

## Files Changed

- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `docs/agent_tasks/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529.md`
- `reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/README.md`
- `reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/status.json`
- `reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/diff-check.json`
- `docs/claude/STATE.md`

## Next Safe Step

Commit and push this focused PR #127 fix, then recheck PR #127 Actions. Treat
remaining non-extraction failures as separate lane-owned work unless a new task
explicitly scopes them.
