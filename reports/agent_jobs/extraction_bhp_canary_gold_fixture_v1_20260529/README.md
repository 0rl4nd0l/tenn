# Extraction BHP Canary Gold Fixture V1

## Summary

This task added a test-only BHP FY2025 real-document regression fixture for
issue #96. The fixture is source-backed and records the current-period BHP
annual values that must be trusted: revenue `51,262,000,000`, operating cash
flow `18,692,000,000`, and net debt `12,924,000,000`, all in native USD
millions with no FX conversion.

The observed #96 BHP canary payload is now covered as a negative regression:
it selected revenue `55,658,000,000`, so the eval harness classifies that
payload as `abstain` with `revenue:wrong` rather than trusted financial truth.

## Source Evidence

- Canary document id: `2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7`
- Source PDF:
  `/data/asx/docs/BHP/financial_performance/2025-08-19_bhp-appendix-4e-and-2025-annual-report_2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7.pdf`
- The source PDF SHA256 is
  `39e139174313295df56143a3cbd2c704eeb9783bdffb4706a083706d6b5a490a`.
- The existing curated BHP FY2025 real-gold PDF has the same SHA256, proving the
  canary document path and curated source are byte-identical.
- `pdftotext` verification found US$ million revenue `51,262`, net operating
  cash flows `18,692`, and net debt `12,924`.

See `source_verification.json` for the exact captured evidence summary.

## Files Changed

- `docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md`
- `financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/README.md`
- `reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/source_verification.json`
- `reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/status.json`
- `docs/claude/STATE.md`

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md --repo-root .`
- `python3 -m json.tool financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval.py -q -k 'not load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist'`
  - Result: `24 passed, 1 deselected`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Scorecard CLI smoke with a BHP-only actual payload via `/dev/stdin`; output
  was valid JSON and classified the BHP payload as trusted while other fixtures
  quarantined due missing actual context.

Known unrelated validation failure:

- Full `test_extraction_gold_eval.py` still fails on
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
  because the unchanged baseline is missing the existing 10X real-gold source
  path under `financial-engine_v2/data/asx/docs/10X/...`. This was reproduced
  on baseline `e2029835` and is not introduced by the BHP fixture.

## Non-Actions

No third canary was run. No BHP live extraction was run. No broad backfill,
direct SQL mutation, production DB write, Qdrant/news/memory mutation, source
PDF mutation, parser route change, prompt change, schema change, runtime/model/
GPU/service change, Cockpit UI change, or GitHub mutation was performed.

## Next Safe Step

The runtime reload plus AAU-only canary remains approval-gated by the separate
packet. The exact phrase needed before that operation is:

`APPROVE #96 RUNTIME RELOAD AND AAU CANARY extraction_aau_runtime_reload_canary_approval_packet_v1_20260529`
