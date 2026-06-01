# Extraction Third Canary Runtime Execution V1

Status: hard-stopped after the first approved document.

## Scope

Approved route: `POST /api/process/document/{document_id}`

Approved documents:

1. AAU `508fc892-ae88-45ec-981f-cd9e124c8375`
2. ATM `96e9aabd-44dc-4c2c-be8c-74248a0a9025`
3. AM5 `aacc4c29-3089-48cf-8b82-8004134f9387`
4. AQX `0ed0104f-f29a-4068-8ff7-370f14fead98`
5. CRS `b43a16fb-7660-4bf7-96ab-0db641cd4032`
6. CLV `da9f9ea5-6596-464f-af14-5acf12f9b050`
7. CTM `035c6758-7aed-41a6-9e84-ad154125d431`

## Runtime Evidence

- Backend health was reachable on `:8000`.
- llama.cpp router was active on `:8001` and had `model:qwen2.5-14b-instruct` loaded.
- Dedicated Celery worker `tenn-llm-gpu-canary@l4nd0-System-Product-Name` responded on `llm_gpu`.
- Approved source paths existed.
- Approved document rows existed exactly once.
- Pre-run `llm_gpu` queue depth was `0`.
- Tesla M40 memory after model load was `10547 / 24576 MiB`.

See:

- `preflight.json`
- `runtime_startup.json`
- `source_paths.json`
- `document_rows.json`
- `queue_before.json`

## Result

Only AAU was submitted.

- Ticker: AAU
- Document: `508fc892-ae88-45ec-981f-cd9e124c8375`
- Run id: `4793ba97-85c0-4fde-9144-3a9b24e866ca`
- Final extraction status: `failed`
- Error: `pass1:OLLAMA_URL must be set when provider is 'ollama'`
- Financial rows written by this run: `0`

The remaining six approved documents were not submitted.

## Diagnosis

The failure is runtime configuration parity, not a completed seven-document
canary result. `generate_json()` loads the model-routing config before
dispatching extraction. That config includes `embedding_provider: ollama`, and
the dedicated worker was started without `OLLAMA_URL`; config resolution failed
before the extraction call could use the llama.cpp runtime on `:8001`.

The backend launcher defaults `OLLAMA_URL` to `http://127.0.0.1:11434`, but the
manual dedicated worker command in this attempt did not set it.

## Post-Stop State

- Post-stop `llm_gpu` queue depth was `0`.
- The score queue still had `3` unrelated `thesis_watchdog_check` items.
- The canary-specific backend, router, and worker units were left active for an
  immediate bounded retry card.

See:

- `canary_results.json`
- `queue_after.json`

## Next Safe Step

Release this failed runtime card, open a narrow retry card, restart the
dedicated `llm_gpu` worker with `OLLAMA_URL=http://127.0.0.1:11434`, re-run the
preflight gates, and resubmit the approved documents one at a time. Do not
claim extraction works across all tickers from this failed canary.
