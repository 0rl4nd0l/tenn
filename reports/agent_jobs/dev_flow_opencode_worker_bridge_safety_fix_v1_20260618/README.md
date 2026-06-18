# OpenCode Worker Bridge Safety Fix

## Status

VALIDATING: implementation is complete and local checks have passed. PR creation
is pending commit and push.

## Objective

Patch the merged OpenCode worker bridge so evidence-only attach mode fails
closed without remote readonly proof, and result validation treats the requested
decision limit as authoritative.

## Constraints

- Scope is limited to the bridge script, bridge tests, optional bridge skill
  clarification, this task card, and this report bundle.
- No Tenn product/runtime/data/extraction/count-24 files.
- No host-global mutations.
- No dependency or lockfile edits.
- Do not merge PRs.

## Evidence

- PR #370 is merged into `migration/clean-runtime-baseline-reconstruct-v1`.
- New Codex Review comments on commit `e8459ab9` identify attach-mode proof and
  decision-limit mismatch issues.
- Live and durable task ledgers were unavailable (`DATA_MISSING`), so fallback
  duplicate-work searches covered task cards, reports, branches, worktrees, PRs,
  and the intended bridge files.

## Validation

Local validation passed. See `VALIDATION.md`.
