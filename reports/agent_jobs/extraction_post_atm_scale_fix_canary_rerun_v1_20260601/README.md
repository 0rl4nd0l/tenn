# Extraction Post ATM Scale Fix Canary Rerun

Task card: `docs/agent_tasks/extraction_post_atm_scale_fix_canary_rerun_v1_20260601.md`

Lane: Financial Truth

Mode: SAFE EXTENSION with bounded runtime side effects.

## Scope

This run submitted exactly seven approved documents, one at a time, through:

`POST /api/process/document/{document_id}`

No broad backfill, `/process/ticker`, direct Celery enqueue, direct SQL mutation,
source PDF mutation, parser/prompt/schema migration, Qdrant/news/memory write,
Cockpit UI edit, or GitHub mutation was performed.

## Runtime Result

All seven approved runtime extractions reached accepted terminal statuses:

| Ticker | Document ID | Run ID | Status |
| --- | --- | --- | --- |
| AAU | `508fc892-ae88-45ec-981f-cd9e124c8375` | `02996be7-e14f-4477-b5f2-600f4c8c419d` | `ok_low_confidence` |
| ATM | `96e9aabd-44dc-4c2c-be8c-74248a0a9025` | `0bf92b5f-18ab-477d-8f98-57f9f30105b8` | `ok_low_confidence` |
| AM5 | `aacc4c29-3089-48cf-8b82-8004134f9387` | `45dd9912-bada-4f60-a0b6-78c9c85ec12c` | `ok` |
| AQX | `0ed0104f-f29a-4068-8ff7-370f14fead98` | `d4e10582-95a9-4e9e-b2b6-c7b2b689bf75` | `ok` |
| CRS | `b43a16fb-7660-4bf7-96ab-0db641cd4032` | `0b1eb004-91ca-4d89-a69b-5600f4add463` | `ok` |
| CLV | `da9f9ea5-6596-464f-af14-5acf12f9b050` | `dc170bd5-5f28-43f4-9b22-63ee710786e5` | `ok` |
| CTM | `035c6758-7aed-41a6-9e84-ad154125d431` | `cb5a9d0c-c58a-477b-bda6-87adc83f391e` | `ok` |

## Scorecard Result

The exported actual payloads rekeyed to the reviewed real-gold fixture IDs and
the seven-fixture scorecard passed:

- Trusted fixtures: 7/7
- Metric expectations: 42/42 correct
- Quarantined: 0
- Wrong: 0
- Missing: 0
- Abstain: 0

ATM now scores as trusted with `scale=millions` and raw IDR metrics, including
revenue `84642439000000`, NP attributable `7208834000000`, and operating cash
flow `4853256000000`.

## Shutdown Result

Dedicated runtime units were stopped after scoring. Shutdown evidence shows
the worker/backend/router units inactive, ports `:8000` and `:8001` closed,
GPU-exclusive activity inactive, GPU guard exit `0`, and Tesla M40 memory at
`0 / 24576 MiB`.

## Boundary

This proves the bounded source-reviewed seven-document canary after the ATM
scale fix. It is not broad ticker-universe extraction graduation.
