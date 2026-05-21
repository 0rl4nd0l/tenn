# ASX Comparator Artifact Schema v1

## 1. Purpose

The ASX comparator artifact schema defines a report-only output shape for
future deterministic parser and table-comparator prototypes. It gives Appendix
5B, Appendix 4C, Appendix 4D, Appendix 4E, annual report, half-year report, and
external table comparator experiments one common metadata contract before any
parser routing or extraction integration is considered.

The schema is for evidence review. It can describe source tables, metric
candidates, unsupported metrics, abstentions, warnings, provenance, and
validation outcomes. It does not create financial truth.

## 2. Non-goals

- Do not implement a parser.
- Do not run extraction, Docling, OCR, comparator tools, Qdrant, news, memory,
  Cockpit, Home, runtime, model, or GPU jobs.
- Do not change parser routing, production extraction, prompts, gold labels,
  scorecards, databases, vector stores, source labels, runtime config, or
  persistence.
- Do not infer canonical financial truth.
- Do not authorize canonical writes.

## 3. Required Artifact Fields

Each artifact must include:

- `artifact_type`: literal `asx_comparator_artifact_v1`
- `schema_version`: literal `1`
- `canonical_write`: literal `false`
- `document_id`
- `ticker`
- `document_type`
- `source_pdf_path` or `source_reference`
- `source_sha256` or `source_checksum`
- `parser_id`
- `parser_version`
- `generated_at`
- `period_end`
- `reporting_period`
- `currency`
- `scale`
- `tables`
- `metric_candidates`
- `unsupported_metric_candidates`
- `abstain_reasons`
- `warnings`
- `provenance`
- `validation_summary`

`tables`, `metric_candidates`, `unsupported_metric_candidates`,
`abstain_reasons`, and `warnings` are arrays. `provenance` and
`validation_summary` are objects.

## 4. Table Evidence Schema

Each table entry supports:

- `table_id`
- `page`
- `bbox`
- `caption`
- `headers`
- `rows`
- `source_anchor`
- `parser_confidence`
- `warnings`

Tables are evidence containers. They do not prove a canonical metric by
themselves. A metric candidate that cites a table must still cite page, row,
column, and evidence text.

## 5. Metric Candidate Schema

Each metric candidate supports:

- `metric_name`
- `candidate_value`
- `raw_value`
- `normalized_value`
- `unit`
- `currency`
- `scale`
- `period`
- `source_table_id`
- `page`
- `row_label`
- `column_label`
- `line_item_id`
- `evidence_text`
- `confidence`
- `status`: one of `candidate`, `review_only`, `abstain`, or `unsupported`
- `canonical_write`: literal `false`
- `abstain_reasons`
- `warnings`

For non-abstain candidates, source table, page, row, column, and evidence text
must be present. If that evidence is missing, the candidate must abstain and
provide an abstain reason.

## 6. Unsupported Metric Policy

Unsupported metrics may be recorded for reviewer visibility only. EPS, NTA,
dividends, EBITDA, total debt, and any other metric placed in
`unsupported_metric_candidates` must use `status=review_only` or
`status=unsupported`.

Unsupported metrics must never use `status=candidate` and must always keep
`canonical_write=false`.

## 7. Abstain Policy

Use `status=abstain` when evidence is missing, ambiguous, conflicting, outside
the supported metric scope, or too weak to form a report-only candidate.

Abstain candidates may omit page, table, row, and column evidence, but they must
explain the abstention in `abstain_reasons`. Artifact-level abstentions belong
in the artifact `abstain_reasons` array.

## 8. `canonical_write=false` Rule

The artifact and every metric candidate must set `canonical_write` to literal
`false`. This schema is report-only metadata. A valid artifact cannot write or
authorize canonical truth.

`status=candidate` means "candidate for review inside this artifact", not
"approved canonical value".

## 9. Provenance Requirements

Each artifact must cite source evidence through `source_pdf_path` or
`source_reference`, and must include `source_sha256` or `source_checksum`.

Metric candidates should cite their table and exact location with
`source_table_id`, `page`, `row_label`, `column_label`, and `evidence_text`.
`provenance` should record the fixture, parser prototype, comparator run, or
other report-only origin used to produce the artifact.

## 10. Future Parser Prototype Expectations

Future Appendix 5B, 4C, 4D, 4E, annual, half-year, or external table comparator
prototypes should emit this artifact shape only into caller-owned report paths.
They should be deterministic, cite evidence, use abstention when evidence is
insufficient, and keep unsupported metrics review-only.

Parser prototypes must not import production extraction routing or write
canonical truth as part of this schema contract.

## 11. Promotion Gates Before Parser Routing

Before any parser routing can use ASX comparator output, a later approved task
must provide:

- corpus-level fixture and real-document gate reports;
- deterministic parser tests for each supported document type;
- failure and abstention coverage;
- production-boundary import checks;
- explicit approval for parser routing changes;
- explicit approval for any canonical write path change.

## 12. Do-Not-Do List

- Do not treat comparator artifacts as financial truth.
- Do not import this schema into production routing.
- Do not run extraction from this schema.
- Do not write canonical values from this schema.
- Do not change ASX gold labels or scorecards for this schema.
- Do not persist DB, Qdrant, memory, news, or runtime state.
- Do not allow Appendix 4C or 5B cash-flow artifacts to emit revenue, NPAT, or
  net-debt as `status=candidate`.
- Do not allow Appendix 4D or 4E artifacts to emit EPS, NTA, or dividends except
  as `review_only` or `unsupported`.
