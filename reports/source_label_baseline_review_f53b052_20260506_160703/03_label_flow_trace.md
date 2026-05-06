# Label Flow Trace

## Current Flow

Backend source construction:

- Chat evidence is normalized by `_build_ui_sources()` and `_normalize_source_item()` in `cockpit_api.py`.
- Labels are normalized against `SOURCE_LABEL_DEFINITIONS`.
- `claim_verified` is set only when `claim_verified`/`supports_claim` is true or a source already carries that valid label.
- Attached sources now enter `_build_ui_sources()` as `context_only` and `claim_verified=false`.

API model serialization:

- `_build_chat_ui_metadata()` emits `source_label_taxonomy_version`, `source_label_counts`, `evidence_labels`, `claim_verified_source_count`, and `source_coverage_status`.
- `CockpitChatMessageRecord` now exposes `metadata`, `sources`, `routing_metadata`, `tool_traces`, `action_preview`, and `chart`.

Session persistence / reload:

- `StateStore` stores chat metadata in `chat_messages.metadata_json`.
- `_finalize_delivered_chat_response()` updates the latest persisted assistant row with the delivered text and metadata.
- Reload via `/api/cockpit/chat/sessions/{session_id}` returns saved sources and routing metadata.
- Legacy assistant rows without metadata reload as `unknown_unclassified`, zero claim-verified sources, and no visible sources.

Frontend API client hydration:

- `api-client.ts` allows the extra session-message fields.
- `chat-screen.tsx` maps reloaded `sources`, `routing_metadata`, tool traces, action preview, and chart into `ChatMessage`.

Source drawer / terminal rendering:

- Inline source rows display the source primary evidence label.
- Analyst shell summary uses role-specific wording such as `Verified sources`, `Context sources`, `No relevant source found`, `Runtime degraded`, or `Evidence incomplete`.
- The separate `sources-drawer.tsx` recent-source attachment drawer was not redesigned.

## Required Answers

Are source labels preserved across reload? Yes for newly saved/current-turn assistant messages. Legacy rows without metadata use a safe non-verified fallback.

Are source labels preserved in drawer display? Yes for the visible chat message source list because reloaded source rows preserve `evidenceLabel`/`evidenceLabels` and the source row renders the primary label. The recent-source attachment drawer is not a provenance drawer and remains unchanged.

Are labels normalized or transformed? Raw evidence labels are normalized during source construction against the current valid label set. Reload/hydration then transports saved labels without reclassifying them.

Are unknown labels dropped? During source construction, labels outside the valid set are ignored; if no valid label remains, the source becomes `unknown_unclassified`. During reload, already-persisted label strings are not dropped by the frontend.

Does reload collapse label kind into generic source-backed? No. Reload preserves `evidence_labels`, `evidence_label`, `claim_verified`, and `source_coverage_status`; UI wording no longer uses the generic source-backed sentence for all sources.

Are no-hit/operational/local-personal/degraded labels preserved if present? Yes in the metadata/source records that are persisted. This commit does not make every producer emit those labels.

Does this commit merely preserve labels, or create the taxonomy? It preserves and propagates labels. The taxonomy definitions already existed in the parent commit; full Source Label Semantics v1 remains future work.
