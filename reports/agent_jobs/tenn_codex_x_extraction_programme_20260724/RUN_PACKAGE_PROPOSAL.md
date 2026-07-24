# Proposed Tenn Run Package

The directory is proposed but deliberately not materialized as executable
state because the required extraction spec and ticket set are missing.
Appending fake `ticket_planned` events or zero hashes would violate the
design contract's restartability and tamper-evidence rules.

```text
tenn_codex_x_extraction_programme_20260724/
├── run_manifest.json
├── events.jsonl
├── ticket_state/
│   └── <TICKET_ID>.json
├── prompts/
│   ├── <TICKET_ID>-implementer-01.txt
│   └── <TICKET_ID>-reviewer-01.txt
├── child_results/
│   └── <TICKET_ID>-implementer-01.json
├── review_results/
│   └── <TICKET_ID>-reviewer-01.json
├── integration_results/
│   └── <TICKET_ID>-integration-01.json
├── diffs/
├── validation/
└── scorecards/
```

## Manifest values already resolved

```json
{
  "run_id": "tenn_codex_x_extraction_programme_20260724",
  "repository": "0rl4nd0l/tenn",
  "canonical_base_sha": "2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7",
  "spec_path": "<DATA_MISSING>",
  "spec_hash": "<DATA_MISSING>",
  "ticket_set": "<DATA_MISSING>",
  "ticket_set_hash": "<DATA_MISSING>",
  "budgets": {
    "max_children": 12,
    "max_attempts_per_ticket": 2,
    "max_child_minutes": 90,
    "max_run_minutes": 720,
    "max_log_bytes": 104857600,
    "max_disk_bytes": 1073741824
  },
  "owner_boundaries": {
    "owner": "Orlando",
    "runtime_authorization": "SEPARATE_REQUIRED",
    "data_authorization": "SEPARATE_REQUIRED",
    "merge_authorization": "SEPARATE_REQUIRED",
    "deploy_authorization": "SEPARATE_REQUIRED"
  }
}
```

This block is a proposal, not `run_manifest.json`, and is intentionally not
schema-validated while required hashes are absent. The explicit owner limit of
two equivalent failed attempts is stricter than the design prototype's default
three-attempt ceiling and therefore controls this programme.

## Reconciliation-to-state rule

- A reconciled `READY` ticket becomes a design-contract `PLANNED` ticket and
  receives the first `ticket_planned` event.
- `SUPERSEDED`, `DONE`, `OVERLAPS_EXISTING`, `DEPENDS_ON`, and `DATA_MISSING`
  stay in the reconciliation ledger and do not receive implementation events.
- No event is appended until the complete ordered ticket set and its canonical
  hash are known.
- The materialized `ticket_state/<TICKET_ID>.json` is always disposable; the
  hash-chained `events.jsonl` remains authority.

## Child-result structure

Each implementer result uses
`schemas/child_result.schema.json` and additionally places the requested
commands/exits, replay evidence, scorecard deltas, risks, changed-file list, and
stop condition in separately hash-bound validation artifacts referenced by the
output patch/commit package. The base schema is not modified.

## Reviewer separation

The reviewer session ID must be fresh and different from every implementer
session ID. Its inputs are limited to:

- spec snapshot and hash,
- exact ticket and hash,
- exact reviewed diff and hash,
- child result and hash,
- validation and scorecard evidence hashes.

No supervisor or implementer transcript is an input.

## Clean export

Only a `READY_FOR_INTEGRATION` review can enter clean export. The integrator
must use a fresh checkout of the then-current canonical/integration spine,
preserve `AGENTS.md`, `.codex/`, hooks, policy/workflow/control files, reject
ignored or untracked dependencies, create one candidate commit, and bind
validation to its exact commit and tree SHA.

Required validation gates:

- changed-path scope check,
- `git diff --check`,
- focused source-case tests,
- no-write replay,
- fixed-denominator scorecard comparison,
- `present_correct`, `present_wrong_value`, `missing_expected_metric`,
  source-unbound, comparative-period, and side-effect deltas,
- independent review pass.

Runtime functionality remains `DATA_MISSING` until a separately authorized
final canary.
