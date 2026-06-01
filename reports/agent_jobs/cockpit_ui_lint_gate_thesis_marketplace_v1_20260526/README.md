# Cockpit UI Lint Gate Thesis And Marketplace

## Summary

Implemented the focused Evaluation fix for issue #89.

- Thesis Audit alert excerpts now use escaped typographic quotes instead of raw JSX quotes.
- Thesis Audit alert dismissal uses a bare `catch` instead of an unused variable.
- Marketplace benchmark listing media keeps the raw external listing image URL, with a local documented lint exception.
- No global lint rule was disabled and no listing media behavior was changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md`
- `corepack pnpm --dir cockpit-ui exec eslint app components lib tests --max-warnings=0`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md`

## Notes

Marketplace benchmark listing media uses external marketplace evidence URLs. A local `@next/next/no-img-element` exception was kept next to the `<img>` so the UI continues rendering the source media directly without replacing evidence media with a placeholder or proxy.
