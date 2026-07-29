# ASX document extraction contracts

Ticket `ASXFP_04_EXTRACTION_CONTRACTS` introduces a deterministic,
fail-closed boundary between document-type classification and financial metric
extraction.

## Authority and non-authority

`app.services.asx_extraction_contracts` is the immutable document-contract
authority. It consumes canonical metric names from
`app.services.financial_metric_contract`; it does not declare aliases, add
metrics, or widen the metric ontology.

Classification and contract selection are metadata only. They never:

- prove a metric value or its period;
- satisfy row-level provenance or source-evidence requirements;
- authorize persistence or a canonical write; or
- bypass source eligibility, reconciliation, validation, noncandidate, or
  advisory gates.

The selection metadata therefore keeps `canonical_write`,
`metric_evidence_proven`, and `persistence_authorized` false.

## Supported contracts

The canonical fields below refer to the current
`CANONICAL_METRIC_FIELDS` authority. Annual, half-year, and generic quarterly
contracts permit those fields only when all existing direct-source and
provenance gates independently pass.

| Document type | Period basis | Allowed canonical metrics |
| --- | --- | --- |
| `annual_report` | `A` | Current canonical metric authority |
| `appendix_4e` | `A` | Current canonical metric authority |
| `half_year_report` | `H` | Current canonical metric authority |
| `appendix_4d` | `H` | Current canonical metric authority |
| `quarterly_report` | `Q` | Current canonical metric authority |
| `appendix_4c` | `Q` | `operating_cf`, `investing_cf`, `financing_cf`, `capex`, `cash_end` |
| `appendix_5b` | `Q` | `operating_cf`, `investing_cf`, `financing_cf`, `capex`, `cash_end` |

Appendix 4C and Appendix 5B explicitly forbid classification-based inference of
`revenue`, `ebit`, `np_attributable`, and `net_debt`. Their classification
cannot enable those fields.

Every contract declares:

- required document-type-anchor and period-basis context;
- permitted period bases;
- minimum deterministic classification-source evidence;
- forbidden classification, provenance, and persistence inferences; and
- abstention conditions.

## Fail-closed routing

`run_multipass_extraction()` preserves the existing source-document gate as the
first authority. After parser output supplies first-page text, deterministic
classification selects a contract. Unknown, ambiguous, unsupported, or
insufficient-evidence classifications return
`validation_gate:extraction_contract_abstain` before Pass 1.

After Pass 1 and deterministic Appendix-wrapper corrections, routing validates
the period basis and required context. A mismatch returns a validation-gate
failure before Pass 2 or Pass 3. A valid decision restricts Pass 3 metric
schemas and source-recovery paths to the contract allowance. Existing
provenance, reconciliation, scale, period, confidence, and persistence gates
remain independently authoritative.

The returned payload records document classification, selected contract, and
routing-decision metadata for auditability. None of those records authorizes a
write.

## Diagnostic status

The protected 12-document diagnostic manifest and its referenced label files
contain expected gold document types, but no independent source-derived
classifier surrogate (such as title text, headings, table captions, anchors, or
form labels). Gold labels cannot be used as classifier input.

Accordingly, real-diagnostic classification for Ticket 04 is `DATA_MISSING`.
No PDF, OCR, extraction, model, prompt, or fabricated surrogate was used to
replace the missing evidence.
