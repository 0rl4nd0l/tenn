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
- permitted document-type-specific anchors, excluding period wording alone and
  shared generic announcement wording;
- minimum deterministic classification-source evidence;
- forbidden classification, provenance, and persistence inferences; and
- abstention conditions.

## Fail-closed routing

`run_multipass_extraction()` preserves the existing source-document gate as the
first authority. After parser output supplies title metadata and page-numbered
section text, deterministic classification collects document-type evidence
with its page location and selects a contract. Unknown, ambiguous, unsupported,
or insufficient-evidence classifications return
`validation_gate:extraction_contract_abstain` before Pass 1.

Explicit Appendix 4C and Appendix 5B form anchors may take precedence over a
generic quarterly-activities cover when those anchors occur on later pages.
For a bundled half-year document, high-confidence half-year-report evidence on
a later page takes whole-document precedence over an earlier Appendix 4D
wrapper. Other annual, half-year, quarterly, and announcement anchors remain
limited to title metadata and first-page text so references deep in a document
cannot create a competing document type. Weak, same-page, unsupported, or
conflicting anchors do not receive bundle precedence and remain subject to
abstention. Announcement/PDF title metadata remains eligible deterministic
evidence, including when an image-heavy first page has little extracted text.

After Pass 1 and deterministic Appendix-wrapper corrections, routing validates
the period basis and required context. A mismatch returns a validation-gate
failure before Pass 2 or Pass 3. A valid decision restricts Pass 3 metric
schemas and source-recovery paths to the contract allowance. Existing
provenance, reconciliation, scale, period, confidence, and persistence gates
remain independently authoritative.

The returned payload records document classification, selected contract, and
routing-decision metadata for auditability. None of those records authorizes a
write.

## Ticket 04 bounded diagnostic repair

The repair is derived from user-supplied summaries of local artifacts identified
by SHA-256, without reading those artifacts or any referenced PDF, gold label,
diagnostic, or holdout path:

- classifier diagnostic:
  `2e1e9fcb3885d9bdf706b668c7699f1a90feb0b7cbfdffed5bac430f8fd918c0`;
- PDF-title sensitivity:
  `026d7b7631994a103f6481fa1cb460994eb49852fafda2fa13bf88ec274007a4`;
- failed-anchor locations:
  `d2efe1592e3b97bd6729125d58bb33b0a747d0372d0e3ce390ee49c78ed2ddac`.

Synthetic text-only regressions cover the summarized failure shapes. They do
not establish holdout accuracy, metric correctness, source provenance, or
production readiness. No PDF, OCR, model, prompt, runtime, metric extraction,
or canonical write is part of this repair.
