# Cockpit News Context Date Filter Follow-Up v1 - 2026-06-09

## Summary

Completed the bounded follow-up from the PR #335 code review.

Changes:

- Direct SQLite news-context fallback now applies inclusive `date_from` and
  `date_to` day bounds before returning hits.
- Cockpit UI no-backend startup warning now distinguishes backend-disabled
  behavior from SQLite news-context fallback availability.
- Focused tests cover the date-bound fallback and the no-backend warning text.

## Scope Boundary

- No GitHub issues, PRs, labels, comments, closes, or merges were mutated.
- No DB, Qdrant, Redis, news-store, extraction, prompt, gold-label, model/GPU,
  or production data mutation was performed.
- No stash was popped, dropped, cleaned, or overwritten.

## Validation Summary

- Task-card validation: PASS.
- Registry read-only check: PASS, no active jobs.
- Focused router and warning tests: PASS, `10 passed`.
- Config router tests: PASS, `7 passed`.
- Ruff on touched runtime/test files: PASS.
- `git diff --check`: PASS.

## Known Unrelated Test Note

Running the entire `scripts/test_cockpit_chat_status_widgets.py` file surfaced
an existing assertion mismatch unrelated to this follow-up:
`Model Runtime: test-model` expected while the current UI renders
`Model runtime: test-model`. This follow-up did not change that runtime panel
copy.
