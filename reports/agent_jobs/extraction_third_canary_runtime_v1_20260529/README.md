# Extraction Third Canary Runtime V1

## Summary

- Related issue: #96
- Approval source: `APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`
- Worktree: `/home/l4nd0/tenn-extraction-third-canary-runtime-v1-20260529`
- Branch: `runtime/extraction-third-canary-runtime-v1-20260529`
- HEAD: `d55a515376e2bd065be9c94843d07ccca06f99f2`
- Execution route used: `POST /api/process/document/{document_id}`
- Broad backfill run: no
- Direct SQL mutation run: no
- Unapproved documents submitted: none

The approved canary was started one document at a time and stopped after the
first document reached a terminal failed extraction status, as required by the
task card.

## Result

| Order | Ticker | Document ID | Run ID | Status | Error |
| --- | --- | --- | --- | --- | --- |
| 1 | AAU | `508fc892-ae88-45ec-981f-cd9e124c8375` | `523e018f-d342-4d1d-b239-8e92ecc4c5ce` | `failed` | `validation_gate:missing_period_end` |

Documents 2-7 (`ATM`, `AM5`, `AQX`, `CRS`, `CLV`, `CTM`) were not submitted.

## Runtime Evidence

- Backend `/api/health`: `ok`
- Celery active/reserved/scheduled before run: empty
- Celery active/reserved/scheduled after abort: empty
- `scripts/gpu_process_guard.sh --check`: exit `0`
- GPU telemetry caveat: `nvidia-smi` returned device-handle errors, so detailed VRAM/process telemetry remains `DATA_MISSING`
- llama.cpp health: `ok`
- API auth note: live backend has no configured `LOCAL_API_KEY`; the local `require_api_key` dependency permits the route without `X-API-Key`

## Side-Effect Audit

- New submitted run: `523e018f-d342-4d1d-b239-8e92ecc4c5ce`
- Financial rows written for AAU: `0`
- Qdrant points for AAU after run: `0`
- Source PDF or same-document sidecar mutation detected: none
- Broad queue orphan detected after abort: none observed through Celery inspect

The failed AAU run persisted an `extraction_runs` row with
`status=failed`, `error=validation_gate:missing_period_end`, and the actual
payload captured in `canary_actual_payloads.json`.

## Artifacts

- `canary_results.json`: preflight, run status, side-effect audit, and abort reason
- `canary_actual_payloads.json`: actual persisted structured payload for the submitted run
- `status.json`: compact runtime status summary

## Next Safe Step

Treat #96 third-canary execution as stopped on AAU. Before any rerun, inspect
why AAU's reconciled payload lacks a persisted period end and decide whether the
period-end validation/extraction path needs a targeted fix. Do not resume the
remaining six canary documents until that blocker is understood.
