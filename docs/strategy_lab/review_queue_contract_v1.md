# Strategy Lab Review Queue Contract v1

Status: repo-artifacts only. No database, no worker, no scheduler, no runtime
dependency.

The review queue turns existing Strategy Lab evidence into analyst workflow
items. It does not persist review state outside versioned repo artifacts and it
does not call a sidecar.

## Queue Item Contract

Each item must include:

- stable `id`
- `label`
- `group`
- `source_path`
- `source_label`
- `provenance_label`
- `priority`
- `sort_key`
- `filter_tags`
- `review_status`
- `decision_state`
- `availability`
- `what_is_trustworthy`
- `remains_non_live`
- `promotion_blockers`
- `unresolved_risks`
- `data_missing`

Allowed `review_status` values:

- `PENDING_REVIEW`
- `BLOCKED`
- `DATA_MISSING`

Allowed source mode: `repo_artifacts_only`.

## Groups

- `repeatability_artifacts`
- `transport_contract_artifacts`
- `runtime_proof_artifacts`
- `degraded_state_artifacts`
- `cleanup_revoke_proof`
- `review_decisions`
- `promotion_blockers`
- `unresolved_risks`

## Sort And Filter Semantics

Default sort: `priority_then_sort_key`.

Supported filter facets:

- `group`
- `review_status`
- `availability`
- `priority`
- `filter_tags`

These facets are UI/reporting ergonomics only. They do not mutate review state.

## Promotion Gates

Every queue response must preserve:

```json
{
  "source_mode": "repo_artifacts_only",
  "review_status": "PENDING_REVIEW",
  "current_sidecar_available": false,
  "execution_allowed": false,
  "canonical_financial_truth": false,
  "real_transport": false
}
```

Promotion is blocked until a later approved task supplies all of:

- human review decision
- current readonly runtime proof if current availability is being claimed
- safe adapter seam review
- retry/degraded/timeout behavior review
- cleanup and revoke evidence for any runtime probe
- secret scan and no-token persistence proof
- proof that no execution, store, source-registry, parser, or canonical-truth
  surface is touched

## DATA_MISSING Rules

Use `DATA_MISSING` for absent artifacts, absent review decisions, missing
source commit refs, unavailable current runtime, missing raw payload hashes, and
unimplemented retry/timeout behavior. Do not infer or substitute these values.
