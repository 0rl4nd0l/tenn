# Memory Dirty-Work Coordination and Route-Validation Closeout v1

## 1. Executive summary

The three dirty Memory files reported by the Cockpit route validation pass were no longer dirty at this task's preflight. Current HEAD at task start was `48a20fac6c502ca1c58ee216306c2d7ed6eaddd4`, commit subject `milestone(cockpit-ui): repair memory thesis deep link`, which preserved the Memory page/UI/test changes before this Codex closeout claim.

The preserved Memory behavior is safe Memory UI work: `/memory?tab=thesis` opens the Strategy tab, tab changes update the URL without writing product memory, and `app/memory/page.tsx` wraps the screen in `Suspense` for search-param usage. The Memory commit also updated `docs/claude/STATE.md`; that file was already part of HEAD before this task and was not changed by this closeout.

Memory commit result: no new Memory source commit was created by this task because the Memory source/test changes were already committed at `48a20fac6c50`. Targeted mocked Playwright validation passed after the commit.

Route-validation report commit result: committed separately as `e38da634385162b02a480a8d42d51269f527cda7` with subject `docs(reporting): record cockpit route validation pass`. No application code was staged in that commit.

Remaining blockers: none for this closeout. The route-validation report still records deferred follow-ups for route smoke, UI test drift, chat/news provenance smoke, and extraction runtime ambiguity.

## 2. Preflight

| item | evidence |
| --- | --- |
| Date | `2026-05-13T12:55:59+10:00` |
| Logical pwd | `/home/l4nd0/tenn` |
| Git root | `/mnt/hdd-data/home/l4nd0/tenn` |
| Branch | `preserve/dirty-work-20260430T065748Z` |
| Start HEAD | `48a20fac6c502ca1c58ee216306c2d7ed6eaddd4` |
| Start short HEAD | `48a20fac6c50` |
| Start git status | only route-validation task/report artifacts staged; new Memory closeout task card added by this task |
| Start unstaged Memory diff | none for `cockpit-ui/app/memory/page.tsx`, `cockpit-ui/components/cockpit/memory/memory-screen.tsx`, `cockpit-ui/tests/memory.spec.ts` |
| Start staged files | route-validation task/report artifacts only |
| Registry claim | acquired for `memory_dirty_work_and_route_validation_closeout_20260513` |
| Chorus | not used; only `wait_for_chat` was available and no read-only route/report inspection primitive was useful |

## 3. Memory dirty-file classification

| file | classification | behavior changed | evidence | validation | action taken |
| --- | --- | --- | --- | --- | --- |
| `cockpit-ui/app/memory/page.tsx` | INTENTIONAL_SAFE_EXTENSION, already committed | Adds `Suspense` around `MemoryScreen` so search-param hooks are valid in the page | `git show HEAD` shows `Suspense` import/wrapper in commit `48a20fac6c50` | `pnpm -C cockpit-ui exec playwright test tests/memory.spec.ts --reporter=line`: 9 passed | No new edit; classified preserved |
| `cockpit-ui/components/cockpit/memory/memory-screen.tsx` | INTENTIONAL_SAFE_EXTENSION, already committed | Parses `tab` query param, maps `thesis` to `strategy`, updates active tab, and syncs URL on tab/row navigation | `git show HEAD` shows `parseMemorySection`, `usePathname`, `useSearchParams`, and `window.history.replaceState` changes | Same mocked Memory Playwright spec passed | No new edit; classified preserved |
| `cockpit-ui/tests/memory.spec.ts` | TEST_ONLY_ALIGNMENT, already committed | Adds mocked test for `/memory?tab=thesis` opening Strategy and clearing URL on Company tab | `git show HEAD` shows new `opens the strategy section from the thesis deep link` test | Same mocked Memory Playwright spec passed | No new edit; classified preserved |

## 4. Validation

