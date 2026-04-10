# Real ASX Gold Corpus

This directory is the canonical real-document gold corpus for Tenn extraction eval.

Each gold file must stay compatible with the current evaluator contract and include:

- `document_id`
- `source_file`
- `period_type`
- `period_end`
- `currency`
- `scale`
- `metrics`
- `expected_trust`

Conservative labeling rules:

- Copy values from the source PDF only, never from model output.
- Stay inside the current real-gold metric lane: `revenue`, `operating_cash_flow`, `net_debt`.
- Use the exact period, currency, and scale stated by the document.
- Do not infer, reconcile, annualize, or derive missing values.
- If a supported metric is not explicit in the PDF, label that metric as `null` or leave the file unlabeled until verified.

Naming convention:

- Prefer `<ticker>_<period_type>_<period_end>.json`, using lowercase `a`, `h`, or `q`.
- If a document is intentionally awkward/problematic, add a short suffix, for example `_difficult`.

`source_file` guidance:

- Prefer a repo-relative PDF path under `financial-engine_v2/data/asx/docs/...`.
- Keep it pointed at the exact source PDF used for labeling.
- Do not point to a copied excerpt, OCR dump, or model artifact.

Recommended first corpus mix:

- 3 quarterly cash flow docs
- 3 half-year results
- 3 full-year results
- 1 awkward/problematic doc

Placeholder-only schema example:

```json
{
  "document_id": "<ticker>_<period_type>_<period_end>",
  "source_file": "data/asx/docs/<TICKER>/financial_performance/<source-pdf>.pdf",
  "period_type": "<A|H|Q>",
  "period_end": "<YYYY-MM-DD>",
  "currency": "<AUD|USD|...>",
  "scale": "<units|thousands|millions>",
  "metrics": {
    "revenue": <number-or-null>,
    "operating_cash_flow": <number-or-null>,
    "net_debt": <number-or-null>
  },
  "expected_trust": "<trusted|abstain|quarantine>"
}
```
