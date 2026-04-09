# Extraction Hardening Backlog

## Now
- Add synthetic fixture harness for extraction-only classification (`extraction_eval.py`).
- Add isolated unit tests for correct/wrong/missing/abstain/quarantine behavior.
- Record fixture docs and taxonomy for shared team language.

## Next
- Expand synthetic fixtures by edge pattern (rounded zeros, mixed currency documents, unusual scale statements).
- Add optional provenance assertions (`result.provenance` lineage fields) in harness output.
- Add fixture-level confidence bands and minimum-score thresholds used by local CI.

## Deferred
- Full live `pytest -m live_eval` hardening in this scaffold.
- Cross-language or downstream modeling benchmarks using synthetic fixtures.
- Any embedding/vector/RAG changes from this hardening work.
