---
job_id: cockpit_next_theme_hydration_v1_20260522
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_next_theme_hydration_v1_20260522.md
  - reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522/
  - reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522/README.md
  - reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522/status.json
  - reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522/validation.json
  - reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522/diff-check.json
  - cockpit-ui/app/layout.tsx
  - cockpit-ui/components/theme-provider.tsx
  - cockpit-ui/tests/smoke.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_next_theme_hydration_v1_20260522
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Next Theme Hydration V1

Fix or conclusively narrow the Next dev hydration warning:

`A tree hydrated but some attributes of the server rendered HTML didn't match the client properties`

Observed diff:

`<html lang="en" className="dark" - style={{color-scheme:"dark"}}>`

## Scope

- Inspect root layout and theme provider only.
- Prefer a minimal app-shell/theme fix that stops root `<html>` attribute mismatch.
- Preserve current dark-only Cockpit appearance.
- Keep existing Cockpit smoke behavior and selectors intact.

## Forbidden

- No Cockpit Home feature edits.
- No backend, runtime, memory, truth, database, Qdrant, parser, provider, lockfile, dependency, Strategy Lab, Marketplace, or Thesis Audit changes.
- No cleanup, deletion, moving, or staging of unrelated task-card artifacts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_next_theme_hydration_v1_20260522.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_next_theme_hydration_v1_20260522.md`
- `git diff --check`
- targeted ESLint for changed files
- TypeScript
- Playwright smoke on a temporary local port
- verify dev-server output no longer includes the root `color-scheme` hydration warning
- Next build if practical
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_next_theme_hydration_v1_20260522.md`
