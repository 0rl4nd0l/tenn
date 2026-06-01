# Extraction CTM Canary Rerun After Period Fix V1

Status: bounded hard stop on CTM.

## Scope

This runtime card submitted only CTM document
`035c6758-7aed-41a6-9e84-ad154125d431` after the source-backed period-type
code fix landed in `07f20ff3`.

Route: `POST /api/process/document/{document_id}`

Run ID: `fbd99043-fd40-46f3-beaa-847e8348060c`

Task ID: `c117c8f1-34f3-40cb-84b7-a8a0cf3ada0f`

## Preflight

Fresh preflight passed:

- backend health: `ok`
- `llm_gpu` queue depth: `0`
- GPU process guard: exit `0`
- worker ping: `pong`
- worker `OLLAMA_URL=http://127.0.0.1:11434`
- live HEAD: `07f20ff3`
- CTM source path existed
- CTM document row existed exactly once
- no active queued/running run status for CTM

See `runtime_startup.json`, `preflight.json`, and `queue_before.json`.

## Result

CTM hard-failed again:

`validation_gate:period_source_mismatch:payload=H:source=A:year_ended_source_phrase`

Runtime evidence from `extraction_runs.structured_json` showed:

- `source_period_evidence.reason = year_ended_source_phrase`
- `source_period_end_evidence.reason = not_detected`
- `source_period_end_evidence.period_end = null`
- no `source_period_type_correction` was recorded

The source text contains the phrasing `during, the year ended 31 December 2025`.
The first correction accepted `year ended <date>` and `for the year ended <date>`
but not `the year ended <date>`, so the explicit typed date evidence was not
detected.

## Cleanup

After the hard stop:

- canary backend, worker, and router units were stopped;
- backend health returned connection refused as expected after cleanup;
- Tesla M40 memory returned to `0 / 24576 MiB`;
- stale `/tmp/llama-server.lock` for stopped router PID `3991961` was removed.

See `queue_after.json`.

## Next Safe Step

Patch `_SOURCE_PERIOD_END_PATTERNS` to accept explicit `the year ended
<date>` wording without accepting loose dates, then run focused detector and
multipass regressions before a second CTM-only runtime rerun.

