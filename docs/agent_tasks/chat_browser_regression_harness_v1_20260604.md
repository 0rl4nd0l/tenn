---
job_id: chat_browser_regression_harness_v1_20260604
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_browser_regression_harness_v1_20260604.md
  - reports/agent_jobs/chat_browser_regression_harness_v1_20260604/README.md
  - reports/agent_jobs/chat_browser_regression_harness_v1_20260604/status.json
  - reports/agent_jobs/chat_browser_regression_harness_v1_20260604/validation.json
  - reports/agent_jobs/chat_browser_regression_harness_v1_20260604/diff-check.json
  - cockpit-ui/lib/chat-browser-harness.test.ts
  - cockpit-ui/tests/chat-browser-harness.ts
  - cockpit-ui/tests/chat-browser-regression.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/chat_browser_regression_harness_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Chat Browser Regression Harness

## Objective

Move `/full-chat` browser regression route mocks, SSE fixture generation, parity
report writing, common chat actions, and route smoke helpers behind one reusable
Playwright harness interface.

## Allowed Implementation

- Add a reusable Playwright harness for the existing chat browser regression
  scenarios.
- Keep scenario code declarative: tests should describe behavior, while route
  mocks, SSE streams, report writing, and common assertions live in the harness.
- Add focused unit tests for pure harness behavior such as SSE stream generation
  and parity report rendering.
- Preserve existing mocked browser regression coverage and non-destructive route
  behavior.

## Forbidden

- No backend, DB, Qdrant, memory-store, financial truth data, runtime-service,
  embedding, extraction, ingestion, schema, vector, or production data changes.
- No frontend product UI changes outside the browser regression test harness.
- No `MultipassResult` contract work in this slice.
- No cleanup or absorption of unrelated worktree dirt from other checkouts.

## Validation

- Validate this task card.
- Check and claim the shared registry before implementation.
- Run focused harness unit tests.
- Run the focused chat browser regression Playwright test where practical.
- Run TypeScript/ESLint on touched frontend test files.
- Run `git diff --check`.
- Run `check-diff` before closeout.
