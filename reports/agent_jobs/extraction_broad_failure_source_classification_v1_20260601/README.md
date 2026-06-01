# Extraction Broad Failure Source Classification V1

## Summary

This audit classified the five validation-gate failures from the bounded broad robustness sample without running extraction or mutating any data store.

Result:

- 3 failures are candidate-selection/source-classification misses: ARL and TLS are AGM result/poll notices; HNG is an unaudited headline update without formal statements.
- 1 failure is a Scale Policy/source-unit detection miss: CAF Appendix 4E has explicit full-dollar values but failed with `scale_unknown`.
- 1 failure is metric ontology/EBIT label semantics: GTE is a valid annual report with dollar units, but loss before income tax was promoted to EBIT and correctly blocked by the validation gate.

This moves the full extraction goal forward by converting the broad-sample failures into concrete next workstreams. It does not prove full ticker-universe extraction graduation.

## Session Declaration

Lane: Evaluation
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Execution mode: SAFE EXTENSION MODE for report/state artifacts; audit-only source inspection
Intended files: task card, `docs/claude/STATE.md`, and this report bundle
Contested surfaces touched: none from `AGENTS.md`
Collision risk: LOW/MEDIUM, due Financial Truth evidence handling but no runtime/code/data mutation
Decision: proceed

## Evidence

- Prior sample artifacts parsed:
  - `reports/agent_jobs/extraction_broad_robustness_sample_v1_20260601/failure_digest.json`
  - `reports/agent_jobs/extraction_broad_robustness_sample_v1_20260601/broad_sample_results.json`
- Source PDFs inspected read-only from `/data/asx/docs`.
- `pdftotext`, `pdfinfo`, and `pdftoppm` are available under `/usr/bin`.
- Text extraction was written only under `/tmp/tenn_broad_failure_source_classification_v1/`.

## Findings

### Candidate Selection

ARL and TLS should be excluded from broad financial extraction candidates because they are AGM result notices with poll/proxy tables, not financial statements.

HNG should also be excluded from canonical financial-row extraction. It contains headline unaudited values in millions but no formal statements, and says the update is ahead of planned release and subject to audit.

### Scale Policy

CAF should remain eligible. Its Appendix 4E table has explicit full-dollar values, including revenue and attributable profit. The `scale_unknown` failure indicates the source-unit policy is too narrow for one-page Appendix 4E summary rows with explicit dollar-prefixed amounts and no table-level `$000`/million header.

### Metric Ontology

GTE should remain eligible. The source is a full annual report and its financial statements use dollar/unit headers. The failure is that `Loss before income tax` was treated as EBIT. The validation gate correctly blocked that. Follow-up should preserve the guard while hardening EBIT abstention or partial metric repair policy.

## Next Safe Step

Create a bounded implementation task card for:

1. Excluding AGM/poll notices and unaudited non-statement headline updates from broad extraction candidates.
2. Adding a source-unit rule for Appendix 4E full-dollar summary rows.
3. Reviewing whether the metric gate can drop/abstain invalid EBIT while preserving other valid metrics, or whether full-payload rejection remains the desired policy.

Do not claim full extraction graduation from this report. The broad sample remains 2 `ok`, 1 `ok_low_confidence`, and 5 `failed` before follow-up implementation.
