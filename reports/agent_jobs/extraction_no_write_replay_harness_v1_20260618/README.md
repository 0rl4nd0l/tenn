# Certified No-Write Extraction Replay Harness

State: DONE_WITH_RISK

Implemented a repo-native certified no-write replay command:

```bash
python3 scripts/extraction_no_write_replay.py \
  --case all \
  --case-manifest financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json \
  --report-dir reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay
```

The runner accepts only certified manifest cases, requires loopback LLM URLs,
uses a disposable `/tmp/tenn-extraction-no-write-replay-*` `DATA_ROOT`, writes
durable outputs only under the selected report directory, and records before
and after side-effect evidence.
The disposable runtime root also owns `HOME`, `TMPDIR`, `XDG_CACHE_HOME`,
`XDG_CONFIG_HOME`, and `XDG_STATE_HOME` for the replay process.

## Validation Result

No-write safety validation passed.

Full six-case replay status is `FAIL` because the current WHC case did not meet
its source-period expectation:

- WHC: `failed`,
  `validation_gate:period_end_source_mismatch:payload=2022-09-21:source=2022-06-30:year_ended_explicit_date`
- CTN: `ok`, `Q`, `2022-03-31`
- HUB: `ok`, `H`, `2023-12-31`
- LBL: `ok`, `H`, `2025-12-31`
- AZJ: `ok`, `A`, `2025-06-30`
- NSR: `ok`, `H`, `2021-12-31`

Side-effect audit from the full run:

- `forbidden_surface_clean=true`
- `report_only_durable_writes=true`
- `isolated_cache_contained=true`
- `isolated_runtime_contained=true`
- `source_pdf_write=false`
- `normal_parser_cache_write=false`
- `db_write=false`
- `qdrant_write=false`
- `redis_write=false`
- `news_write=false`
- `registry_write=false`
- `github_mutation=false`

The full run used an ephemeral validation environment with PyMuPDF available.
`docling` was not installed in that ephemeral environment, so non-WHC parser
runs used the existing PyMuPDF fallback. WHC is explicitly configured for the
known PyMuPDF/openability replay path.

## Files Added

- `scripts/extraction_no_write_replay.py`
- `scripts/test_extraction_no_write_replay.py`
- `financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json`
- `docs/agent_tasks/extraction_no_write_replay_harness_v1_20260618.md`
- `reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/`

## Unsafe Actions Avoided

No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, registry,
runtime config, service, GitHub, broad extraction, count sample, backfill, or
production data mutation was performed.

## Remaining Risk

The runner is safe to use for certified no-write replay evidence, but the
six-case corpus is not extraction-green on current canonical code because WHC
still fails the source-period gate in this execution path. Do not treat the
full corpus as a passing extraction quality gate until WHC is fixed or the
manifest is intentionally reclassified.
