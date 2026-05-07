# Cockpit Home Contract Design V1

Lane: Reporting
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: SAFE EXTENSION
Intended files:
- `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `reports/agent_jobs/cockpit_home_contract_design_v1/**`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
Contested surfaces touched: none
Collision risk: MEDIUM because a separate active same-lane Reporting job exists with disjoint files
Decision: proceeded after explicit user instruction, with edits limited to allowed files; scaffold committed on current HEAD

## 1. Branch / HEAD / Worktree / Dirty Status

- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD: `b9f4d353a186`
- Worktree: `/mnt/sdb2/home/l4nd0/tenn`
- Final worktree status after closeout: clean.
- Unrelated preserve-worktree artifacts were isolated in named stashes:
  - `preserve unrelated dirty artifacts before cockpit home check-diff`
  - `preserve unrelated marketplace audit task card before cockpit home check-diff`
  - `preserve unrelated legacy chat envelope audit card before cockpit home closeout`
  - `preserve unrelated cockpit sidebar settings nav before cockpit home closeout`
  - `preserve generated next-env route type change before cockpit home closeout`
- Isolated paths included other task cards, `tenn_cockpit_home_design_export_20260506/`, and `tenn_prompt_contracts_response_guidelines.zip`.

## 2. Task Card and Registry Status

- Task card: `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- Metadata fix applied: `approval_required: true`
- Validation:
  - `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_contract_design_v1.md`
  - Result: passed, `ok: true`
- Registry active-job check:
  - `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
  - Initial implementation result: passed, `active_jobs: []`
  - Final commit-prep rerun: one active same-lane Reporting job appeared, `verification-source-page-viewer-default-integration-v1`, in `/tmp/tenn-source-page-viewer-default-integration-v1`.
  - File overlap with this task: none observed from registry `allowed_files`.
- Registry overlap check during implementation:
  - `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_contract_design_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`
  - Initial implementation result: failed only on unrelated dirty files outside this task card's `allowed_files`; no active registry overlap was reported.
  - Final commit-prep rerun: failed on the same unrelated dirty files plus same-lane overlap with the active verification source-page job. No allowed-file overlap was reported.
- Claim attempt:
  - `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_contract_design_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`
  - Result: failed for the same unrelated dirty-file guard. No registry claim was recorded.

## 3. Files Changed

- `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `reports/agent_jobs/cockpit_home_contract_design_v1/README.md`
- `reports/agent_jobs/cockpit_home_contract_design_v1/diff-check.json`

No backend runtime, legacy `/chat`, database, Qdrant, news store, memory store, ingestion, or live-data wiring files were changed.

Commit closeout:
- The scaffold is committed on the current branch.
- Commit message follows the Tenn milestone protocol.

## 4. Contract Fields Added/Designed

- `CockpitHomeBffResponse`: top-level narrow Home BFF response scaffold with `ok`, `generated_at`, taxonomy version, deterministic root state, market session, portfolio, movers, news, attention queue, data health, and narrative sections.
- `CockpitHomeDeterministicState`: shared deterministic state block with `data_state`, `degraded`, `data_missing`, and `as_of`.
- `CockpitHomeMarketSessionContract`: ASX session/calendar placeholder fields without implementing a backend endpoint.
- `CockpitHomePortfolioContract`: deterministic portfolio totals/coverage fields with nullable numeric values to avoid fabricated figures.
- `CockpitHomeSourceBearingItem` and `CockpitHomeEvidenceIdentity`: source/evidence identity fields for Home items, including `source_id`, `source_kind`, `source_label`, `evidence_labels`, `resolvable`, resolver type, document/chunk/evidence IDs, URL/title, and published timestamp.
- `CockpitHomeDataHealthContract` and `CockpitHomeNarrativeContract`: deterministic health state plus LLM-assisted narrative slots that remain downstream of deterministic evidence.

## 5. Source-Label Mapping Rules

`cockpit-ui/lib/cockpit-home-contract.ts` maps backend snake_case labels to Home display labels:

- `claim_verified` -> `CLAIM-VERIFIED`
- `context_only` -> `CONTEXT-ONLY`
- `no_hit` -> `NO-HIT`
- `operational_trace` -> `OPERATIONAL-TRACE`
- `local_personal_data` -> `LOCAL-PERSONAL-DATA`
- `memory_context` -> `MEMORY-CONTEXT`
- `external_web_context` -> `EXTERNAL-WEB-CONTEXT`
- `local_news_context` -> `LOCAL-NEWS-CONTEXT`
- `financial_truth` -> `FINANCIAL-TRUTH`
- `degraded_runtime` -> `DEGRADED-RUNTIME`
- `missing_required_evidence` -> `MISSING-EVIDENCE`
- `unknown_unclassified` and unknown labels -> `UNKNOWN-UNCLASSIFIED`

The mapping is typed with `satisfies Record<CockpitHomeBackendSourceLabel, TrustLevel>` so missing taxonomy entries fail TypeScript.

## 6. DATA_MISSING / Degraded Semantics

- `CockpitHomeDataState` is `READY | PARTIAL | DEGRADED | DATA_MISSING`.
- `cockpitHomeHasDataMissing()` treats explicit `DATA_MISSING`, non-empty deterministic `data_missing`, `missing_required_evidence`, and `no_hit` as missing-data conditions.
- `cockpitHomeIsDegraded()` treats explicit `degraded`, `DEGRADED`, and `degraded_runtime` as degraded conditions.
- `collectCockpitHomeStateIssues()` asserts that `DATA_MISSING` must include at least one deterministic missing-data reason.
- Nullable numeric/source fields are used where data can be absent so the frontend contract cannot invent canonical numbers or evidence IDs.

## 7. Attached-Source Handoff Shape

- `CockpitHomeAttachedSource` mirrors preserved `ChatScreen` serialization: `{ source_id, source_kind }`.
- `CockpitHomeChatHandoff` preserves `route: "/full-chat"` and `chat_screen: "ChatScreen"`.
- `buildCockpitHomeChatHandoff()` emits `attached_sources` only when the Home item has a non-empty backend-resolvable `source_id`, allowed `source_kind`, and non-missing/non-degraded evidence.
- Handoff is blocked with `blocked_reason: "DATA_MISSING" | "DEGRADED" | "UNRESOLVABLE_SOURCE"` when a Home item lacks a backend-resolvable source identity.
- No legacy `/chat` wiring was added.

## 8. Tests Run and Exact Results

Preflight:
- `git branch --show-current`: `preserve/dirty-work-20260430T065748Z`
- `git rev-parse --short=12 HEAD`: `b9f4d353a186`
- `git status --short`: succeeded; dirty files listed above.
- `git worktree list`: succeeded.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_contract_design_v1.md`: passed, `ok: true`.
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`: passed, `active_jobs: []`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_contract_design_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`: failed only on unrelated dirty files outside `allowed_files`.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_contract_design_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`: failed for the same unrelated dirty-file guard.
- Final `list-active` rerun before commit: one active same-lane Reporting job, `verification-source-page-viewer-default-integration-v1`, with disjoint files.
- Final `check-overlap` rerun before commit: failed on that same-lane job and unrelated dirty files; no file overlap with this task's allowed files was reported.
- After isolating unrelated artifacts into named stashes, `git status --short --untracked-files=all` returned clean except for the generated `diff-check.json` refresh, which was amended into the milestone commit.

Focused validation:
- `pnpm --dir cockpit-ui exec vitest run lib/cockpit-home-contract.test.ts`: passed, `1 passed`, `3 tests passed`.
- `pnpm --dir cockpit-ui exec tsc --noEmit`: passed with no output.
- `git diff --check`: passed with no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_contract_design_v1.md`: passed after unrelated preserve artifacts were isolated; wrote clean `reports/agent_jobs/cockpit_home_contract_design_v1/diff-check.json`.

Code review:
- `code-reviewer` workflow was applied to the allowed frontend contract diff.
- Result: no critical findings, warnings, or suggestions requiring code changes.

## 9. Collision Risk

MEDIUM:
- Active registry jobs were clear during implementation, then a separate same-lane Reporting job appeared before final commit preparation.
- No contested backend surfaces were touched.
- Implementation stayed inside the task's allowed files.
- A same-lane Reporting job appeared before final commit preparation, but its registry `allowed_files` are disjoint from this task's files.
- Risk remains MEDIUM, not LOW, because of that same-lane active Reporting job. The unrelated preserve-worktree artifacts are now isolated in a stash.

## 10. DATA_MISSING

- `reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md` is still missing from this preserve worktree.
- The required audit input was read from `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-audit-v1/reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md`.
- A registry claim record is DATA_MISSING because the claim command failed on unrelated dirty files before writing an active record.

## 11. Recommended Next Safe Implementation Step

Implement the real Home BFF endpoint or adapter only in a separate task. The next task should use a clean dedicated worktree or clear/allow the unrelated preserve-worktree artifacts first, then wire a backend-owned source resolver and same-origin BFF without changing legacy `/chat`.

## 12. Project Memory Save Recommendation

Save this project memory entry:

`Cockpit Home contract scaffold defines typed BFF response, deterministic state, source-label taxonomy mapping, DATA_MISSING/degraded invariants, and ChatScreen attached-source handoff; no live endpoint or backend wiring yet.`

## Final Report Template

Files changed:
- `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `reports/agent_jobs/cockpit_home_contract_design_v1/README.md`
- `reports/agent_jobs/cockpit_home_contract_design_v1/diff-check.json`

Files inspected:
- `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-audit-v1/reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `cockpit-ui/lib/hooks/use-attached-sources.ts`
- `cockpit-ui/components/cockpit/home/evidence-badge.tsx`
- `cockpit-ui/tsconfig.json`
- `cockpit-ui/vitest.config.ts`

Lane: Reporting
Execution mode: SAFE EXTENSION
Collision risk: MEDIUM
Validation run:
- focused Vitest
- TypeScript check
- `git diff --check`
- task-card validate/check-diff
Validation result:
- focused Vitest passed
- TypeScript passed
- `git diff --check` passed
- task-card validation passed
- task-card `check-diff` passed after unrelated artifacts were isolated in named stashes
Files intentionally not touched:
- backend runtime files
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/cockpit/core/chat.py`
- legacy `/chat`
- databases, Qdrant, news stores, memory stores
Remaining blockers:
- Same-lane registry checks should be rerun before any follow-up implementation because another Reporting job was active during final commit preparation.
Next safe step:
- Create a separate clean task for live Home BFF wiring.
