# 15 — Currency and FX Handling

Defines how non-AUD currencies are treated in the extraction pipeline and what downstream consumers should expect.

---

## Current behaviour (no FX conversion)

The extraction pipeline stores financial metrics in the currency reported by the document.
No FX conversion is applied at any stage.

| Document currency | `_validate_gate` outcome | DB storage |
|-------------------|--------------------------|------------|
| AUD | `ok` (if all other gates pass) | Metrics stored as-is |
| Non-AUD (USD, GBP, EUR, …) | `ok_low_confidence` | Metrics stored as-is; `currency` column set |

**Two warnings are emitted per non-AUD document:**
1. At Pass 1 classification: `"non-AUD currency detected: {currency} — values stored as-is (no FX conversion applied)"`
2. At `_validate_gate`: `"validation_gate:non_aud_currency:{currency} — downgrading to ok_low_confidence (no FX policy)"`

The `ok_low_confidence` status is **not a failure**. Metrics are persisted to `asx_periodic_financials` identically to `ok` status. It is a semantic marker meaning "extracted values are valid but require interpretation before cross-company comparison."

---

## What `ok_low_confidence` changes (and does not change)

| Consumer | Effect of `ok_low_confidence` |
|----------|-------------------------------|
| `_upsert_financial_rows` | No effect — both `ok` and `ok_low_confidence` trigger upsert |
| `ExtractionRun.status` | Recorded verbatim; visible in logs and DB |
| RAG / chat / analysis services | **No effect** — none of these branch on extraction status |
| `/financials` API endpoint | **No effect** — returns metrics regardless of status |
| `currency` column | Populated from Pass 1 result for all statuses |

Programmatic behavior is identical between `ok` and `ok_low_confidence`. The distinction is operator-visible only.

---

## High-denomination native currencies

Source-explicit Indonesian rupiah table units are handled as native currency,
not converted:

- `Rp`, `IDR`, and `rupiah` table markers resolve to `currency=IDR`.
- Explicit `Rp`/`IDR`/rupiah `trillion` or `trillions` table units resolve to
  `scale=trillions`.
- Pass 3a multiplies raw table values by `1_000_000_000_000`.
- `_validate_gate` still returns `ok_low_confidence` after hard gates pass.
- Source-unit row evidence such as `Rp 12.5 trillion` must agree with the
  normalized metric value; 100x or larger disagreement fails.

The AUD-like `$500B` sanity cap is not applied to IDR native values because it
would reject valid high-denomination rupiah facts. IDR instead uses a loose
native-currency cap only to catch extreme over-scaling. This is not FX
conversion and does not make IDR rows comparable with AUD peers.

---

## What downstream consumers must assume

Until FX conversion is implemented:

- **Non-AUD metrics cannot be directly compared with AUD peers.** A USD-denominated BHP revenue figure and an AUD-denominated RMS revenue figure are not on the same scale.
- The `currency` column on `asx_periodic_financials` identifies which currency a row uses. Filter or convert before cross-company analysis.
- The `extraction_status` column on `extraction_runs` identifies which runs produced non-AUD results (status = `ok_low_confidence`).

---

## Roadmap

FX conversion is a future module. When built, it should:

1. Read the `currency` column from `asx_periodic_financials`.
2. Apply daily FX rates (from a provider such as OpenBB) to convert non-AUD metrics.
3. Store converted values in a separate column or derived table — do not overwrite original extracted values.
4. Mark converted rows with the applied rate and date.
5. Retire the `ok_low_confidence` downgrade for rows where conversion succeeded.

Until that module exists, do not invent conversion rates in ad-hoc analysis code. Use the `currency` column to identify and exclude or separately treat non-AUD rows.

---

## Key files

| File | Role |
|------|------|
| `backend/app/services/multipass_extraction.py` | `_validate_gate` (non-AUD downgrade), `run_multipass_extraction` (Pass 1 warning) |
| `backend/app/models/asx_financials.py` | `currency` column on `asx_periodic_financials` |
| `backend/app/models/extractions.py` | `status` column on `extraction_runs` |
| `docs/architecture/14_roadmap_and_modules.md` | FX conversion listed as future data acquisition module |

**Regression guard:** `test_validate_gate_non_aud_returns_ok_low_confidence` in `backend/tests/test_multipass_extraction.py`.
