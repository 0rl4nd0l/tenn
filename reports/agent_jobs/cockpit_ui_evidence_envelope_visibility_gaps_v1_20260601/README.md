# Cockpit UI Evidence Envelope Visibility Gaps

## Summary

Implemented a bounded Reporting safe extension for GitHub issue #175.

- Chat now treats `local_news_context` as a visible evidence state.
- Expanded chat source rows render all source evidence labels, not only the primary label.
- Standalone News maps backend evidence-envelope fields from `/rag/query` payloads.
- News result rows show evidence-envelope labels when supplied and `DATA_MISSING evidence envelope` when absent.

## Boundaries

- No backend, DB, Qdrant, news store, memory store, financial truth, parser, extraction, runtime, model, GPU, or service configuration changes.
- No source-label semantics were relaxed.
- No context-only, no-hit, degraded, duplicate, snippet-only, or `DATA_MISSING` evidence is upgraded to claim-verified.
- Existing #83 and #87 backend/route ownership boundaries remain untouched.

## Validation

- Task-card validation passed.
- Registry overlap check passed before implementation.
- Registry claim was acquired in isolated worktree `/home/l4nd0/tenn-cockpit-ui-evidence-envelope-visibility-gaps-v1-20260601`.
- Focused Vitest passed: 4 files, 33 tests.
- Focused ESLint passed.
- TypeScript `tsc --noEmit` passed.
- `git diff --check` passed.
- Task-card `check-diff` passed.

## Notes

The shared checkout remained untouched. The only other active registry job observed during implementation was the unrelated Financial Truth extraction job.
