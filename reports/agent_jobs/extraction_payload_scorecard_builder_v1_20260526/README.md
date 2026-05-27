# Extraction Payload Scorecard Builder

Issue: #97

Lane: Evaluation
Supporting lanes: Financial Truth, Provenance
Mode: SAFE EXTENSION, report-local/eval-only
Risk: MEDIUM

## Session

- Worktree: `/home/l4nd0/tenn-extraction-payload-scorecard-builder-v1-20260526`
- Branch: `safe/extraction-payload-scorecard-builder-v1-20260526`
- Base HEAD: `3725591cf76ec1a56428a476e23dbd1ebc4050fc`
- Task card: `docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md`
- Registry: shared registry claim/release succeeded; final read-only list-active returned no active jobs.
- Collision handling: isolated worktree was created because the baseline checkout had unrelated untracked task-card dirt.

## What Changed

- Added `build_confirmed_metric_payload_scorecard()` in `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`.
- Added `PayloadScoreStatus` result classes:
  - `present_correct`
  - `missing_expected_metric`
  - `present_wrong_value`
  - `wrong_unit_currency_scale`
  - `wrong_period`
  - `missing_evidence`
  - `unsupported_correctly_abstained`
  - `ambiguous_quarantined`
  - `not_evaluated_no_actual_payload`
- Added focused synthetic unit coverage in `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`.
- Generated `payload_scorecard_sample.json` under this report directory from checked-in eval fixtures plus report-local synthetic actual payloads.

## Boundary

The builder consumes pre-supplied actual payload maps only. It does not run production extraction, mutate labels, write canonical financial truth, write DB/Qdrant/news/memory, move source PDFs, change parser routing, change prompts, or touch runtime/model/GPU/service config.

Source-PDF openability is emitted as `source_pdf_exists` and `source_pdf_summary`; it is explicitly not counted as extraction correctness.

## Generated Artifact

`payload_scorecard_sample.json` summary:

```json
{
  "artifact_type": "confirmed_metric_payload_scorecard_v1",
  "total_fixture_count": 15,
  "total_metric_expectations": 146,
  "scored_metric_expectations": 73,
  "result_class_summary": {
    "ambiguous_quarantined": 73,
    "missing_evidence": 0,
    "missing_expected_metric": 0,
    "not_evaluated_no_actual_payload": 55,
    "present_correct": 17,
    "present_wrong_value": 1,
    "unsupported_correctly_abstained": 0,
    "wrong_period": 0,
    "wrong_unit_currency_scale": 0
  },
  "source_pdf_summary": {
    "exists": 0,
    "missing": 15,
    "not_declared": 0
  }
}
```

The sample actual map is intentionally report-local and synthetic. It proves the builder path and schema; it is not a production extraction result or a broad accuracy claim.

## Confirmed

- #97 is advanced from audit-only blocker to an implemented report-local scorecard builder.
- Missing actual payloads are scored as `not_evaluated_no_actual_payload`, not pass.
- Source openability is separate from extraction correctness.
- Value mismatch, missing metric, wrong period, wrong unit/scale, missing evidence, unsupported abstain, and ambiguous quarantine behavior are covered by synthetic unit tests.
- `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` remain conceptually separate. The narrow core stays a no-regression baseline, not the final broad-metric product goal.

## Inferred

- This builder is the correct first #97 implementation step before any production extractor run because it provides the payload scoring contract without requiring live extraction.
- Once approved actual payloads exist, the same builder can score confirmed-coverage rows without reinterpreting labels or mutating canonical truth.

## Speculative

- The sample report's missing source-PDF counts may improve after #99 source asset metadata/resolver work; this task did not inspect or move source PDFs.

## DATA_MISSING

- Approved actual extracted payloads for all confirmed metric coverage expectations.
- Approved confirmed-coverage payload accuracy threshold.
- #98 contract parity for broader metric families such as `total_equity` and `interest_expense`.
- #99 durable source asset manifest/resolver for reviewable source-PDF evidence.
- Live broad extracted-payload accuracy across annual, half-year, 4D, and 4E filings.

## #98 / #99 Dependency

#98 and #99 are not required to use this builder with pre-supplied report-local actuals. They are required before broader use or promotion:

- #98 must align metric schema/contract support before scoring persisted-only or unsupported metric families.
- #99 must provide a durable metadata-only source asset manifest/resolver before source reviewability is considered complete.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md`: PASS.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: PASS before claim and after release.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md --repo-root .`: PASS.
- `python3 scripts/agent_job_registry.py claim ...`: PASS.
- `python3 scripts/agent_job_registry.py release extraction_payload_scorecard_builder_v1_20260526 --repo-root .`: PASS.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q`: PASS, `9 passed, 1 warning in 0.13s`.
- `uv run --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `python3 -m json.tool reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/payload_scorecard_sample.json`: PASS.
- `git diff --check`: PASS.

## Architecture Review

- `SYSTEM_CONTRACT.md`: compliant. This is evaluation/reporting code only and does not alter backend authority, extraction behavior, storage, retrieval, prompts, parser routing, model/runtime config, or canonical truth.
- `.cursor/rules/*`: DATA_MISSING in this checkout; the architecture-check skill expected these files, but they were absent.
- Code review: no critical/warning findings from the final diff review; residual risk is limited to future actual-payload schema variance.

## Files Changed

- `docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/README.md`
- `reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/status.json`
- `reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/payload_scorecard_sample.json`
- `reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/diff-check.json`

## Final Git Status

Pending final `check-diff` and commit at report write time. The working tree contains only allowlisted task files, code/test changes, and report artifacts for this job.

## Project Memory Recommendation

Save a memory note after final closeout: #97 now has a report-local confirmed metric extracted-payload builder; broader use still needs approved actual payloads, #98 contract parity, and #99 source asset resolver work before any accuracy promotion.
