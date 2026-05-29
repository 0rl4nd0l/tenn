# Extraction Gold Source Path Resolution V1

## Summary

The real-gold eval corpus source-file check now uses the existing allowlisted
ASX source resolver instead of checking only `PROJECT_ROOT / source_file`.

This removes the false missing-source signal for the 10X Appendix 5B fixture:
the fixture path is `data/asx/docs/10X/...`, while the source PDF is available
on this host at `/data/asx/docs/10X/...`.

## Change

`financial-engine_v2/backend/tests/test_extraction_gold_eval.py` now imports
`resolve_confirmed_metric_coverage_source_path()` from
`app.services.confirmed_metric_coverage_review` and uses it for real-gold
corpus source-file assertions.

The resolver still enforces local PDF paths under the ASX docs allowlist, so
genuinely missing or out-of-allowlist source files remain visible failures.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md --repo-root .`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval.py -q`
  - Result: `25 passed, 5 warnings`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`

## Non-Actions

No source PDFs were copied, moved, symlinked, edited, or staged. No extraction,
canary, backfill, production DB write, direct SQL mutation, Qdrant/news/memory
mutation, parser route change, prompt change, schema change, runtime/model/GPU/
service change, Cockpit UI change, or GitHub mutation was performed.

## Remaining Blockers

The #96 AAU runtime reload and AAU-only canary remains approval-gated by the
separate packet. The exact required phrase is:

`APPROVE #96 RUNTIME RELOAD AND AAU CANARY extraction_aau_runtime_reload_canary_approval_packet_v1_20260529`