| command | result | proves | does not prove |
| --- | --- | --- | --- |
| `git diff --name-status -- cockpit-ui/app/memory/page.tsx cockpit-ui/components/cockpit/memory/memory-screen.tsx cockpit-ui/tests/memory.spec.ts` | no output | the reported Memory files were clean at this task's preflight | who committed them |
| `git show --name-status --oneline HEAD -- cockpit-ui/app/memory/page.tsx cockpit-ui/components/cockpit/memory/memory-screen.tsx cockpit-ui/tests/memory.spec.ts` | `48a20fa milestone(cockpit-ui): repair memory thesis deep link`; all three files modified | the dirty Memory files were preserved in HEAD before this task | whether every prior local edit was intentional beyond the commit message/diff |
| `pnpm -C cockpit-ui exec playwright test tests/memory.spec.ts --reporter=line` | `9 passed (21.0s)` | mocked Memory browser spec passes across configured projects | broad Cockpit UI health |
| `git diff --cached --name-status` before route commit | only route-validation task/report files staged | route commit separation | route task `check-diff` behavior |
| route staged allowlist check | no output | no non-route file staged for route commit | untracked current task card visibility to old route check-diff |
| `git diff --cached --check` before route commit | passed | no staged whitespace errors | runtime behavior |
| `python3 -m json.tool` on route `status.json` and `diff-check.json` | passed | route JSON artifacts valid | route health |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md` before route commit | failed | old route card check-diff saw the current closeout task card plus report-glob limitation | staged route commit was unsafe; explicit staged allowlist proved staged set |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md` before closeout report commit | failed only on files under `reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/` | current task card is valid and staged source paths are clean | report-glob limitation for this task's report files |

## 5. Commit separation

Memory commit files: `48a20fac6c50` contains `cockpit-ui/app/memory/page.tsx`, `cockpit-ui/components/cockpit/memory/memory-screen.tsx`, `cockpit-ui/tests/memory.spec.ts`, and `docs/claude/STATE.md`. This commit existed before this Codex closeout claim.

Reporting commit files: `e38da6343851` contains only:
- `docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/README.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/diff-check.json`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/mutating_route_gate_list.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/route_validation_matrix.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json`

Proof not mixed: `git diff --cached --name-status` and the explicit staged allowlist showed only route-validation task/report artifacts before the route commit. No Memory source/test file was staged in the route commit.

## 6. Route-validation closeout

The Cockpit route-validation task/report artifacts were committed separately as `e38da634385162b02a480a8d42d51269f527cda7`.

`check-diff` for the old route task failed before the route commit because it saw this current Memory closeout task card as untracked outside the old route card allowlist, and because the known report-glob limitation rejected the route report files. The staged allowlist showed no non-route files staged, and no application code was staged.

Final route-validation status: artifacts are preserved in git. The route-validation report's own `status.json` remains a historical artifact from the route-validation pass; this closeout report is the authoritative place for the final route commit hash.

## 7. Risks / DATA_MISSING

- DATA_MISSING: exact owner/session that created `48a20fac6c50`; current evidence only shows commit author/subject and that the commit landed before this claim.
- The Memory commit touched `docs/claude/STATE.md` in addition to the three dirty Memory files. This closeout did not alter that file.
- Skipped: `tsc --noEmit`, ESLint, and Next build were not rerun by this task because the Memory commit message records those as already run and the targeted mocked Playwright spec was rerun successfully.
- Route task `check-diff` pre-commit was not clean due the old route-card allowlist not including this current closeout task card and the report-glob limitation.

## 8. Next safe step

- Route smoke follow-up: run a stable status-code/body-shape capture for read-only Cockpit GET endpoints.
- UI test drift fixes: handle Holdings, Marketplace Mission, and Settings test drift from the route-validation report.
- Chat/news provenance smoke: design explicit, cheap POST probes or fixture-backed tests before touching live query routes.
- Extraction runtime audit: resolve 8001/8002 ambiguity under Evaluation/Financial Truth.

## 9. Project Memory save recommendation

SAVE_RECOMMENDED.

Target categories:
- Validation Baselines: Memory deep-link Playwright spec passed; route-validation artifacts committed.
- Open Risks / Blockers: route `check-diff` report-glob limitation and old-card allowlist interaction.
- Repo / GitHub / Codex Audit Notes: Memory dirty work was already preserved by `48a20fac6c50`; route-validation artifacts landed separately.

## 10. Final state

Final git status, active jobs, registry release, and closeout commit hash are completed after this report is staged and committed. Commit hashes known at report-writing time:
- Memory preservation commit: `48a20fac6c502ca1c58ee216306c2d7ed6eaddd4`
- Route-validation report commit: `e38da634385162b02a480a8d42d51269f527cda7`

Generated closeout artifacts include this README, `memory_dirty_file_classification.md`, `status.json`, and `diff-check.json`.
