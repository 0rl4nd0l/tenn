# Phase 3G Recommendation

Recommendation: `GO_PHASE3G_CONSOLIDATION_EXECUTION_TASK_CARD_DRAFT_ONLY`

## Rationale

Phase 3F found enough current evidence to define a consolidation/save plan. It
did not find evidence that the candidate files are already committed, merged, or
otherwise preserved in an authoritative baseline.

The next safe step is therefore a draft-only Phase 3G task card that describes
the exact future consolidation execution. Phase 3G must not perform actual
consolidation unless the user separately approves mutation.

## Why Other Options Were Not Selected

`GO_PROJECT_MEMORY_SAVE_BLOCK_ONLY` was not selected as the immediate next
phase because the file-level save/archive/exclude decision still needs a
task-card-shaped draft. A Project Memory save block is useful after the Phase 3G
draft or after the user approves a stable consolidation decision.

`DEFER_MANUAL_REVIEW_REQUIRED` was not selected because the current local
evidence is sufficient to draft the next task card. Manual review is still
required before actual consolidation mutation.

`DEFER_MISSING_INPUTS` was not selected because all named input paths were
available.

`REJECT_TOO_RISKY` was not selected because the next recommended step remains
draft-only and keeps runtime, backend, Cockpit, stores, dependencies, services,
tokens, production data, and trading paths forbidden.

## Phase 3G Draft Requirements

The Phase 3G draft should:

- Keep mutation mode draft-only unless the user separately approves actual
  consolidation mutation.
- Enumerate exact allowed paths for every candidate save action.
- Separate authoritative Strategy Lab docs/schema/tests from report-only
  evidence.
- Keep Phase 2B helper material pending-review and out of runtime/backend
  wiring.
- Include explicit handling for Phase 3A staged additions.
- Include explicit handling for Phase 3D and Phase 3E task cards.
- Decide whether each ignored report bundle should be force-added or left as
  external evidence.
- Exclude generated pycache files.
- Preserve the core architecture boundary:
  Tenn remains the research brain and provenance authority, QuantDinger remains
  a replaceable sidecar/comparator, and all Strategy Lab artifacts remain
  pending review unless Tenn-owned review changes them.

## Hard Stop For Future Work

Do not start production-module implementation, real adapter/client work, real
transport, artifact persistence, QuantDinger/MCP/Docker startup, token issuance,
dependency installation, backend/runtime/Cockpit wiring, DB/Qdrant/news/memory
or financial-truth writes, parser/gold-label changes, source-registry writes, or
paper/live/trading execution before the consolidation decision is resolved.
