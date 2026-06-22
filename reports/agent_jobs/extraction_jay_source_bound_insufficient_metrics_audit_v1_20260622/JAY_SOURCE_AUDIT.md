# JAY Source Audit

## Finding

JAY `04438122-c607-4c53-bb41-2e3864c06479` should not be retired as a source noncandidate. It is a source-bound market-update/trading-update document with a clear Q3 FY23 revenue table. The current zero-metric failure is a plausible extraction coverage gap, but this task does not prove a product fix.

## Primary Source

- File: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/JAY/financial_performance/2023-04-11_q3fy23-update-march-record-trips-and-revenues_04438122-c607-4c53-bb41-2e3864c06479.pdf`
- SHA256: `f2915ac994b93b7d01bb92ffe7d9943ed34e85a4cb8e0a8c755359873e68be4a`
- PDF title: `2023-04-11 Market Update`
- Pages: 4
- Saved status: `failed`
- Saved error: `validation_gate:insufficient_metrics:0`
- Saved period: `Q`, `2023-03-31`
- Saved scale: `thousands`

## Source Evidence

- Page 1 headline identifies a Q3 FY23 market update.
- Page 2 contains a `Q3 Trips and revenues` table.
- The Q3 FY23 row includes:
  - `Revenue Booked`: `$1,403K`
  - `Revenue Refunded`: `$(251)K`
  - `Net Revenue`: `$1,152K`
  - `Net Rev / Trip`: `$7.57`
- The same page has a March annualised run-rate table with `Net Revenue` `$5.69M`.
- Page 3 states that the later Q3 FY23 Quarterly Business Review and Appendix 4C would contain full contribution-profit and cash-flow detail.

## Saved Artifact Evidence

- Count-24 source artifact: `/home/l4nd0/tenn-count24-current-canonical-execution-v1-20260617/reports/agent_jobs/extraction_count24_current_canonical_execution_v1_20260617/sample_results.json`
- Prior source classification was incomplete: `DATA_MISSING_title_only_preflight_no_pdf_parse`.
- Prior source classification after extraction was `unknown_document`, reason `not_detected`.
- Prior result had all canonical metrics null and no metric provenance.
- Docling cache exists and includes the Q3 FY23 revenue table rows.

## Pairing Candidate

Checked one adjacent same-family candidate:

- `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/JAY/financial_performance/2023-07-07_q4-fy23-market-update-growth-in-fy23-of-99_e2149cbc-e031-4e20-8110-597b5c9d7d8e.pdf`
- SHA256: `8e5fda1f905aa86c680ebd8038a0badc5b1de6ed50f41795af36fe1db6415101`
- It is also a JAY market update and contains the same trips/revenue table family, including Q4 FY23 `Net Revenue` `$1,546K` and FY23 `Net Revenue` `$5,085K`.

## Classification

- source_noncandidate: `false`
- unsupported_document_family: `false`
- extractable_source_bound: `true`
- confidence: `medium`

The document family is not a statutory report, so cash-flow and profit metrics should not be inferred. However, the source provides a labeled revenue-family metric that matches current extractor instructions for `revenue`, and a quarterly payload only needs one canonical metric to clear the minimum-count gate after the other gates pass.

## Stop State

Stop at report-only `NO_PRODUCT_FIX_PROVEN_IN_THIS_TASK`.

The next safe step is a narrow no-write replay/fixture packet for JAY market updates, not a direct parser/classifier/prompt/product-code edit.
