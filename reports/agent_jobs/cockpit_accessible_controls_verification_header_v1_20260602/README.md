# Cockpit Accessible Controls: Verification Header

Issue: #53

Branch: `safe/cockpit-accessible-controls-verification-header-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-accessible-controls-verification-header-v1-20260602`

## Outcome

Implemented a narrow accessible-name remediation for the Verification header.
The active ticker input, method/provider select trigger, and strict-mode switch
now have durable programmatic names while preserving existing values, handlers,
layout, and route behavior.

This is a partial remediation slice for #53, not a full issue closeout. Other
routes from the broader accessibility audit remain open or covered by separate
PRs.

## Boundaries

- No backend, extraction, retrieval, memory, Qdrant/Postgres, financial truth,
  source/evidence label, runtime/model/GPU, or service config changed.
- No adjacent active Verification route files were touched.
- No broad UI redesign was performed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_verification_header_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_verification_header_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_verification_header_v1_20260602.md --repo-root .` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the lockfile for the isolated worktree.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/verification/verification-header.test.tsx` passed: 1 file, 2 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/verification/verification-header.tsx components/cockpit/verification/verification-header.test.tsx` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` was absent in this checkout.
- Full #53 route-wide completion remains unproven; this report only covers the
  Verification header slice.
