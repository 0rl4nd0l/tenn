# Session Reload Label Persistence

## Fixed Behavior

Current-turn assistant messages now save normalized source-label metadata after the delivered response is finalized. Reload via `/api/cockpit/chat/sessions/{session_id}` returns:

- `metadata`
- `sources`
- `routing_metadata`
- `tool_traces`
- `action_preview`
- `chart`

Frontend reload maps those fields back into the same `ChatMessage` shape used by current-turn responses.

## Legacy Fallback

Older assistant rows with no metadata reload with:

- `evidence_labels=["unknown_unclassified"]`
- `claim_verified_source_count=0`
- `source_coverage_status="unknown_unclassified"`
- no visible sources

This is intentionally non-verified and cannot become `claim_verified`.

## Migration Safety

The change uses StateStore additive schema handling and does not rewrite existing session rows. No Alembic migration, Postgres migration, Qdrant operation, or live session-row rewrite was performed.
