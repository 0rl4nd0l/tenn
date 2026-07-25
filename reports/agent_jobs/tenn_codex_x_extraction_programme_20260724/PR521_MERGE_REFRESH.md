# PR #521 Merge and Ticket-01 Refresh

## Objective

Squash-merge Tenn PR #521 exactly at its reviewed head, prove the merged
canonical identity and registry/parity behavior, then append a report-only
Codex X extraction supervisor revision without launching ticket 01.

## Current state

`DONE`

- PR #521 disposition: `SQUASH_MERGED_EXACT_HEAD`
- Reviewed head:
  `7c421ad9e7721796e07dd6427f4caf584a577155`
- Reviewed tree:
  `17eecd8c81c3deb8c57c0565fbd13e9d31954bcc`
- Merge/canonical SHA:
  `107c926930ef5a14783a8293bac9b47c9046bfed`
- Canonical tree:
  `9e43e6380c357e1a40a23bff6d4a07522c86ff98`
- Ticket 01 classification: `READY`
- Codex X child launch: `NOT_RUN`, still prohibited by this goal

## Constraints and unsafe actions

The owner authorized one expected-head squash merge of PR #521 only. No
runtime, service, queue, DB, Qdrant, GPU, model, extraction, backfill,
production-data, source-PDF, gold-label, deployment, other PR mutation, or
Codex X child launch was authorized.

The original Tenn launch checkout and all unrelated dirty/stale worktrees were
preserved. A detached clean worktree at the exact merged canonical SHA was
used for validation.

## Merge evidence

- PR #521 was still an open draft with one commit, exact reviewed head/tree and
  parent, exactly nine reviewed paths, `MERGEABLE`/`CLEAN`, and two completed
  successful checks.
- The independent review artifact remained byte-identical to supervisor commit
  `11e1f49f034a2554ce96682adef88028e8ae34f6`.
- Canonical had advanced from reviewed base `2f5a8aac...` to `a144a69f...` only
  through merged PR #520's four disjoint launcher/test paths.
- PR #517 merge `d438cb454b56b4718c5a1c4721e48831a7b107a5` remained an ancestor.
- GitHub projected conflict-free tree
  `9e43e6380c357e1a40a23bff6d4a07522c86ff98`.
- PR #521 was marked ready only after the final machine-asserted gate passed.
- One REST merge call used expected head
  `7c421ad9e7721796e07dd6427f4caf584a577155` and returned
  `merged=true`, SHA `107c926930ef5a14783a8293bac9b47c9046bfed`.
- Final canonical is the merge SHA, has parent `a144a69f...`, matches the
  projected tree, and differs from its parent by exactly the reviewed nine
  paths.

The reviewed nine path contents match the reviewed head exactly. Canonical
control files and PR #520 launcher paths match the pre-merge canonical blobs.
PR #517's non-overlap source/tests are unchanged.

## Registry, parity, and PR #517 validation

On detached merged canonical:

- 348 focused registry, capability-guard, Docling, and multipass tests passed.
- Import smoke loaded the registry and all migrated callers.
- Parity digest matched
  `cc042df11e1743d9cf3085020991bd6dd8f73da835a7ece2efb48edf1c9f51ce`.
- `net_debt` remains direct-source-required with no authorized derivation.
- The sole authorized derivation is
  `appendix_5b_explicit_capex_subitem_sum` for `capex`.

Raw waiter evidence:

- `/tmp/tenn-pr521-merged-validation-20260725.json`
- `/tmp/tenn-pr521-merged-validation-20260725.json.log`

## Narrow ticket-01 reconciliation

The spec, ticket, plan, and ticket-set hashes are unchanged. Merged canonical
still lacks explicit numeric precision/supported-metric recall,
period-basis/accounting-basis correctness, and real scorecard grouping by
declared supported ASX document class. Provenance failure and real/synthetic
separation already exist and must be preserved.

Open draft PR #508 remains at
`4913ef0883410fcc6436b1387fa7c17642190d05`. Its four paths own NPAT owner
attribution and OCI-boundary multipass work; none overlaps ticket 01's allowed
scorecard file scope.

Ticket 01 is therefore `READY`. The schema state is `PLANNED`, with no blocker,
zero attempts, and no session IDs or result hashes.

## Updated run package

The additive revision is:

`proposed_run_package/revisions/pr521_integration_20260725/`

It contains the refreshed run manifest, schema bindings, ticket state, merge
and parity summary, artifact hashes, and exact first-child prompt. The prompt
SHA-256 is
`be4525a7b253cdc3a9c6aa11138365b9c9edfffeffbce3bb00d37f22117038c5`.

Both schema instances validate against the pinned design schemas. Every
revision artifact hash verifies.

## Files touched

Only files under
`reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/` were changed
in the supervisor worktree. The original manifests, ticket state, held prompt,
PR #513 disposition revision, and independent-review artifact remain
unchanged.

## Files intentionally not touched

No Tenn product, control-plane, runtime, source, fixture, gold-label, PDF,
service, data, deployment, or Codex X workspace file was edited. PR #508 and
all other PRs were not mutated.

## Commands and exit status

- Portable Tenn Git Guard preflights: exit `0`; no non-stale ownership block.
- Live `gh pr view`, GitHub API commit/compare, and `git ls-remote` checks:
  exit `0`.
- Exact head/tree/parent/path/check/review/canonical assertion gate: exit `0`.
- `gh pr ready 521`: exit `0`.
- Single expected-head REST squash merge: exit `0`, `merged=true`.
- Post-merge PR/canonical/tree/ancestry/path verification: exit `0`.
- Merged-canonical focused waiter: exit `0`, 348 passed.
- Direct registry/parity import smoke: exit `0`.
- JSON parsing and two design-schema validations: exit `0`.
- Prompt structure and revision artifact-hash checks: exit `0`.
- `git diff --check`: exit `0`.

## Ignored and untracked artifacts

The report tree is ignored by repository policy. Only the exact named report
package files in this revision are force-added. Existing ignored caches,
reports, and unrelated untracked artifacts are not absorbed.

## Remaining risk and `DATA_MISSING`

Ticket 01 is ready for a future implementation session, not complete.
Runtime functionality and live extraction correctness remain `DATA_MISSING`.
No child, review, integration, publication, deployment, canary, or runtime
proof exists.

## Next safe action

Obtain separate explicit authorization to launch one fresh Codex X implementer
from the exact hash-bound ticket-01 prompt. Do not launch the old held prompt,
and do not launch from this supervisor goal.
