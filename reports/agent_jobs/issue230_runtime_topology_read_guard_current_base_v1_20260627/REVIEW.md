# Review

## Self-Review

Findings: none requiring code changes.

Checked:

- Backend route guard is route-specific to `/config`, `/models`, and `/queue`.
- RED backend tests fail for the expected root cause and GREEN backend tests
  pass after the route decorators are guarded.
- Browser config/model/queue helper calls send `X-API-Key`.
- Direct browser `/api/cockpit/config` fetches under `cockpit-ui/components`
  were searched and updated inside the task-card allowlist.
- The diff does not touch runtime/model/GPU/service config, DB/Qdrant/Redis,
  extraction prompts, gold labels, source PDFs, or production data.

Residual risk:

- Local frontend Vitest/ESLint could not run because `vitest` and `eslint` are
  not installed in `cockpit-ui/node_modules` in this checkout.
- No live backend/Cockpit runtime smoke was run.
