# WHC Openability Runtime Endpoint Rerun

State: DONE_WITH_RISK

This report probes local extraction runtime endpoints and reruns the exact WHC
openability selected-table replay only if a live endpoint is already available.

No service starts, persistent runtime config edits, broad extraction, backfill,
DB/Qdrant/Redis/news/memory/source-PDF mutation, prompt/gold/schema/model/GPU
mutation, or PR #318 patch mining are allowed.

## Endpoint Probe

- Live: `http://127.0.0.1:11434/api/tags`
- Live: `http://127.0.0.1:11434/v1/models`
- Available models included `qwen2.5:32b` and `nomic-embed-text:latest`.
- `127.0.0.1:8080` and `127.0.0.1:8081` were not listening.

## Replay Result

The exact WHC replay was rerun with process-local overrides only:

- `OLLAMA_URL=http://127.0.0.1:11434`
- `EXTRACTION_LLAMACPP_URL=http://127.0.0.1:11434`
- `EXTRACT_MODEL=qwen2.5:32b`
- `DATA_ROOT=/tmp/tenn_whc_openability_runtime_endpoint_rerun_data_*`

The replay reached Pass 3a and produced 9 non-null metrics, but final validation
failed:

`validation_gate:missing_period_end`

## Metrics Observed

- revenue: `4,920,102,000`
- ebit: `2,765,893,000`
- np_attributable: `1,951,965,000`
- operating_cf: `2,529,823,000`
- investing_cf: `-177,195,000`
- financing_cf: `-1,232,370,000`
- capex: `-124,210,000`
- cash_end: `1,215,460,000`
- net_debt: `-970,763,000`

These were not accepted because `period_end` remained null.

## Next Repair

The next bounded fix is to bind exact source period-end evidence from
openability diagnostic period phrases into the existing period evidence path.
The evidence is already present in synthetic table captions, e.g.
`For the year ended 30 June 2022`.
