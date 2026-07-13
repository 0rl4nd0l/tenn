# Decisions

## Compatibility

Legacy cards without `control_contract_version`, and explicit integer V1
cards, remain valid with migration warnings. Invalid declared versions and
invalid V2 contracts fail closed.

## Semantic Identity

The scope fingerprint is computed rather than accepted from a card. Evidence
hashes are canonicalized before fingerprinting so prefix, case, or surrounding
whitespace cannot manufacture a new scope.

## Separate State Machines

Task claims answer who is working. Decision entries answer what the evidence
proved. A completed task does not imply a changed proof question, and an older
resolved decision cannot outrank a later exact conflict.

## Track Isolation

Prospective-readiness evidence blocks only its declared dependent transitions.
It does not consume the two allowed no-delta continuations for unrelated
offline research. Offline fitting, model persistence, and promotion remain
separate capabilities and transitions.

## Closeout

`ADVANCED` requires semantic change, not file creation. Terminal/no-progress
outcomes require an exact `resume_only_if`, forbid continuation artifacts, and
reuse existing evidence. V2 board fields must agree with `RUN_OUTCOME.json`.

## Bootstrap

The first V2 run in a repository uses an explicit, idempotent initializer for
the shared decision ledger. Initialization creates only the missing empty
ledger, never truncates an existing one, and remains distinct from appending a
decision.

## Deferred Optimization

Single-pass ledger indexing is deferred. It is a performance optimization, not
a correctness requirement for this bounded rollout.
