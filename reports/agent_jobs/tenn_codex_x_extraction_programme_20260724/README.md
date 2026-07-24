# Tenn Codex X Extraction Programme Reconciliation

## Outcome

Reconciliation is complete and stopped before child launch.

The completed planning set was recovered from an isolated Codex X workspace,
hashed, and compared with canonical Tenn and live PRs #508, #513, and #517.
There is no currently launchable `READY` ticket. The earliest useful ticket,
`ASXFP_01_SCORECARDS`, overlaps open draft PR #513 in the real-gold evaluator
and scorecard contract. Launching it now would risk defining a denominator
against an unresolved metric authority.

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
- PR #513 is an open draft at
  `12ecb02fee3eebe9fd19527bc55a444502ec26d4`. It owns declarative
  metric-contract authority and changes evaluator/persistence consumers.
  Tickets 01, 04, 05, 06, 08, and 09 cannot safely advance across that
  unresolved authority.

## Package

- [Reconciliation table](RECONCILIATION.md)
- [Compact ledger](RECONCILIATION_LEDGER.json)
- [Artifact hashes](ARTIFACT_HASHES.json)
- [Run-package proposal](RUN_PACKAGE_PROPOSAL.md)
- [Exact held first prompt](FIRST_CHILD_PROMPT.md)
- `proposed_run_package/run_manifest.json`
- `proposed_run_package/schema_bindings.json`
- `proposed_run_package/ticket_state/ASXFP_01_SCORECARDS.json`

No child, reviewer, integrator, simulator, extraction, runtime, data, source,
gold-label, prompt-bundle, store, service, merge, or deployment action ran.
No product file or PR was modified.

## Validation

- Canonical identity and PR ancestry: `PASS`
- Complete planning inventory and SHA-256 hashes: `PASS`
- Standalone ADR search: `PASS`, none present
- All 18 tickets reconciled: `PASS`
- Proposed run manifest against design schema: `PASS`
- Proposed first ticket state against design schema: `PASS`
- JSON parsing, `git diff --check`, and report-only changed-path check: `PASS`
- Child launch: `NOT_RUN`, required stop on unresolved overlap
- Runtime functionality: `DATA_MISSING` until separately authorized canary

## Next safe action

Obtain an exact owner disposition for PR #513: merge it onto the accepted
canonical spine, close/supersede it, or explicitly park its scorecard and
persistence-consumer scope. Then refresh canonical and re-reconcile ticket 01
against the resulting metric-contract authority. Do not launch the held prompt
against the current spine.
