# ASX Document-Type Fixture Contract

## 1. Purpose

This contract defines the first safe fixture and schema foundation for future
ASX-aware document-type classification. The fixtures describe short synthetic
text surrogates and expected classifier outputs for document type metadata.

Document-type classification is metadata, not metric truth. A document type can
help a future pure classifier explain what kind of ASX announcement was seen,
but it does not prove any financial metric and does not authorize extraction,
parser routing, canonical writes, or financial truth persistence.

## 2. Non-goals

- Do not implement a classifier.
- Do not add parser routing or extraction behavior.
- Do not change Docling, OCR, comparator tools, prompts, gold labels, canonical
  scorecards, DBs, Qdrant, memory, news, Cockpit, Home, runtime config, model
  config, GPU config, or financial truth writes.
- Do not use production data.
- Do not copy full report pages or large source text.

## 3. Supported Document Types

The approved `expected_document_type` values are:

- `annual_report`
- `half_year_report`
- `appendix_4c`
- `appendix_4d`
- `appendix_4e`
- `appendix_5b`
- `other_asx_announcement`
- `unknown_or_abstain`

## 4. Required Fixture Fields

Each fixture JSON object must include:

- `fixture_id`
- `document_id`
- `ticker`
- `expected_document_type`
- `expected_confidence_band`
- `expected_abstain`
- `source_text_surrogate`
- `positive_anchors`
- `negative_anchors`
- `required_evidence`
- `abstain_reasons`
- `must_not_infer_metrics`
- `canonical_write`
- `notes`

`expected_confidence_band` must be one of `high`, `medium`, `low`, or
`abstain`. `canonical_write` must be literal `false`.

## 5. Evidence And Anchor Policy

Fixtures use short synthetic or surrogate phrases only. The
`source_text_surrogate` object may contain first-page title text, ASX
announcement title text, headings, table captions, relevant line anchors, and
footer or form labels. These anchors exist to support future classification
tests, not extraction tests.

Positive anchors are the minimum phrases expected to support the document type.
Negative anchors are phrases that should prevent an over-broad classifier from
choosing the wrong class. Required evidence should identify the anchor
combination a future classifier must cite.

## 6. Abstain Policy

A fixture must set `expected_abstain=true` when the surrogate has too little
signal, conflicting form labels, mixed document-type evidence, or only generic
announcement language. Abstain fixtures must include non-empty
`abstain_reasons`. Abstention should be preferred over guessing between
Appendix 4D and Appendix 4E, or between generic ASX announcements and formal
periodic reports.

## 7. Per-Document-Type Expected Anchors

### Annual Report

Expected anchors include `annual report`, directors' report, financial
statements, notes to the financial statements, corporate governance, or an
annual reporting period. Appendix form labels should be negative anchors.

### Half-Year Report

Expected anchors include `half-year report`, interim financial report,
condensed consolidated financial statements, directors' declaration, or a
six-month period. Appendix 4D may also describe half-year results, so a future
classifier must distinguish formal report packaging from Appendix form labels.

### Appendix 4C

Expected anchors include `Appendix 4C`, `Quarterly cash flow report`, `Rule
4.7B`, operating cash flow lines, and financing or investing cash flow sections.
Appendix 4C fixtures must not imply revenue, NPAT, net debt, or income
statement metric extraction.

### Appendix 4D

Expected anchors include `Appendix 4D`, `Half year report`, and `Results for
announcement to the market`. EPS, NTA, and dividends may appear only as
review-only unsupported context unless a future schema explicitly supports
them.

### Appendix 4E

Expected anchors include `Appendix 4E`, `Preliminary final report`, and
`Results for announcement to the market`. EPS, NTA, and dividends may appear
only as review-only unsupported context unless a future schema explicitly
supports them.

### Appendix 5B

Expected anchors include `Appendix 5B`, `Mining exploration entity or oil and
gas exploration entity quarterly cash flow report`, `Rule 5.5`, exploration
expenditure, and related-party payments. Appendix 5B fixtures must not imply
revenue, NPAT, net debt, or income statement metric extraction.

### Other ASX Announcement

Expected anchors include investor presentation, strategy update, operational
update, capital raising, appointment, trading update, or other announcement
labels without a supported Appendix/report form label. This type is still
metadata only.

## 8. Negative And Ambiguous Cases

Negative cases must prove the future classifier can abstain or avoid overreach.
Examples include low-signal titles, generic market updates, and conflicting
Appendix 4D/4E evidence. Ambiguous cases should set `unknown_or_abstain` with
`expected_abstain=true`.

## 9. `canonical_write=false` Rule

Every fixture must set `canonical_write` to `false`. The fixture contract is a
read-only evaluation contract. It must never create, imply, or authorize
canonical financial truth writes.

## 10. Future Classifier Expectations

A future classifier should be a pure module that accepts the fixture-shaped
metadata and returns:

- `document_type`
- `confidence_band`
- `abstain`
- cited evidence anchors
- abstain reasons when applicable
- `canonical_write=false`

The classifier should use deterministic anchor evidence before any model-based
fallback, and it should prefer abstention when required evidence is missing or
conflicting.

## 11. Promotion Gates Before Production Routing

Before any production routing, extraction behavior, or parser selection can use
ASX document type output, a later task must add and pass:

- pure classifier unit tests;
- read-only comparator artifacts with `canonical_write=false`;
- deterministic sidecar parser prototypes;
- corpus-level gate reports;
- explicit approval for any parser routing change;
- explicit approval for any canonical write path change.

## 12. Do-Not-Do List

- Do not treat document type as financial metric truth.
- Do not infer revenue, NPAT, net debt, EPS, NTA, dividends, cash flow, or any
  other metric from document type alone.
- Do not route parsers based on this contract.
- Do not write canonical values based on this contract.
- Do not alter existing gold labels or scorecards.
- Do not run extraction, Docling, OCR, comparator, Qdrant, memory, news,
  Cockpit, Home, runtime, model, or GPU jobs for this fixture contract.
