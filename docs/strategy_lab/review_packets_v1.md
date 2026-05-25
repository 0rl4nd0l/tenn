# Strategy Lab Review Packets v1

Status: markdown/json report artifacts only.

Review packets provide portable analyst-review summaries. They do not send data
externally, write Tenn stores, create an artifact database, or promote sidecar
availability.

## Packet Types

- `experiment_review_packet`
- `repeatability_summary_packet`
- `risk_summary_packet`
- `artifact_provenance_packet`
- `cleanup_revoke_audit_packet`

## Required Packet Invariants

Every packet must include:

```json
{
  "review_status": "PENDING_REVIEW",
  "source_mode": "repo_artifacts_only",
  "current_sidecar_available": false,
  "execution_allowed": false,
  "canonical_financial_truth": false,
  "real_transport": false
}
```

## Allowed Outputs

- Markdown report artifacts.
- JSON report artifacts.
- Optional readonly Cockpit display.

## Forbidden Outputs

- External delivery.
- Database persistence.
- Runtime scheduling.
- Live transport calls.
- Execution or order action.
- Canonical-truth promotion.
