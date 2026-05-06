# Label Taxonomy

## Implemented Labels

`claim_verified`

- The source directly supports a claim in the answer.
- Assigned only when source metadata or supporting evidence indicates direct claim support.

`context_only`

- The source was used for background/context, but does not directly verify a claim.
- Safe default for non-empty context that lacks direct support.

`no_hit`

- A search/tool/source path was attempted but returned no relevant evidence.
- Never treated as claim verified or source-backed.

`operational_trace`

- Tool/runtime/system trace, not financial evidence.
- Never treated as claim verifying evidence.

`local_personal_data`

- User/Cockpit-local data such as holdings.
- Not financial truth and not external source-backed evidence.

`memory_context`

- Company, market, thesis, or related memory context.
- Not canonical truth unless separately supported by a real source.

`external_web_context`

- External web result.
- Not canonical financial truth by itself.

`local_news_context`

- Local/news retrieval evidence.
- Can be paired with `claim_verified` only when the retrieved source directly supports the claim.

`financial_truth`

- Canonical financial truth or structured extracted metric evidence.
- Preserved as a separate boundary from news, memory, holdings, and web context.

`degraded_runtime`

- Answer was produced under runtime/tool/synthesis degradation.
- Surfaces at answer metadata level and prevents a fully verified presentation.

`missing_required_evidence`

- The answer has a known evidence gap.
- Used when expected local ticker-news evidence is missing or retrieval failed.

`unknown_unclassified`

- Safe fallback for unclassified sources.
- Must not render as verified.

## Assignment Sites

`financial-engine_v2/backend/app/services/tenn_chat.py`

- Assigns labels to Tenn chat source rows.
- Marks local ticker news as `local_news_context`.
- Promotes to `claim_verified` only when supporting evidence matches the source.
- Emits answer-level labels, coverage status, and evidence status.
- Emits `missing_required_evidence`, `no_hit`, and `degraded_runtime` where relevant.

`financial-engine_v2/backend/app/routes/cockpit_api.py`

- Normalizes source labels for API and stream payloads.
- Summarizes source label counts, claim verified count, evidence labels, and coverage status.
- Treats unknown/unclassified sources as non-verified.
- Treats financial truth as its own coverage status when applicable.

`financial-engine_v2/cockpit/core/agent_loop.py`

- Emits degraded runtime routing metadata for synthesis timeout and LLM failure paths.

## Serialization Sites

`financial-engine_v2/backend/app/routes/cockpit_api.py`

- Serializes normalized source metadata and routing metadata in Cockpit API responses.

`cockpit-ui/lib/api-client.ts`

- Maps snake_case source label payload fields to UI source objects.

`cockpit-ui/components/cockpit/chat/chat-screen.tsx`

- Normalizes metadata from response payloads and SSE source events.

## Rendering Sites

`cockpit-ui/components/cockpit/chat/terminal-message.tsx`

- Renders role-aware trust labels:
  - Degraded runtime
  - Claim-supported
  - Financial truth evidence
  - No-hit audit
  - Local personal data
  - Context sources only

`cockpit-ui/components/cockpit/chat/sources-drawer.tsx`

- Not changed. Metadata is now available to support a focused future drawer rendering update.
