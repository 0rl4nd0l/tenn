# Extraction Third Canary Worker Env Retry V1

Status: bounded hard stop after CLV.

## Why This Retry Ran

The prior runtime card stopped on AAU because the dedicated `llm_gpu` worker did
not have `OLLAMA_URL` set. `generate_json()` loads the model-routing config, and
that config includes `embedding_provider: ollama`; without `OLLAMA_URL`, config
load failed before extraction could call llama.cpp.

This retry restarted only the dedicated worker with:

- `OLLAMA_URL=http://127.0.0.1:11434`
- `EMBEDDING_URL=http://127.0.0.1:11434`
- `LLAMACPP_URL=http://127.0.0.1:8001`
- `LLM_URL=http://127.0.0.1:8001`
- `EXTRACT_MODEL=qwen2.5-14b-instruct`

`runtime_restart.json` proves the worker process had those env values and that
the routing config resolved extraction to llama.cpp `:8001`.

## Preflight

Fresh preflight passed before retry submission:

- backend health: `ok`
- `llm_gpu` queue depth: `0`
- GPU process guard: exit `0`
- loaded router model: `model:qwen2.5-14b-instruct`
- worker ping: `pong`
- all seven approved source paths existed
- all seven approved document rows existed exactly once
- no approved document had an active queued/running run status

See `preflight.json` and `queue_before.json`.

## Result Summary

| Order | Ticker | Run ID | Status | Rows written |
| --- | --- | --- | --- | --- |
| 1 | AAU | `14616c70-ba40-4398-bd63-23fa1508a190` | `ok_low_confidence` | 1 |
| 2 | ATM | `74442c2b-3ce4-45b9-8eed-1581d1fa319e` | `ok_low_confidence` | 1 |
| 3 | AM5 | `c1c5fd5e-39f9-4efe-8534-e4d839558445` | `ok` | 1 |
| 4 | AQX | `9aa658d6-c8db-4376-9698-cb33f05172f4` | `ok` | 1 |
| 5 | CRS | `44a86108-eab0-4b41-911e-545a4d7682c5` | `ok_low_confidence` | 1 |
| 6 | CLV | `45b9c846-9f00-44ca-b8c6-7833f80e6342` | `failed` | 0 |
| 7 | CTM | not submitted | not submitted | 0 |

The retry stopped correctly at CLV and did not submit CTM.

## CLV Failure

CLV failed with:

`validation_gate:insufficient_metrics:0`

Observed details:

- Parser: `docling_gpu`
- Page count: `4`
- Table count: `0`
- Pass 4 merged payload: `{}`
- Gate: `status=failed`, `confidence=0.000`, `non_null_metrics=0`
- Financial rows written: `0`
- Risk note written: `1`

This is a real extraction/source-document blocker, not the earlier worker env
blocker.

## Harness Note

The first retry driver briefly marked AQX as failed because it treated an
intermediate `summary.status=succeeded` at `document_load` as terminal before
`final_summary` existed. A direct run-status check showed AQX was still running.
The resumed driver used final-summary-only terminal handling and continued on
the existing AQX run without resubmitting AQX.

## Cleanup

After CLV hard-stopped:

- `llm_gpu` queue depth was `0`.
- Worker active/reserved/scheduled inspection showed no active extraction task.
- Canary-specific worker, backend, and llama router units were stopped.
- Tesla M40 memory returned to `0 / 24576 MiB`.
- Stale `/tmp/llama-server.lock` for stopped router PID `3846184` was removed.

See `queue_after.json`.

## Next Safe Step

Diagnose the CLV zero-metric/source-document class blocker before rerunning CTM
or claiming extraction works across all tickers. The successful five-document
retry is useful graduation evidence, but it is not a full canary pass.
