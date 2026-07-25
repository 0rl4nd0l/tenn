# Tenn Codex X Extraction Programme Reconciliation

## Outcome

PR #513 remains closed as superseded. Its reviewed successor PR #521 was
squash-merged once with expected-head protection. Canonical now contains the
exact reviewed declarative metric-authority delta.

`ASXFP_01_SCORECARDS` is now `READY`; its run-package state is schema-valid
`PLANNED` with no blocker and zero attempts. The exact first-child prompt was
regenerated, but no child was launched.

## Canonical identity

- Repository: `0rl4nd0l/tenn`
- Accepted extraction canonical branch:
  `migration/clean-runtime-baseline-reconstruct-v1`
- Commit: `107c926930ef5a14783a8293bac9b47c9046bfed`
- Tree: `9e43e6380c357e1a40a23bff6d4a07522c86ff98`
- Commit subject: `refactor(extraction): adopt metric contract authority (#521)`
- Local supervisor launch branch: `deploy/canonical-runtime-v1`
- GitHub default `main`: `cc99cec1bfc4ee79aac407a8caeed8d4baec2f6b`

The extraction canonical selection is fresh: all three named extraction PRs
target the migration branch, that branch contains merged PR #517, and default
`main` does not.

## Planning inputs

- Codex X run:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589`
- Read-only planning workspace:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source`
- Specification:
  `docs/superpowers/specs/2026-07-23-asx-financial-profile-extraction-recovery.md`
- Delivery plan:
  `docs/plans/asx_financial_profile_extraction_recovery_plan.md`
- Tickets:
  `.scratch/asx-financial-profile-extraction-recovery/issues/01-*.md`
  through `18-*.md`
- ADRs: no standalone ADR files exist in the recovered planning package.
  The governing design decisions are embedded in the spec under
  `Implementation Decisions`, `Testing Decisions`, and `Out of Scope`.

The spec, plan, and tickets are untracked artifacts inside the isolated
workspace. They are planning inputs only, not current repository truth.

## Live work boundaries

- PR #517 is merged as
  `d438cb454b56b4718c5a1c4721e48831a7b107a5` and contained in canonical.
  It owns current-period source-column binding; ticket 13 is superseded rather
  than replayed.
- PR #508 is an open draft at
  `4913ef0883410fcc6436b1387fa7c17642190d05`. It owns NPAT owner attribution
  and OCI boundaries. Ticket 09 remains held.
- PR #513 is closed as superseded at
  `12ecb02fee3eebe9fd19527bc55a444502ec26d4`.
- Replacement PR #521 was squash-merged at
  `7c421ad9e7721796e07dd6427f4caf584a577155`, tree
  `17eecd8c81c3deb8c57c0565fbd13e9d31954bcc`, into canonical merge commit
  `107c926930ef5a14783a8293bac9b47c9046bfed`. Both exact-head checks passed.
  The reviewed nine-path content is exact on canonical.

## Package

- [Reconciliation table](RECONCILIATION.md)
- [Compact ledger](RECONCILIATION_LEDGER.json)
- [Artifact hashes](ARTIFACT_HASHES.json)
- [Run-package proposal](RUN_PACKAGE_PROPOSAL.md)
- [Exact held first prompt](FIRST_CHILD_PROMPT.md)
- [PR #513 disposition](PR513_DISPOSITION.md)
- [PR #521 independent review](PR521_INDEPENDENT_REVIEW.json)
- [PR #521 merge and ticket-01 refresh](PR521_MERGE_REFRESH.md)
- `proposed_run_package/run_manifest.json`
- `proposed_run_package/schema_bindings.json`
- `proposed_run_package/ticket_state/ASXFP_01_SCORECARDS.json`
- `proposed_run_package/revisions/pr513_disposition_20260724/`
- `proposed_run_package/revisions/pr521_integration_20260725/`

The original proposed run files remain the immutable terminal view pinned by
report-only commit `d5dd1dd476a496d74a5e0cf77ca26f00e03f4fb9`. Both later revisions
are additive. This revision records the authorized PR #521 merge and generates
one hash-bound prompt artifact. No Codex X child, integrator, simulator,
extraction, runtime, data, source, gold-label, store, service, or deployment
action ran.

## Validation

- Canonical identity and PR ancestry: `PASS`
- Complete planning inventory and SHA-256 hashes: `PASS`
- Standalone ADR search: `PASS`, none present
- All 18 tickets reconciled: `PASS`
- Proposed run manifest against design schema: `PASS`
- Proposed first ticket state against design schema: `PASS`
- JSON parsing, `git diff --check`, and report-only changed-path check: `PASS`
- Replacement exact-commit suites: `464 passed`, 14 existing warnings
- Independent read-only review: `PASS`, zero findings
- PR #521 checks: `lint-and-test=SUCCESS`, `scan=SUCCESS`
- Protected squash merge: `PASS`, one attempt, merge SHA `107c9269...`
- Merged-canonical registry/PR #517 tests: `348 passed`
- Parity digest: `cc042df11e1743d9cf3085020991bd6dd8f73da835a7ece2efb48edf1c9f51ce`
- Updated run manifest and ticket state schema validation: `PASS`
- Updated revision artifact hashes: `PASS`
- Child launch: `NOT_RUN`, not authorized by this supervisor goal
- Runtime functionality: `DATA_MISSING` until separately authorized canary

## Next safe action

Obtain separate explicit authorization to launch one fresh Codex X implementer
from the exact prompt under revision `pr521_integration_20260725`, sha256
`be4525a7b253cdc3a9c6aa11138365b9c9edfffeffbce3bb00d37f22117038c5`.
Do not launch the old held prompt.
