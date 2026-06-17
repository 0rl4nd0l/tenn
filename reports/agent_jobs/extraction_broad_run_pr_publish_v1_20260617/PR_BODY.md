## Summary

Surfaces broad-run row-level extraction provenance and machine-readable accepted-output scale/magnitude risk flags.

This branch adds:

- per-metric broad-run provenance fields, including row/source/page/table/scale evidence where available
- accepted-output scale and magnitude risk flags for review-only visibility
- summary rollups for provenance coverage and risk flag distribution
- focused unit coverage for provenance, risk flags, and summary aggregation
- two no-extraction report fixtures: one saved LBL accepted-output replay and one exact positive synthetic risk case

## Validation

- `python3 scripts/agent_job_contract.py validate ...` for all task cards
- `python3 scripts/agent_job_contract.py check-report-artifacts ...` for all report bundles
- `python3 scripts/agent_job_contract.py check-diff ...`
- `git diff --check origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD`
- `PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/scripts/broad_extraction_test.py financial-engine_v2/scripts/test_broad_extraction_test.py`
- `PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q`

## Boundaries

- No canonical writes
- No count-24 or count-32
- No broad extraction or broad backfill
- No full ticker-universe extraction
- No runtime service start
- No DB/Qdrant/Redis/news/memory/source-PDF/prompt/gold/schema/model/GPU/service mutation
- PR #318 was not used
