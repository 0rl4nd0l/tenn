# Proposed Tenn Run Package

## Location

`reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/`

```text
proposed_run_package/
├── run_manifest.json
├── schema_bindings.json
├── prompts/
│   └── ASXFP_01_SCORECARDS-implementer-01.held.txt
├── ticket_state/
│   └── ASXFP_01_SCORECARDS.json
└── revisions/
    ├── pr513_disposition_20260724/
    │   ├── run_manifest.json
    │   ├── schema_bindings.json
    │   └── ticket_state/
    │       └── ASXFP_01_SCORECARDS.json
    └── pr521_integration_20260725/
        ├── README.md
        ├── artifact_hashes.json
        ├── run_manifest.json
        ├── schema_bindings.json
        ├── revision_summary.json
        ├── prompts/
        │   └── ASXFP_01_SCORECARDS-implementer-01.txt
        └── ticket_state/
            └── ASXFP_01_SCORECARDS.json
```

The original manifest and ticket state remain the immutable terminal view
pinned by report-only commit `d5dd1dd...`. The additive disposition revision
records PR #513 closed as superseded and PR #521 accepted as the then-unmerged
successor. The additive PR #521 integration revision records the protected
squash merge, refreshed canonical identity/tree, parity verification, and the
ticket-01 transition to schema-valid `PLANNED`, classified `READY`.

No `events.jsonl` is fabricated: this is still a pre-launch package, not a
started orchestrator run. One artifact-derived child prompt was regenerated
because ticket 01 is now `READY`, but no child/session/result instance exists.
A materialized ticket state never substitutes for the future hash-chained
ledger.

## Result structures

`schema_bindings.json` pins all five design schemas:

- run manifest;
- ticket state;
- child result;
- review result;
- clean-export integration result.

Child, review, and integration result arrays are empty because no corresponding
session ran. Creating placeholder instances would fabricate session IDs,
timestamps, output hashes, reviews, and integration evidence. When work is
authorized, each fresh session writes one immutable schema-valid instance.

The implementer evidence bundle must hash-bind the base schema's output to the
requested changed files, commands/exits, replay evidence, scorecard deltas,
risks, and stop condition. The reviewer receives only the spec, ticket, exact
diff, child result, and validation hashes. The clean exporter uses a distinct
fresh session and a fresh checkout.

## Transition and restart rules

- Only a reconciled `READY` ticket enters `PLANNED`.
- Ticket 01 is `READY`, represented as schema state `PLANNED`; no attempt or
  retry occurred.
- At most two equivalent failed implementation attempts are permitted.
- Equivalent scope is keyed by ticket, allowed-scope hash, and input hashes.
- Any scope/evidence change creates a new ticket/run revision rather than
  resetting counters.
- Restart rebuilds compact state from immutable artifacts and the future
  hash-chained ledger, never from transcripts.

## Reviewer separation

The reviewer must be a different fresh Codex X session from every implementer.
It is read-only and receives no supervisor or implementer transcript. A
`READY_FOR_INTEGRATION` result must bind the exact reviewed output hash.

## Clean export

Clean export starts only after independent review passes. It must:

- refresh the live canonical/integration spine;
- use a fresh clean checkout;
- reconstruct only the accepted ticket delta;
- preserve `AGENTS.md`, `.codex/`, hooks, workflows, policies, and newer
  canonical work;
- reject ignored and untracked dependencies;
- bind validation logs to the exact candidate commit and tree SHA;
- pass changed-scope checks, `git diff --check`, focused tests, no-write replay,
  fixed-denominator scorecard comparison, and independent review.

Publication, future merges, child launch, runtime, data, source PDFs, gold
labels, stores, services, deployment, canary, and backfill remain separately
authorized.
