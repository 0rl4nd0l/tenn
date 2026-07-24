# Tenn Codex X Extraction Programme Reconciliation

## Outcome

PR #513 has the exact disposition `ADOPT_SUCCESSOR` and is closed as
superseded. Fresh draft PR #521 carries the isolated declarative
metric-authority delta on exact canonical `2f5a8aac...`; its exact-head local
validation, independent review, and GitHub checks pass.

There is still no launchable `READY` ticket. `ASXFP_01_SCORECARDS` is now
`DEPENDS_ON_SUCCESSOR_INTEGRATION`: the ambiguity is resolved, but canonical
does not contain PR #521. No child was launched.

## Canonical identity

- Repository: `0rl4nd0l/tenn`
- Accepted extraction canonical branch:
  `migration/clean-runtime-baseline-reconstruct-v1`
- Commit: `2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7`
- Tree: `cba105b2ff945fb0279158c7f54de2bcf4517e5d`
- Commit subject: `fix(runtime): resolve llama symlink library path (#518)`
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
- Replacement draft PR #521 is open at
  `7c421ad9e7721796e07dd6427f4caf584a577155`, tree
  `17eecd8c81c3deb8c57c0565fbd13e9d31954bcc`. Both checks pass. It owns the
  accepted behavior-preserving declarative metric-contract authority delta but
  remains unmerged.

## Package

- [Reconciliation table](RECONCILIATION.md)
- [Compact ledger](RECONCILIATION_LEDGER.json)
- [Artifact hashes](ARTIFACT_HASHES.json)
- [Run-package proposal](RUN_PACKAGE_PROPOSAL.md)
- [Exact held first prompt](FIRST_CHILD_PROMPT.md)
- [PR #513 disposition](PR513_DISPOSITION.md)
- [PR #521 independent review](PR521_INDEPENDENT_REVIEW.json)
- `proposed_run_package/run_manifest.json`
- `proposed_run_package/schema_bindings.json`
- `proposed_run_package/ticket_state/ASXFP_01_SCORECARDS.json`
- `proposed_run_package/revisions/pr513_disposition_20260724/`

The original proposed run files remain the immutable terminal view pinned by
report-only commit `d5dd1dd476a496d74a5e0cf77ca26f00e03f4fb9`. The disposition
revision is additive. No Codex X child, integrator, simulator, extraction,
runtime, data, source, gold-label, prompt-bundle, store, service, merge, or
deployment action ran.

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
- Child launch: `NOT_RUN`, required stop pending canonical integration
- Runtime functionality: `DATA_MISSING` until separately authorized canary

## Next safe action

Obtain separate authorization to merge draft PR #521 at exact head
`7c421ad9e7721796e07dd6427f4caf584a577155`. After merge, refresh canonical,
create another run revision, verify the authority and parity digest on that
canonical SHA, and reclassify only the residual ticket 01 gap. Do not launch
the old held prompt.
