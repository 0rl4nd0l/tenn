# DATA_MISSING

Job: `asx_deterministic_extraction_extension_audit_v1_20260519`

The following gaps were recorded instead of guessing.

## Current Artifacts

- Broader `gold`, `metric`, `docling`, and `extraction` report artifacts from the recent Gold Metric Coverage Audit were not present as committed files in the isolated worktree. A separate active registry job owns related report paths in the runtime checkout, so this audit did not inspect or reuse those uncommitted artifacts.
- The only matching committed Appendix 5B report found in this branch was `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/`.

## Parser Ownership

- No backend `ASXDocumentType` enum or deterministic ASX document-type classifier was found.
- Existing backend Pass 1 owns A/H/Q report type, not ASX form type.
- Script-level `scripts/document_classifier.py` exists but only classifies broad `appendix_report`, `financial_report`, `announcement`, `presentation`, `conference`, `investor_update`, `timetable`, and `unknown`.

## Appendix Parsers

- No standalone Appendix 5B backend parser/scorer/gate stack was present in this branch. Current Appendix 5B behavior is embedded in multipass table locator/merge/gate logic and tests, plus the fifth-document approval packet.
- No deterministic Appendix 4C parser module was found.
- No deterministic Appendix 4D parser module was found.
- No deterministic Appendix 4E parser module was found.

## Comparator Implementations

- No MinerU implementation/reference found in inspected surfaces.
- No Chandra implementation/reference found in inspected surfaces.
- No TATR/Table Transformer implementation/reference found in inspected surfaces.
- No pdfplumber implementation/reference found in inspected surfaces.
- No pypdfium2 implementation/reference found beyond a fixture note documenting garbled output on a known PDF.
- Camelot exists only in script-level cashflow fallback code and is explicitly guarded out of backend dependencies.

## Evaluator Support

- Real-gold supported metrics are limited to `revenue`, `operating_cash_flow`, and `net_debt`.
- Confirmed metric coverage mapping supports the current schema field set, but not EPS, EBITDA, NTA, dividends, or total debt as first-class scored fixture metrics.
- `ExtractionOutputSchema` exists but is explicitly not activated in the live pipeline.

## ASX Form Fixtures

- Current fixture directories contain Appendix 5B and Appendix 4D examples, but no dedicated ASX document-type classifier fixture suite was found.
- Dedicated Appendix 4C/4E classifier and parser fixtures are missing as a separate tested contract.

## Documentation Drift

- `docs/architecture/12_evaluation_and_drift_monitoring.md` describes an older fixture pool of 13 fixtures, while current fixture and real-gold directories each contain 15 JSON files.
