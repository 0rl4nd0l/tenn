# Merge Parking Registry

Merge parking is a repo-native holding area for completed, validated, frozen
work that is not yet merged. It makes a branch and its evidence visible for
later review without granting permission to merge it.

Parking is not merge approval. A later agent or human reviewer must read the
task card, report, diff, validation results, branch/head, and registry state
before any merge, cherry-pick, rebase, or other integration decision.

This registry is documentation and validation only. It does not create Git refs,
claim branches, merge work, cherry-pick commits, rebase branches, reset or stash
changes, delete branches, or clean files.

## Status Labels

- `PARKED_READY_FOR_REVIEW`: validation evidence exists and the branch is ready
  for review, not automatic merge.
- `PARKED_BLOCKED_BY_DEPENDENCY`: the branch is complete but waits on another
  task, branch, decision, or artifact.
- `PARKED_NEEDS_REBASE`: the branch likely needs a later rebase or replay
  review before integration.
- `PARKED_NEEDS_VALIDATION`: evidence is incomplete or stale and must be rerun.
- `PARKED_NEEDS_HUMAN_DECISION`: a human decision is required before review can
  progress.
- `PARKED_SUPERSEDED`: another branch or task replaced this parked item.
- `MERGED`: the parked item was integrated after review.
- `REJECTED`: review decided not to integrate it.
- `ABANDONED`: the item is intentionally left behind without integration.

## Freeze Rule

Once a branch is parked, it should not receive unrelated changes. If additional
work is needed, create a follow-up task card or a new branch. If the parked
branch must change, update the parking entry with the new head, validation
evidence, and reason.

## Review Rule

A later merge/replay agent must inspect all of the following before acting:

- task card and allowed files
- report directory
- branch and current head
- diff against the intended base
- validation commands and results
- registry state and blockers
- `data_missing` entries
- `next_agent_should` and `next_agent_must_not`

The reviewer must not treat `ready_for_merge: true` as approval. It only means
the entry claims it is ready to be reviewed.

## Safe Continuation

Safe continuation after parking means:

- continue from the parked branch only after reading the parking entry and task
  report
- re-run focused validation if the base branch moved or validation is stale
- create a new task card for integration, rebase, or replay work
- preserve all product/runtime/financial-truth/memory boundaries

## Files

- `REGISTRY.md` is the human-readable index.
- `_entry_template.md` is the starting point for one parked item.
- `merge_parking_entry_schema_v1.json` validates entry frontmatter or JSON.
- `registry_schema_v1.json` validates `REGISTRY.md` frontmatter or JSON.
- `scripts/merge_parking_registry.py` validates explicit paths or changed files
  only.
