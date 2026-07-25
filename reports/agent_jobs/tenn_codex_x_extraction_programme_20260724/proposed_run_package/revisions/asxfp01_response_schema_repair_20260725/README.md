# ASXFP Ticket 01 Strict Response Schema Repair

## Verdict

The corrected-schema implementer ran once and returned schema-valid
`DATA_MISSING`. This is implementation attempt 1 with retry count 0 because
strict admission passed and a real model turn began.

The child produced no product change, commit, patch, tests, or real scorecard.
Ticket `ASXFP_01_SCORECARDS` is now `BLOCKED` pending separate authorization.
Both earlier launches remain orchestration failures that consumed zero
attempts.

The response-format defect is repaired. Every object schema is closed with
`additionalProperties: false`. Because scorecard keys are dynamic, the six
scorecard categories now use arrays of closed records with exactly `name`,
`before`, and `after`. The top-level implementation semantics are unchanged.

## Prepared worker

The earlier run `20260725T032937Z-107c926930-fb7928` is retained as incident
evidence and already has an exclusive session-identity record. A new worker was
therefore prepared without launching Codex:

- run ID: `20260725T041849Z-107c926930-e0e992`
- writable HEAD: `107c926930ef5a14783a8293bac9b47c9046bfed`
- writable tree: `9e43e6380c357e1a40a23bff6d4a07522c86ff98`
- prompt SHA-256:
  `1bbb5077adb1fbd0c57230d931197897e68204e534c05a09d9513bf3620ee9fc`
- model-output schema SHA-256:
  `b0475bdf6b08191d6e42b0c8403a9fad0a06944e751a3d2b08d733e861b597ab`

The no-launch transport preflight passed and reported
`would_start_child=false`. The authorized launch then created exactly one
session:

- session ID: `019f978e-6163-77f3-b30c-4b124d4a029f`
- implementer status: `DATA_MISSING`
- model result hash:
  `62b30c5514db04c1ee4a985976a83a955aaf94ee9fd09ad775002847b19bfe86`

## Attempt disposition

The child used `git -C <writable-checkout> status --porcelain`. Because the
isolated checkout has launcher-owned Git metadata outside the worktree, that
command resolved the enclosing launcher control repository and reported its
`SOURCE.md` and `manifest.json` as untracked. The child stopped fail-closed.

Independent validation using the exact isolated Git metadata proves the
product checkout is clean at the pinned HEAD and tree. The changed-path set is
empty and `git diff --check` passes.

## Identity boundary

The launcher still owns both transport identifiers. It derives `run_id` from
the run directory and captures `session_id` only from
`thread.started.thread_id`. Neither identifier is accepted from model output.
The child-result envelope schema is unchanged.

## Authorization boundary

`proposed_launch_command.sh` was executed exactly once. No reviewer was
launched. No Tenn product file, runtime, data, service, PR, merge, or
deployment action occurred.

## Next safe action

Stop and request separate owner authorization before launching the proposed
read-only reviewer or attempting any retry.
