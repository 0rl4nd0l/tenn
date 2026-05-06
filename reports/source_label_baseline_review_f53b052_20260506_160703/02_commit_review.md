# Commit Review

Commit: `f53b0526a6a483c350f8ee74434b95ed3f0dc06a`

Summary: 23 files changed, 870 insertions, 27 deletions.

## File Classification

| File | Classification | What changed | Taxonomy impact | Runtime surface |
| --- | --- | --- | --- | --- |
| `financial-engine_v2/backend/app/routes/cockpit_api.py` | API model, source-label serialization, reload hydration | Added attached-source UI-source handling, persisted chat metadata helpers, extra session-message response fields, and metadata persistence after delivered responses. | Preserves existing labels; adds attached-source `context_only` propagation; does not create full taxonomy. | Contested/MEDIUM |
| `financial-engine_v2/cockpit/storage/state.py` | Session persistence | Added `metadata_json` column handling plus serialize/deserialize support for chat messages and latest-message replacement metadata. | Stores existing metadata without interpreting claims. | MEDIUM |
| `financial-engine_v2/cockpit/core/chat.py` | Backend source construction | Attached-source evidence now carries `source_type=attached_source`, `evidence_label=context_only`, `evidence_labels=["context_only"]`, `claim_verified=false`. | Narrow attached-source classification only. | MEDIUM |
| `cockpit-ui/lib/api-client.ts` | Frontend API model | Extended chat-session record type with metadata, sources, routing metadata, tool traces, actions, and chart fields. | Enables label transport; no taxonomy logic. | MEDIUM |
| `cockpit-ui/components/cockpit/chat/chat-screen.tsx` | Frontend reload hydration | Maps reloaded sources and routing metadata back into `ChatMessage` shape, including `evidenceLabel`, `evidenceLabels`, and `claimVerified`. | Preserves labels across reload; no claim verification. | MEDIUM |
| `cockpit-ui/components/cockpit/chat/terminal-message.tsx` | Source drawer/UI rendering | Replaced generic source-backed wording with role-specific source summary labels. Inline source rows show the primary evidence label. | Reduces false source-backed wording; does not verify claims. | MEDIUM |
| `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx` | Tests | Added/updated tests for verified, no-hit, and context-only wording. | Regression coverage for rendering semantics. | LOW |
| `financial-engine_v2/backend/tests/test_build_ui_sources.py` | Tests | Added attached-source context-only source test. | Covers non-verified attached sources. | LOW |
| `financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py` | Tests | Added reload persistence and legacy fallback tests. | Covers reload preservation and safe unknown fallback. | LOW |
| `financial-engine_v2/cockpit/tests/test_chat_attached_sources.py` | Tests | Checks attached source evidence metadata in keyword and agent-loop paths. | Covers attached-source labels. | LOW |
| `financial-engine_v2/cockpit/tests/test_state_chat_sessions.py` | Tests | Checks metadata round trip and latest assistant metadata replacement. | Covers persistence. | LOW |
| `reports/source_label_propagation_drawer_honesty_20260506_154915/*` | Docs/report | Records the original implementation summary, validation, gaps, and next prompt. | Explicitly says taxonomy redesign is out of scope. | LOW |

## Behavior Questions

Preserves existing labels: yes, for current-turn assistant messages that have normalized source metadata.

Introduces new taxonomy: no. Parent `51ccfd8` already contained `SOURCE_LABEL_DEFINITIONS` and `source_label_semantics_v1`; `f53b052` does not redesign it.

Affects claim verification: no verifier behavior changes. `claim_verified` remains data-driven from existing source metadata; attached sources are explicitly non-verified.

Affects source-backed labeling: yes in UI wording, by removing a generic "source-backed" sentence and rendering role-specific summaries.

Affects Holdings/local personal data labels: no Holdings routing or storage changes. Existing metadata path can preserve `local_personal_data` if present.

Affects no-hit/degraded-runtime labels: no new broad producers. Existing labels/statuses are preserved if present; non-news no-hit and deeper runtime degradation gaps remain future work.

Touches contested runtime surfaces: the reviewed commit touches `cockpit_api.py`, `cockpit/core/chat.py`, and `cockpit-ui/components/cockpit/chat/*`, so the commit itself is MEDIUM risk by the task rubric. The audit artifact write is LOW risk.
