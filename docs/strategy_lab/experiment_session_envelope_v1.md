# Strategy Lab Experiment Session Envelope v1

Status: read-only design and reporting contract.

An experiment session is a review envelope over offline evidence. It is not a
job runner, backend orchestrator, queue worker, persistent sidecar manager, or
transport adapter.

## Required Fields

- `session_id`
- `label`
- `review_status`
- `current_sidecar_available`
- `execution_allowed`
- `canonical_financial_truth`
- `real_transport`
- `session_status`
- `source_commit_ref`
- `source_worktree_ref`
- `evidence_timestamps`
- `runtime_proof_refs`
- `reprobe_refs`
- `degraded_state_refs`
- `cleanup_proof_refs`
- `revoke_proof_refs`
- `review_decision_refs`
- `promotion_blockers`
- `unresolved_risks`
- `data_missing`

## Invariants

- `review_status` is `PENDING_REVIEW`.
- `current_sidecar_available` is `false`.
- `execution_allowed` is `false`.
- `canonical_financial_truth` is `false`.
- `real_transport` is `false`.
- All refs are repo paths or `DATA_MISSING`.
- Missing refs remain `DATA_MISSING`; they are never fabricated.

## Clean Re-Probe Session

The first session is:

`stratlab_qd_clean_reprobe_readonly_20260525`

It groups:

- runtime proof refs
- exact backtest/regime reprobe payload refs
- sidecar-unavailable and timeout degraded-state fixture refs
- cleanup proof refs
- revoke proof refs
- review/export packet refs

## Non-Goals

- No runtime startup.
- No sidecar process lifecycle.
- No backend orchestration.
- No persistent artifact store.
- No live/MCP transport.
- No token management.
- No execution or order path.
