# Extraction Canary Actual Payload Exporter

## Outcome

Implemented a read-only exporter from explicit `extraction_runs` rows to the
actual-payload JSON map consumed by the confirmed-metric payload scorecard.

The helper is:

```bash
python scripts/export_extraction_run_actual_payloads.py \
  --db-path /data/fe_local.db \
  --run-id <run_uuid> \
  --out-json <actuals.json> \
  --summary-json <summary.json>
```

It requires explicit run or document selectors, reads SQLite in read-only mode,
allows only accepted statuses by default (`ok`, `ok_low_confidence`), validates
`structured_json.metrics`, and writes provenance/boundary metadata into the
summary and payload records.

## Canary Export Probe

The seven accepted canary runs were exported from `/data/fe_local.db`:

- AAU `14616c70-ba40-4398-bd63-23fa1508a190`
- ATM `74442c2b-3ce4-45b9-8eed-1581d1fa319e`
- AM5 `c1c5fd5e-39f9-4efe-8534-e4d839558445`
- AQX `9aa658d6-c8db-4376-9698-cb33f05172f4`
- CRS `44a86108-eab0-4b41-911e-545a4d7682c5`
- CLV `ecdfbcf1-273a-417c-84ae-a92a1360ad70`
- CTM `233900e7-1683-4ff4-bded-abb68824c0e3`

The export summary reports seven payloads, zero export errors, and no DB or
canonical-truth mutation.

## Scorecard Probe

The exported actuals were passed to:

```bash
python scripts/extraction_gold_eval_scorecard.py \
  --profile confirmed_metric_payload \
  --actuals-json reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_actual_payloads.json \
  --include-pre-persistence-gate \
  --out-json reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_payload_scorecard_probe.json
```

The scorecard accepted the JSON shape and correctly failed the gate because the
seven canary document ids are unmatched by the current confirmed-metric fixture
scope. This is the desired fail-closed behavior: accepted canary runtime output
is now reviewable actual-payload evidence, but it is not gold truth and does not
prove extraction graduation.

## Validation

- `financial-engine_v2/.venv/bin/python -m pytest scripts/test_export_extraction_run_actual_payloads.py -q` -> `5 passed`
- `financial-engine_v2/.venv/bin/python -m ruff check scripts/export_extraction_run_actual_payloads.py scripts/test_export_extraction_run_actual_payloads.py` -> pass
- `python3 -m py_compile scripts/export_extraction_run_actual_payloads.py scripts/test_export_extraction_run_actual_payloads.py` -> pass
- JSON validation for `canary_actual_payloads.json`, `canary_actual_payloads_summary.json`, `canary_payload_scorecard_probe.json`, and `function_quality_findings.json` -> pass

## Scope Boundary

This slice did not run extraction, start runtime services, mutate SQLite, create
gold labels, update source PDFs, change prompts, change schemas, touch Qdrant,
touch memory stores, touch Cockpit UI, or mutate GitHub state.

Next safe step: create a source-review task for the seven accepted canary
documents so selected metrics can become confirmed fixtures, then rerun the
payload gate against those source-reviewed labels.
