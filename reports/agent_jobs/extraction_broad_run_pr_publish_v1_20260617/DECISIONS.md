# Decisions

## Open Draft PR

Decision: open a draft PR, not ready-for-review.

Reason: the publish workflow defaults to draft PRs unless the user explicitly
asks for ready-for-review. The branch is locally reviewed, but CI and owner
review have not run remotely yet.

## Explicit Base

Decision: target `migration/clean-runtime-baseline-reconstruct-v1`.

Reason: the branch tracks and was built from that migration baseline; the repo
default is `main` but is not the requested integration target.

## No Merge

Decision: stop after branch push and draft PR creation.

Reason: merge was not approved and the task card explicitly forbids it.
