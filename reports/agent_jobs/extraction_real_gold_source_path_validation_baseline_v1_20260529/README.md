# Real-Gold Source Path Validation Baseline

Job: `extraction_real_gold_source_path_validation_baseline_v1_20260529`

Branch: `safe/extraction-real-gold-source-path-validation-baseline-v1-20260529`

Worktree: `/home/l4nd0/tenn-extraction-real-gold-source-path-validation-baseline-v1-20260529`

Lane: Evaluation, supporting Financial Truth and Provenance.

## Summary

The baseline focused extraction regression set failed because
`test_extraction_gold_eval.py` required every real-gold corpus `source_file` to
exist under the repo-local `financial-engine_v2/data` tree. The 10X real-gold
fixture uses an ASX document path that resolves through the existing allowlisted
source resolver but is not always present in that repo-local tree.

The test now validates every real-gold corpus `source_file` through
`resolve_confirmed_metric_coverage_source_path()`. In default mode,
`FileNotFoundError` is treated as host-local source-asset absence only after the
resolver has validated the path as local, PDF-shaped, and within an allowed ASX
source root. Malformed, disallowed, non-PDF, remote, or non-local paths are not
caught and still fail the test. Strict openability remains available with
`TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md`:
  passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md --repo-root .`:
  passed in the isolated worktree.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md`:
  passed.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  passed.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  `24 passed, 5 warnings`.
- `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  `24 passed, 5 warnings`.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_multipass_extraction.py`:
  `226 passed, 5 warnings`.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.

## Boundaries

No runtime reload, canary run, broad backfill, production DB write, Qdrant/news
or memory mutation, source-PDF mutation, parser-routing change, extraction prompt
change, gold-label mutation, schema migration, GPU/model/service change, or
Cockpit UI work was performed.

The remaining third-canary gate is runtime approval and execution, not this
test portability fix.
