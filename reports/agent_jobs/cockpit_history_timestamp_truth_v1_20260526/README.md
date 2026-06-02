# Cockpit History Timestamp Truth

## Summary

Implemented a focused Reporting fix for issue #91.

- Document payloads without real execution timestamps now render as read-only `Document Inventory` rows.
- Missing execution time is shown as `DATA_MISSING`, with `Unknown` duration.
- Document inventory no longer appears as `document_ingestion`, `completed`, `Just now`, or `0ms`.
- Queue summary rows no longer fabricate a start time or duration.
- Summary labels now distinguish history rows from execution-backed job counters.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md`
- `corepack pnpm exec vitest run components/cockpit/history/history-screen.test.tsx`
- `corepack pnpm exec tsc --noEmit --pretty false`
- `corepack pnpm exec eslint components/cockpit/history/history-screen.tsx components/cockpit/history/history-screen.test.tsx`
- Playwright rendered check against `http://127.0.0.1:3011/history` with mocked `/api/cockpit/docs` and `/api/cockpit/queue`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md`

## Rendered Evidence

Screenshot: `/tmp/tenn-history-timestamp-truth-91.png`

The rendered row text was:

```text
doc-0 Document Inventory {"title":"BHP annual report","filename":"bhp-annual-report.pdf","published_at":"2026-05-01T00:00:00Z","execution_timestamp":"DATA_MISSING"} inventory DATA_MISSING Unknown Read-only
```

The document row had no `Just now` and no `0ms`.
