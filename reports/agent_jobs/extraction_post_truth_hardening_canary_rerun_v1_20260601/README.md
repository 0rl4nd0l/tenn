# Extraction Post Truth Hardening Canary Rerun V1

## Result

The bounded seven-document backend-route rerun completed. All seven approved
documents accepted through `POST /api/process/document/{document_id}`, and the
actual payload export/rekey matched all seven source-reviewed fixtures.

This is still not broad extraction graduation. The real-gold scorecard trusted
six fixtures and quarantined ATM on scale.

## Accepted Runtime Runs

| Ticker | Status | Run ID |
| --- | --- | --- |
| AAU | `ok_low_confidence` | `27ab81b5-94f7-4424-82dc-d8c3a7a0661e` |
| ATM | `ok_low_confidence` | `05e96f37-0c1e-4fdc-bd3f-a0bd810245c1` |
| AM5 | `ok` | `27e395ee-eb54-49b5-84fa-f13302422bdb` |
| AQX | `ok` | `6876e6a1-479d-4f8b-8ac2-85d091c04611` |
| CRS | `ok` | `5b75802c-c8f3-415e-a767-c6c315ffc55d` |
| CLV | `ok` | `c60d58a8-bb31-4b37-865f-5d1dc5487267` |
| CTM | `ok` | `741f93b9-2c2a-4f07-b1cc-1bb2aae3699a` |

## Scorecard

- Fixtures scored: 7
- Trusted fixtures: 6
- Quarantined fixtures: 1
- Correct metrics: 34 / 42
- Quarantined metrics: 8
- Wrong metrics: 0
- Missing metrics: 0

Trusted: AAU, AM5, AQX, CLV, CRS, CTM.

Quarantined: ATM, due `context_mismatch:scale`.

## Evidence Files

- `preflight.json`: registry, GPU, queue, model, source-row, and source-path gates.
- `results.json`: one-at-a-time submission and polling evidence.
- `canary_actual_payloads.json`: accepted runtime payload export.
- `canary_actuals_real_gold_keyed.json`: actuals rekeyed to fixture IDs.
- `source_document_rekey_summary.json`: all seven actual payloads matched.
- `canary_real_gold_scorecard.json`: formal trusted/quarantine scorecard.
- `runtime_shutdown.json`: dedicated units stopped, ports closed, M40 VRAM cleared.

## Next Safe Step

Fix ATM IDR scale normalization/metadata so source values expressed in millions
of Rupiah score against raw IDR real-gold expectations, then rerun this bounded
seven-document scorecard before any broader ticker-universe claim.
