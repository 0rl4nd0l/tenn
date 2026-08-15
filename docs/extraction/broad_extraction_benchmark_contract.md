# Broad extraction benchmark contract

- Status: evaluation contract only
- Owner: Financial Truth
- Source of truth: `financial-engine_v2/backend/app/services/broad_extraction_benchmark.py`
- Last verified base: `7a28721deb93dfefa3859a2d79bfca81453b54c5`
- Stale if: the issue #554 corpus size, metric profile, identity dimensions, or
  acceptance thresholds change

## Purpose

The issue #554 benchmark contract makes broad extraction results comparable
without reading source documents or writing Financial Truth. Callers supply a
frozen corpus, a source-adjudicated expectation matrix, a candidate observation
set, and optionally a baseline observation set. The pure `score_benchmark(...)`
function validates those inputs and returns an immutable deterministic score.

This module is not an extractor or benchmark runner. It does not open PDFs,
call a model, access a database, mutate gold data, or promote an observation.

## Frozen input contract

The scorer requires:

- exactly 20 documents from 20 distinct issuer identities;
- exactly ten declared metrics for every document, producing 200 expectation
  cells;
- admitted documents bound to a source path and lowercase SHA-256;
- explicit `data_missing` documents with no claimed source identity;
- annual, half-year, or quarterly period type and a valid ISO period end;
- applicability and adjudication state for every expectation; and
- raw value, raw unit, normalized value, and evidence location for every
  verified applicable expectation.

A `data_missing` document cannot carry verified expectations or extraction
observations. An accepted observation must carry finite raw and normalized
numbers, raw-unit identity, valid period identity, source SHA-256, and evidence
location. ISO currency is also required for monetary metrics;
`shares_outstanding` is the explicit non-currency exception. Malformed,
duplicate, partial, or out-of-contract inputs fail before a score is produced.

## Outcome semantics

Every expectation cell receives exactly one outcome:

- `correct`: an accepted observation matches raw value, unit/scale, normalized
  value, period type and end, currency, source hash, and evidence location;
- `incorrect`: an accepted observation fails any required identity dimension,
  including an accepted value for an inapplicable or unresolved expectation;
- `abstained`: an applicable verified cell has no accepted observation;
- `unsupported`: the expectation is not scoreable and no value was accepted;
  or
- `data_missing`: its document has no admitted source.

`coverage` is correct cells divided by all predeclared applicable cells.
`exact_accuracy` is correct cells divided by accepted cells. The score also
reports mismatch counts for raw value, scale, normalized value, currency,
period, source, and provenance, plus source/provenance binding rates.
Each immutable row also carries issuer and document-class identity so reports
can aggregate without a separate document join.

## Digests

- `corpus_digest` binds the ordered-normalized document identities.
- `contract_digest` binds both the documents and all 200 expectations.

Input order does not change either digest. Any source identity, applicability,
expected value, unit, currency, period evidence, or adjudication change changes
the relevant digest. A future runner must persist both digests with its result.

## Gates

`gate_passed` is the absolute product threshold. It requires:

- at least 95% coverage of applicable cells;
- at least 99% exact accepted accuracy;
- zero period swaps;
- 100% source-hash binding;
- 100% evidence-location binding;
- no `data_missing` cells; and
- no regression against a supplied baseline.

`repair_gate_passed` is the incremental failure-class threshold. It requires a
supplied baseline, at least one newly correct cell, no previously correct cell
becoming non-correct, no increase in incorrect cells or any identity-mismatch
class, zero candidate period swaps, and complete candidate source/provenance
binding. An unchanged candidate cannot claim repair progress. A safety-only
change that produces no newly correct cell also cannot pass the repair gate.

Neither gate promotes data or closes issue #554 automatically.

## Current evidence boundary

This contract is tested only with synthetic in-memory fixtures. Synthetic
fixtures prove scorer behavior; they are not extraction-quality evidence.
The frozen source-adjudicated 20-by-10 matrix, a no-write runner adapter, and a
real before/after corpus result remain separate work. Running that corpus or
changing extractor behavior requires its own exact task scope and Tier-2
approval. Until then, no broad recovery, 95% coverage, or issue-completion claim
is supported by this contract.
