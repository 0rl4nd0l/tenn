# Next Codex Prompt: Reporting UI Source Drawer

## Lane

Reporting

## Execution Mode

SAFE EXTENSION MODE

## Goal

Update the Cockpit source drawer to render the evidence/source label metadata introduced by Source Label Semantics v1 without changing backend retrieval, synthesis, memory, ingestion, Qdrant, news.sqlite, or financial truth behavior.

## Suggested Scope

Allowed likely files:

- `cockpit-ui/components/cockpit/chat/sources-drawer.tsx`
- `cockpit-ui/components/cockpit/chat/sources-drawer.test.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx` only if needed for shared formatting
- `cockpit-ui/lib/cockpit-types.ts` only if additional UI-only display fields are required

## Requirements

- Render `claim_verified` distinctly from `context_only`.
- Render `no_hit`, `missing_required_evidence`, and `degraded_runtime` as audit/gap states, not verified evidence.
- Render `local_personal_data` as cockpit-local/personal data, not financial truth.
- Render `memory_context` as memory context, not claim-verified evidence.
- Render `external_web_context` as external context, not canonical financial truth.
- Render `local_news_context` as local news context.
- Preserve compact drawer layout and existing source interactions.

## Validation

Run focused UI tests:

```bash
pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/sources-drawer.test.tsx components/cockpit/chat/terminal-message.test.tsx
pnpm --dir cockpit-ui exec tsc --noEmit
git diff --check
```

Record any unrelated existing UI failures separately and do not fix them in the Reporting lane unless directly required by source drawer label rendering.
