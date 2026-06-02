# Cockpit Accessible Controls: Verification Header Clean Replacement

Issue: #53

Supersedes polluted slice: PR #199

Branch: `safe/cockpit-accessible-controls-verification-header-clean-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-accessible-controls-verification-header-clean-v1-20260602`

## Outcome

Implemented a clean, UI-only accessible-name remediation for the Verification
header from `origin/migration/clean-runtime-baseline-reconstruct-v1`. The active
ticker input, method/provider select trigger, and strict-mode switch now have
durable programmatic names while preserving existing values, handlers, layout,
and route behavior.

This is a partial remediation slice for #53, not a full issue closeout. Other
routes from the broader accessibility audit remain open or covered by separate
PRs.

## Why This Replacement Exists

PR #199 contains the intended Verification header UI change, but current live
PR evidence shows it also carries a large unrelated extraction diff against the
remote migration baseline. This branch recreates only the UI slice so it can be
reviewed and merged without backend/extraction drift.

## Boundaries

- No backend, extraction, retrieval, memory, Qdrant/Postgres, financial truth,
  source/evidence label, runtime/model/GPU, or service config changed.
- No adjacent active Verification route files were touched.
- No broad UI redesign was performed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py list-active` passed with no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the lockfile.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/verification/verification-header.test.tsx` passed: 1 file, 2 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/verification/verification-header.tsx components/cockpit/verification/verification-header.test.tsx` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.
- `python3 -m json.tool` passed for the report JSON files.
- `git diff --check` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .` passed.

## DATA_MISSING

- Full #53 route-wide completion remains unproven; this report only covers the
  Verification header slice.
