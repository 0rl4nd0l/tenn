# Task Card Dirt Hygiene

## Confirmed facts

- `/home/l4nd0/tenn` resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- The isolated closeout worktree is `/home/l4nd0/tenn-task-card-dirt-hygiene-v1-20260524`.
- Isolated branch: `safe/task-card-dirt-hygiene-v1-20260524`.
- Isolated base HEAD: `0141021b4622b999e3c5ca82f3dd6f559186cda9`.
- Current shared-registry `list-active` returned `active_jobs=[]` before the isolated claim.
- Initial shared-checkout preflight saw transient untracked cards for Strategy Lab and backend evidence guard jobs.
- The Strategy Lab readiness card is now tracked in ancestor commit `0211a5b4`.
- The backend evidence guard card and README are now tracked in HEAD `0141021b`.
- Current untracked task-card artifacts copied into this isolated branch are the hygiene card, `backend_chat_evidence_guard_canonical_integrate_v1_20260524.md`, and `strategy_lab_status_card_browser_smoke_v1_20260524.md`.
- No backend, Cockpit chat, evidence/source helper, runtime topology, Docker, cron, parser/extraction, memory, Qdrant/news, dependency, lockfile, or UI source file was edited by this hygiene job.

## Inferred facts

- The Strategy Lab readiness and backend evidence guard cards are recent completed job-control evidence because their owning commits include the task cards and report files.
- `strategy_lab_status_card_browser_smoke_v1_20260524.md` is a report-only follow-up audit card, not an active implementation, because it has no active registry lock and no report output yet.
- The safest closeout is an isolated branch checkpoint of the unowned docs/report artifacts, because the shared checkout was live while unrelated task cards appeared.

## DATA_MISSING

- No report directory exists yet for `strategy_lab_status_card_browser_smoke_v1_20260524`.
- This audit did not run the browser-smoke task; it only classified and checkpointed the card.
- This audit did not inspect runtime state, production databases, Qdrant, news stores, memory stores, Docker, cron, parser/extraction, or financial truth data.

## Branch and HEAD

- Canonical requested path: `/home/l4nd0/tenn`
- Canonical realpath: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Isolated worktree: `/home/l4nd0/tenn-task-card-dirt-hygiene-v1-20260524`
- Isolated branch: `safe/task-card-dirt-hygiene-v1-20260524`
- Base HEAD: `0141021b4622b999e3c5ca82f3dd6f559186cda9`
- Latest commits at isolated closeout:
  - `0141021b fix(query): guard chat claims by evidence type`
  - `0211a5b4 chore(reporting): surface strategy lab status in cockpit`
  - `0552a9eb fix(query): keep no-hit market tools unverified`
  - `370c7c99 feat(reporting): add chat evidence actionability states`
  - `016f613f feat(reporting): extend cockpit actionability states`

## Active registry jobs and wait behavior

- First shared preflight saw the Strategy Lab frontend readiness job active.
- Later shared preflight saw the backend evidence guard job active in sibling worktree `/home/l4nd0/tenn-backend-chat-evidence-guard-v1-20260524`.
- This job waited twice for 300 seconds while broad task-card overlap and Strategy Lab dirty files were present.
- After the waits, both owning jobs had committed their task-card/report evidence into the baseline.
- The interrupted shared closeout was moved to the isolated branch/worktree at the user's direction.
- Isolated `list-active` before claim returned `active_jobs=[]`.
- Isolated `check-overlap` passed before claim.
- Isolated claim for `task_card_dirt_hygiene_v1_20260524` succeeded.

## Untracked task-card table

| path | job_id | lane | status | report dir exists | commit evidence | classification | recommended action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/backend_chat_evidence_guard_canonical_integrate_v1_20260524.md` | `backend_chat_evidence_guard_canonical_integrate_v1_20260524` | Query Orchestration | Current untracked integration follow-up card | no | none before this hygiene checkpoint | REPORT_ONLY_AUDIT_CARD | Checkpoint this docs-only integration follow-up card with the hygiene report so it does not remain unrelated task-card dirt. |
| `docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md` | `backend_chat_evidence_guard_v1_20260524` | Query Orchestration | Transient preflight-seen, now tracked | yes | HEAD `0141021b fix(query): guard chat claims by evidence type` | RECENT_COMPLETED_JOB_CARD | No hygiene action needed. Already committed by owning job. |
| `docs/agent_tasks/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524.md` | `strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524` | Reporting | Transient preflight-seen, now tracked | yes | ancestor `0211a5b4 chore(reporting): surface strategy lab status in cockpit` | RECENT_COMPLETED_JOB_CARD | No hygiene action needed. Already committed with report artifacts. |
| `docs/agent_tasks/strategy_lab_status_card_browser_smoke_v1_20260524.md` | `strategy_lab_status_card_browser_smoke_v1_20260524` | Reporting | Current untracked follow-up card | no | none before this hygiene checkpoint | REPORT_ONLY_AUDIT_CARD | Checkpoint this docs-only follow-up card with the hygiene report so it does not remain unrelated task-card dirt. |
| `docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md` | `task_card_dirt_hygiene_v1_20260524` | Evaluation | Current untracked current-job card | yes | none before this hygiene checkpoint | ACTIVE_CURRENT_TASK_CARD | Commit this card and its report inventory, then release the registry claim. |

## Files left untouched and why

- `cockpit-ui/**`: forbidden for this repo-hygiene task.
- `financial-engine_v2/**`: forbidden backend/chat/evidence/runtime scope for this repo-hygiene task.
- Runtime, DB, Qdrant, news, memory, Docker, cron, parser/extraction, and dependency surfaces: outside task scope.

## Files committed

Canonical checkpoint subject: `chore(repo): classify task-card artifacts`.

Committed scope:

- `docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`
- `docs/agent_tasks/backend_chat_evidence_guard_canonical_integrate_v1_20260524.md`
- `docs/agent_tasks/strategy_lab_status_card_browser_smoke_v1_20260524.md`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/README.md`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.json`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.csv`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/status.json`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/diff-check.json`

## Validation commands and results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`: passed before isolated claim.
- `python3 scripts/agent_job_registry.py list-active`: passed with `active_jobs=[]` before isolated claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`: passed before isolated claim.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`: passed.
- `python3 -m json.tool reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.json`: passed.
- `python3 -m json.tool reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/status.json`: passed.
- `python3 -m json.tool reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/diff-check.json`: passed.
- `git diff --check`: passed with no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`: passed with `disallowed_files=[]`.
- `python3 scripts/agent_job_registry.py release task_card_dirt_hygiene_v1_20260524`: passed.
- Final `python3 scripts/agent_job_registry.py list-active`: passed; one disjoint active Strategy Lab job remained.

## Final git status

Final canonical `git status --short --untracked-files=all` after checkpoint was clean.

## Future check-diff cleanliness

Future unrelated `check-diff` runs should be cleaner because the remaining untracked docs task-card artifacts were captured as tracked docs/report evidence in the canonical branch.

## Remaining blockers

- The browser-smoke card has no report output yet; it is only a prepared follow-up task card.

## Recommended next task

Run `strategy_lab_status_card_browser_smoke_v1_20260524` separately if a browser/dev-server smoke is still desired. Keep it Reporting lane and frontend-only.

## Project Memory save recommendation

Save the lesson that broad task-card hygiene allowlists can collide with active sibling jobs; when the shared checkout is live, move the checkpoint to an isolated branch/worktree and copy only unowned docs/report artifacts.
