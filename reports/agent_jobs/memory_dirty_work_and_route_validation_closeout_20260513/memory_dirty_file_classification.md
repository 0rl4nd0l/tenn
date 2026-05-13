# Memory Dirty File Classification

## Summary

The reported dirty Memory files were clean by the time this closeout task began. They had already been committed at `48a20fac6c502ca1c58ee216306c2d7ed6eaddd4` with subject `milestone(cockpit-ui): repair memory thesis deep link`.

## Classification Table

| file | classification | safe? | reason |
| --- | --- | --- | --- |
| `cockpit-ui/app/memory/page.tsx` | INTENTIONAL_SAFE_EXTENSION | yes | Adds `Suspense` around `MemoryScreen` to support search-param hooks. No product memory write path is added. |
| `cockpit-ui/components/cockpit/memory/memory-screen.tsx` | INTENTIONAL_SAFE_EXTENSION | yes | Adds URL/query-state synchronization for Memory tabs and maps legacy/deep-link `tab=thesis` to the existing Strategy section. No API mutation route is introduced. |
| `cockpit-ui/tests/memory.spec.ts` | TEST_ONLY_ALIGNMENT | yes | Adds a mocked Playwright regression for `/memory?tab=thesis` opening Strategy and clearing the query when Company is selected. |

## Behavior

Confirmed from commit diff:
- `/memory?tab=thesis` initializes the Memory screen on the Strategy tab.
- Selecting Company removes the `tab` query parameter.
- Selecting non-default sections writes `?tab=<section>` into local browser history.
- Row and level navigation use the same tab-state helper.
- The page adds a `Suspense` wrapper required by Next/search-param usage.

## Mutation Assessment

The preserved change is UI/read-state only. It mutates browser URL history but does not write product memory, does not apply/confirm/reject thesis proposals, and does not call memory add/expire routes.

## Validation

`pnpm -C cockpit-ui exec playwright test tests/memory.spec.ts --reporter=line` passed: `9 passed (21.0s)`.

The spec is mocked for relevant Cockpit routes, including `/api/cockpit/memory/index`, `/api/cockpit/memory`, and `/api/cockpit/memory/company-dump`. It does not write product memory.

## Action Taken

No Memory source/test changes were edited by this closeout task. The already-preserved Memory commit was accepted as the Memory dirty-work outcome. The route-validation report artifacts were committed separately.
