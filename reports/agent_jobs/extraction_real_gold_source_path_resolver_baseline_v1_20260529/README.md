# Extraction Real-Gold Source Path Resolver Baseline V1

## Summary

Fixed the baseline real-gold eval source-asset check so it uses the existing
allowlisted ASX source resolver instead of only checking
`financial-engine_v2/data/asx/docs`.

This removes the current full `test_extraction_gold_eval.py` failure for the
10X Appendix 5B source PDF that exists under `/data/asx/docs`.

## Scope

- Lane: Evaluation.
- Supporting lanes: Provenance and Financial Truth.
- Branch: `safe/extraction-real-gold-source-path-resolver-v1-20260529`.
- Worktree:
  `/home/l4nd0/tenn-extraction-real-gold-source-path-resolver-v1-20260529`.
- Runtime extraction run: no.
- Third canary run: no.
- Broad backfill run: no.
- DB/Qdrant/news/memory/canonical truth mutation: no.
- Source PDF copy/edit/symlink/staging: no.
- Parser routing, prompt, schema, runtime/model/GPU/service, and Cockpit UI
  changes: no.

## Implemented

- `test_extraction_gold_eval.py` imports
  `resolve_confirmed_metric_coverage_source_path`.
- The real-gold corpus source-file assertion now verifies that the allowlisted
  resolver can resolve each corpus source PDF to an actual file.
- The assertion remains strict: missing or disallowed source paths still fail.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md --repo-root .`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - `24 passed, 5 warnings`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `git diff --check`
- Task-card `check-diff`: passed with no disallowed files.
- Diff review: no critical, warning, or suggestion findings after preserving
  the old source-file assertion message.
- Source/binary staging scan: no PDF, image, database, parquet, or
  `data/asx/docs` paths in the diff.

## Remaining Blockers

- BHP canary fixture branch remains in draft PR
  https://github.com/0rl4nd0l/tenn/pull/127.
- Any AAU/runtime canary continuation still requires exact approval:
  `APPROVE #96 RUNTIME RELOAD AND AAU CANARY extraction_aau_runtime_reload_canary_approval_packet_v1_20260529`.
- Full accurate extraction graduation still requires the approved runtime canary,
  post-run #97 scorecard gates, and broader accuracy evidence.
