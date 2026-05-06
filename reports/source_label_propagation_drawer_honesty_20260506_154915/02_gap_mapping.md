# Gap Mapping

## G001: Historical Reload Loses Labels

Audit finding: session reload returned content/timestamps only.

Patch mapping:
- Store normalized assistant metadata in `chat_messages.metadata_json`.
- Return metadata, sources, routing metadata, tool traces, action preview, and chart from `/api/cockpit/chat/sessions/{session_id}`.
- Frontend `toChatMessage()` maps reloaded source rows back into `ChatMessage.sources` and analyst metadata.
- Legacy assistant rows without metadata return non-verified `unknown_unclassified`.

## G002: Attached Sources Hidden From Labelled API Sources

Audit finding: attached source evidence entered prompt context but `_build_ui_sources()` had no `attached_source` branch.

Patch mapping:
- Attached-source bundle emits `evidence_label=context_only`, `evidence_labels=["context_only"]`, `claim_verified=false`.
- `_build_ui_sources()` now maps `attached_source` evidence to visible `kind=context` source rows.
- Synthetic `score=1.0` is preserved only as a UI score and does not promote to claim verification.

## G004: Generic Source-Backed UI Wording

Audit finding: terminal message footer displayed generic financial source-backed wording for any positive source count.

Patch mapping:
- Removed generic wording.
- Added role-specific summaries: `Verified sources`, `Context sources`, `Local holdings`, `Memory context`, `No relevant source found`, `Runtime degraded`, and `Evidence incomplete`.
