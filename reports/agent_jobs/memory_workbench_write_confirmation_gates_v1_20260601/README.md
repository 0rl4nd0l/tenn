# Memory Workbench Write Confirmation Gates V1

Issue: #154

Branch: `safe/memory-workbench-write-confirmation-gates-v1-20260602`

Worktree:
`/home/l4nd0/tenn-memory-workbench-write-confirmation-gates-v1-20260602`

## Outcome

Implemented a bounded Memory Workbench confirmation gate for the web write
path. The slice keeps Cockpit as a client/orchestration layer and does not
create frontend-owned memory state.

Every Memory Workbench write path is now classified by route-specific intent:

| Path | Intent |
| --- | --- |
| company add | `company-memory-add` |
| company expire | `company-memory-expire` |
| sector add | `sector-memory-add` |
| sector expire | `sector-memory-expire` |
| macro add | `macro-memory-add` |
| macro expire | `macro-memory-expire` |
| safe edit expire plus add | expire intent plus add intent for row kind |
| thesis proposal create | `thesis-proposal-create` |
| thesis proposal confirm | `thesis-proposal-confirm` |
| thesis proposal reject | `thesis-proposal-reject` |
| thesis proposal apply | `thesis-proposal-apply` |

## Contract

The UI now requires a visible browser confirmation before submitting a mutating
Memory Workbench action. The BFF requires both:

- `X-Cockpit-Memory-Write-Intent: <route-specific-intent>`
- JSON body fields `intent` and `confirmation: "reviewed-memory-write"`

Missing or incorrect evidence is rejected before the BFF proxies to backend
memory routes.

## Boundaries

- Backend memory ownership remains unchanged.
- User-thesis proposal apply remains limited to the existing backend proposal
  state machine.
- No production data, memory store, Qdrant, Postgres, news, extraction,
  parser, prompt, gold-label, runtime, model, GPU, or service config was
  changed.
- Direct backend `/api/context/memory*` and `/api/context/thesis*` API-key
  routes were not changed in this slice; the implemented gate covers the
  Cockpit Memory Workbench web path.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --write-report` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --repo-root .` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the lockfile for the isolated worktree.
- `corepack pnpm --dir cockpit-ui exec vitest run lib/memory-write-routes.test.ts components/cockpit/memory/memory-screen.test.tsx` passed: 2 files, 6 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/memory/memory-screen.tsx components/cockpit/memory/memory-screen.test.tsx lib/memory-write-routes.test.ts app/api/cockpit/memory/_write-intent.ts app/api/cockpit/memory/company/add/route.ts app/api/cockpit/memory/company/expire/route.ts app/api/cockpit/memory/market/add/route.ts app/api/cockpit/memory/market/expire/route.ts app/api/cockpit/memory/thesis/proposals/route.ts app/api/cockpit/memory/thesis/proposals/[proposalId]/confirm/route.ts app/api/cockpit/memory/thesis/proposals/[proposalId]/reject/route.ts app/api/cockpit/memory/thesis/proposals/[proposalId]/apply/route.ts` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.
- `git diff --check` passed.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` was absent in this checkout.
- Open PR #165 also touches `memory-screen.tsx` with three accessible-name
  additions. This branch avoids those hunks, but should be revalidated after
  #165 merges.
