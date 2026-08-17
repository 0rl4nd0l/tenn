# Broad extraction benchmark contract

- Status: evaluation contract only
- Owner: Financial Truth
- Source of truth: `financial-engine_v2/backend/app/services/broad_extraction_benchmark.py`
- Last verified base: `2bd1033e6e202998be6db82858c75a8119f7ac40`
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
The separate `scripts/run_broad_extraction_benchmark_v2.py` adapter binds and
scores an authorized v2 replay; it does not change this pure scorer contract.

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

The scorer and v2 execution adapter are tested with synthetic fixtures.
Synthetic fixtures prove contract, receipt, completeness, and publication
behavior; they are not extraction-quality evidence. The source-adjudicated v2
20-by-10 matrix is frozen and hash-bound, but no v2 extraction or score exists.
Running that corpus or changing extractor behavior requires its own exact
Tier-2 authority. Until then, no broad recovery, 95% coverage, or
issue-completion claim is supported by this contract.

## V2 execution contract

The v2 adapter accepts only the frozen input identities recorded in its source
manifest: corpus, expectations, case manifest, semantic corpus digest, and
semantic contract digest. All 20 cases must map one-to-one to admitted corpus
documents. Repo-relative source paths are joined once to the declared source
root and hashed; the replay does not search fallback roots or substitute a
different matching file. The predecessor v1 runner and replay behavior remain
unchanged.

Validation requires an explicit absolute Python interpreter. The runner starts
with an import-only preflight for the real replay modules, records the Python
binary hash and installed dependency-version snapshot, and creates no receipt.
It also requires an explicit exact Git HEAD, a clean tracked worktree, no
untracked files in the executable code roots, and records the commit tree plus
hashes of the runner, replay, scorer, extractor, and metric-contract modules.
Use the documented `financial-engine_v2/.venv` environment or another explicit
existing repo-supported interpreter; do not install or alter dependencies as
part of a one-shot run.

The child replay starts with explicit isolated/no-bytecode interpreter flags
and a receipt-bound allowlisted environment; inherited `PYTHONPATH`, Python
startup hooks, and other caller variables are not passed through. At child
startup it rehashes the running interpreter and revalidates the exact dependency
versions/snapshot against the receipt before extraction modules are imported.
The receipt-bound Git/code identity is revalidated immediately around those
imports, after case execution, and again before the outer runner publishes any
scored artifact. Any observed drift is terminal `EVIDENCE_CONFLICT`.

An authorized launch requires both the output root and its sibling
`INVOCATION_RECEIPT.json` to be absent. After every input, source, output, and
interpreter check passes, the runner creates the receipt using
`O_CREAT|O_EXCL` and immediately launches replay. The receipt is never removed
or replaced. Direct non-preflight v2 replay also requires that exact
hash-matching receipt, so calling the lower-level script cannot bypass the
one-shot boundary. The lower-level replay also binds its actual execution
profile and current clean Git/code identity to the receipt and rejects
non-baseline or code-drifted v2 launches.

Replay writes only to a fresh hidden staging directory. Scoring requires one
result for each of the 20 declared case/document pairs, no infrastructure
failure, and a passing side-effect audit. A complete replay is scored even when
its extraction expectations fail; those misses are benchmark outcomes, not
missing execution evidence. Raw per-case connection, protocol, read/write, and
timeout transport exceptions are infrastructure failures even when they do not
carry an extraction-pass prefix.
Missing or duplicate results produce no score.

The replay payload keeps strong, direct `total_debt` capture in a separate
benchmark-only internal namespace so the frozen metric can be observed without
promoting that internal extractor field into canonical or persisted Financial
Truth. It admits that capture only when the debug candidate also carries an
exact requested-period source cell; strong but period-unbound debt remains an
abstention. The current production-shaped extractor does not emit such a bound
debt source cell, so current debt observations truthfully abstain; changing
extractor period binding is outside this execution-support contract. Accepted
monetary observations preserve the bound source cell's
raw value and explicit unit suffix instead of reconstructing them from the
normalized value. Both `ok` and `ok_low_confidence` are scoreable successful
observations. Shares outstanding likewise requires an exact requested-period
source cell and preserves its scaled count identity; it does not require a
currency. When a monetary source cell has an explicit currency prefix, that
source currency is preserved instead of being replaced by the document-level
currency.

Immediately before extraction, every v2 source is copied through a held,
non-symlink file descriptor into the isolated runtime root and the copy is
re-hashed against the frozen source identity. Extraction reads that isolated
copy, preventing a shared-root path replacement from being mislabeled with the
frozen hash. Success and post-launch failure evidence are sealed with
`OUTPUT_MANIFEST.json` and `SHA256SUMS`, then published with an atomic
no-replace directory rename. An existing or racing output is never deleted,
reset, or overwritten.
