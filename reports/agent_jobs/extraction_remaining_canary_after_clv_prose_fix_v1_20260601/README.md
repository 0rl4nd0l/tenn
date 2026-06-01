# Extraction Remaining Canary After CLV Prose Fix V1

Status: bounded hard stop on CTM.

## Scope

This runtime card submitted only the remaining approved documents after AAU,
ATM, AM5, AQX, and CRS were already accepted in the worker-env retry and after
the CLV prose-highlight code fix landed in `4b0acebe`.

Submitted documents:

1. CLV `da9f9ea5-6596-464f-af14-5acf12f9b050`
2. CTM `035c6758-7aed-41a6-9e84-ad154125d431`

Route: `POST /api/process/document/{document_id}`

## Preflight

Fresh preflight passed:

- backend health: `ok`
- `llm_gpu` queue depth: `0`
- GPU process guard: exit `0`
- loaded router model: `model:qwen2.5-14b-instruct`
- worker ping: `pong`
- worker `OLLAMA_URL=http://127.0.0.1:11434`
- CLV and CTM source paths existed
- CLV and CTM document rows existed exactly once
- no active queued/running run status for CLV or CTM

See `runtime_startup.json`, `preflight.json`, and `queue_before.json`.

## Results

| Order | Ticker | Run ID | Status | Rows written |
| --- | --- | --- | --- | --- |
| 1 | CLV | `ecdfbcf1-273a-417c-84ae-a92a1360ad70` | `ok` | 1 |
| 2 | CTM | `fbf2cf1d-3f9b-4c96-91d5-8a0a88862fc0` | `failed` | 0 |

CLV passed after the prose-highlights fix. Worker logs show Pass 4 merged:

`{'revenue': 44100000.0, 'np_attributable': 4200000.0, 'cash_end': 10300000.0}`

with gate status `ok`, confidence `0.720`, and `3` non-null metrics.

CTM failed with:

`validation_gate:period_source_mismatch:payload=H:source=A:year_ended_source_phrase`

The CTM source text explicitly says the directors present the report for the
year ended 31 December 2025, but Pass 1 classified the report as `H`.

## Cleanup

After the CTM hard stop:

- `llm_gpu` queue depth was `0`.
- Canary-specific backend, worker, and router units were stopped.
- Tesla M40 memory returned to `0 / 24576 MiB`.
- Stale `/tmp/llama-server.lock` for stopped router PID `3934188` was removed.

See `queue_after.json`.

## Next Safe Step

Add source-backed period-type correction for unambiguous explicit
`year ended` evidence, without weakening the period mismatch gate, then rerun
only CTM through the backend-owned single-document route.
