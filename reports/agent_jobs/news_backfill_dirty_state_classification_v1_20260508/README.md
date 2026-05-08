# News Backfill Dirty-State Classification v1

Lane: Provenance
Supporting lane: Reporting
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: AUDIT ONLY
Intended files:
- `docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md`
- `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md`
- `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json`
- `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/status.json` if a registry claim is created
Contested surfaces touched: none
Collision risk: LOW for read-only reporting and this audit's allowed artifacts; HIGH for any mutation to news/runtime/product files
Decision: audit only; do not claim because registry overlap preflight failed on an existing dirty task card outside this audit's `allowed_files`

## Contract Scope

- Agent: Codex.
- Target system layer: provenance/reporting artifacts only. This audit did not change ingestion, extraction, storage, retrieval, analysis, client runtime, Qdrant, memory, or financial truth.
- Relevant contract rules: `docs/architecture/SYSTEM_CONTRACT.md` sections 1.1, 1.2, 2, 3, 4, 5, 7, 8, and 10.3 require backend authority, pipeline ordering, no alternate truth stores, no fabricated data lineage, and no fallbacks that hide missing data.
- What must not change: `scripts/backfill_missing_news_memos.py`, news stores, Qdrant, embeddings, ingestion scripts, memo extraction runtime, query orchestrator, Cockpit Home implementation, financial truth, company/market/thesis memory, parser logic, and gold labels.
- Why this audit is safe: only the approved task card and report directory were written; all code/product/news paths were inspected read-only through git metadata.
- GPU process check: not required. This audit did not spawn, restart, or depend on llama-server.

## 1. Branch / HEAD

| Item | Evidence |
| --- | --- |
| Branch | `preserve/dirty-work-20260430T065748Z` from `git branch --show-current` |
| HEAD | `c4ab78d05533bee681138ec337c0134fed7c7960` from `git rev-parse HEAD` |
| HEAD subject | `milestone(news): bound memo backfill dispatch` from `git show --name-status --oneline HEAD` |
| Current worktree | `/mnt/sdb2/home/l4nd0/tenn`, current branch shown by `git worktree list` |

## 2. Registry / Lock Status

| Step | Result |
| --- | --- |
| Task card creation | `docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` was absent, then created with the provided content |
| Task card validation | `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` returned `ok: true`, `issues: []` |
| Registry root | `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`, scope `shared` |
| Active jobs | `python3 scripts/agent_job_registry.py list-active` returned `active_jobs: []` |
| Overlap check | `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` returned `ok: false` |
| Overlap issue | `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md is dirty outside current task card allowed_files` |
| Claim | Not created. The task explicitly says to claim only if safe; overlap preflight was not safe. |
| Release | Not applicable; no claim was created. |

## 3. Preflight Summary

Required read-only preflight commands were run.

| Command | Result |
| --- | --- |
| `git branch --show-current` | `preserve/dirty-work-20260430T065748Z` |
| `git rev-parse HEAD` | `c4ab78d05533bee681138ec337c0134fed7c7960` |
| `git status --short --untracked-files=all` | `?? docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md`; `?? docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` |
| Scoped ignored status for prior report dirs | Only `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/{INVESTIGATION.md,README.md,diff-check.json,status.json}` appeared as `!!`; the news-pipeline report dir did not appear dirty/ignored because it is tracked clean |
| `git worktree list` | Current preserve worktree plus many sibling audit/safe/integration worktrees; no active registry ownership was reported for this audit's files |
| `python3 scripts/agent_job_registry.py list-active` | `active_jobs: []` |
| `python3 scripts/agent_job_registry.py check-overlap ...` | Failed on the untracked Cockpit Home task card outside this audit card |

No prohibited command was run. The backfill script was not executed.

## 4. Dirty File Table

| Path | Git status | Likely lane | Likely owner/workstream | Stage class | Classification | Subsystem | Blocks Cockpit Home Market Movers / News Snapshot v1? | Safe to preserve? | Needs user approval before commit/revert/delete? | Recommended next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/backfill_missing_news_memos.py` | tracked clean; absent from `git status`; empty `git diff` and `git diff --stat` | Provenance / news pipeline | News memo/backfill workstream | none | intentional tracked code, not current dirty state | news memo backfill dispatch | No current dirty blocker | Yes, preserve current HEAD version | Yes for any edit or revert | Leave untouched |
| `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` | `??` | Reporting | Codex Cockpit Home job | untracked | intentional task card, currently uncommitted | agent task card | Yes, it blocks task-card overlap checks for other jobs and records the blocked v1 attempt | Yes | Yes | Preserve or commit in a dedicated cleanup/preservation step; delete only with user approval |
| `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/README.md` | `!!` ignored/untracked | Reporting | Codex Cockpit Home job | ignored | intentional report artifact | agent job report | Indirectly; evidence for the blocked v1 attempt, but ignored reports did not trigger the current overlap issue | Yes | Yes | Preserve with the task card if keeping the blocked attempt record |
| `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/INVESTIGATION.md` | `!!` ignored/untracked | Reporting | Codex Cockpit Home job | ignored | intentional investigation artifact | agent job report | Indirectly; contains v1 source investigation and blocked-state evidence | Yes | Yes | Preserve with the task card if keeping the blocked attempt record |
| `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/status.json` | `!!` ignored/untracked | Reporting | registry / Codex Cockpit Home job | ignored | generated status artifact | agent registry/report | No direct product blocker | Yes | Yes | Preserve as evidence or remove only with approval |
| `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/diff-check.json` | `!!` ignored/untracked | Reporting | task-card check-diff / Codex Cockpit Home job | ignored | generated validation artifact | agent report | No direct product blocker | Yes | Yes | Preserve as evidence or remove only with approval |
| `docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` | `??` | Provenance | Codex current audit | untracked | intentional task card | agent task card | No product blocker; can block later task-card claims until preserved or removed | Yes | Yes | Preserve with this report or remove only with approval |
| `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md` | ignored/untracked after write | Provenance | Codex current audit | ignored | intentional report artifact | agent job report | No product blocker | Yes | Yes | Preserve as this audit's definition-of-done artifact |
| `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json` | ignored/untracked after validation | Provenance | task-card check-diff / Codex current audit | ignored | generated validation artifact | agent job report | No product blocker | Yes | Yes | Preserve as validation evidence or remove only with approval |

Tracked clean artifacts from the prior dirty-file audit:

| Path group | Git status | Evidence | Classification | Recommended next action |
| --- | --- | --- | --- | --- |
| `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md` and `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/*` | tracked clean | `git ls-files --stage` returned entries; `git log -- ...` shows `feeade4 milestone(provenance): record news dirty-file classification audit`; scoped status returned no rows | intentional preserved audit artifacts, not current dirty state | Leave untouched |

## 5. Detailed Classification of `scripts/backfill_missing_news_memos.py`

Current state is CONFIRMED clean:

- `git diff -- scripts/backfill_missing_news_memos.py` returned no output.
- `git diff --stat -- scripts/backfill_missing_news_memos.py` returned no output.
- `git status --short --untracked-files=all` did not list the script.
- `git diff --name-status HEAD` returned no output.

Commit attribution is CONFIRMED:

- `git log --oneline --decorate -- scripts/backfill_missing_news_memos.py` shows only:
  - `c4ab78d milestone(news): bound memo backfill dispatch`
  - `9aae854 milestone(news): decouple memo enrichment from nightly ingest`
- `git show --name-status --oneline 9aae854` shows `A scripts/backfill_missing_news_memos.py`.
- `git show --name-status --oneline HEAD` shows `M scripts/backfill_missing_news_memos.py`.
- `git show --name-status --oneline 4ea8bfa` does not list `scripts/backfill_missing_news_memos.py`.
- `git diff --name-status 9aae854..HEAD -- scripts/backfill_missing_news_memos.py` shows `M scripts/backfill_missing_news_memos.py`.
- `git diff --stat 9aae854..HEAD -- scripts/backfill_missing_news_memos.py` shows `130 insertions(+), 1 deletion(-)`.
- `git blame -- scripts/backfill_missing_news_memos.py` attributes the base script to `9aae854` and the batch-dispatch additions to `c4ab78d`.

Classification against the requested candidates:

| Candidate | Classification | Evidence |
| --- | --- | --- |
| `4ea8bfa milestone(news): constrain memo extraction output quality` | No current script diff belongs to this commit | `git show --name-status --oneline 4ea8bfa` does not include the script; script log omits `4ea8bfa` |
| `9aae854 milestone(news): decouple memo enrichment from nightly ingest` | Yes for initial creation/base script | `git show --name-status --oneline 9aae854` adds the script; blame attributes most base lines to `9aae854` |
| `c4ab78d milestone(news): bound memo backfill dispatch` | Yes for the current HEAD modification | `HEAD` modifies the script; diff from `9aae854..HEAD` is the bounded-dispatch change; blame attributes batch-dispatch lines to `c4ab78d` |
| Another active/unknown job | Not supported by current evidence | Registry `list-active` returned empty; there is no uncommitted script diff |
| Local uncommitted operator work | No current evidence | Script is tracked clean at HEAD; exact historical uncommitted state before `c4ab78d` is DATA_MISSING |
| Generated/accidental edit | Not supported | The script and test changes are in milestone commits with matching names and tests; no generated markers were observed |
| DATA_MISSING | Only for historical dirty-state reconstruction | The exact prior uncommitted diff that blocked the Home task is not available now because it is no longer dirty |

Conclusion: `scripts/backfill_missing_news_memos.py` is intentional tracked news-backfill code at the current HEAD. It is not a current dirty blocker. The likely previously blocking script diff has been preserved in `c4ab78d`, but the exact prior uncommitted snapshot is DATA_MISSING.

## 6. Classification of Uncommitted Task Cards and Ignored Reports

| Artifact | Current classification |
| --- | --- |
| `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` | Untracked, intentional, Reporting lane, owner/workstream Codex Cockpit Home v1. It is the active dirty artifact that caused this audit's overlap check to fail. |
| `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/*` | Ignored/untracked, intentional/generated report evidence for the blocked Cockpit Home v1 attempt. Safe to preserve; commit/delete needs approval. |
| `docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` | Untracked, intentional, current Provenance audit task card. Safe to preserve; commit/delete needs approval. |
| `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md` | Ignored/untracked, intentional current audit report. Safe to preserve; commit/delete needs approval. |
| `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json` | Ignored/untracked, generated by required check-diff validation. Safe to preserve; commit/delete needs approval. |
| `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md` | Tracked clean in `feeade4`, no longer uncommitted. |
| `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/*` | Tracked clean in `feeade4`, no longer ignored dirty state. |

## 7. What Blocks Market Movers / News Snapshot v1

CONFIRMED current blocker:

- The untracked `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` file blocks new task-card overlap checks when it is outside another job's `allowed_files`.

CONFIRMED non-blocker:

- `scripts/backfill_missing_news_memos.py` does not currently block v1 because it is clean at HEAD.

INFERRED from existing Cockpit Home report:

- The Cockpit Home v1 implementation was blocked earlier by inability to claim safely while unrelated dirty artifacts existed. Its ignored report says Market Movers remained `NO_MARKET_MOVERS_ENDPOINT` / `DATA_MISSING`, and News Snapshot wiring was deferred until the job can be claimed safely.

## 8. Safe Cleanup / Preservation Options

| Option | What it preserves | Safety notes |
| --- | --- | --- |
| Preserve task/report artifacts in a dedicated provenance commit | Cockpit Home v1 blocked attempt plus this audit's evidence | Safest if the team wants durable history. Requires user approval and likely `git add -f` for ignored report files. |
| Commit only task cards, leave ignored reports local | Reduces visible dirty status from `docs/agent_tasks/*` | Weaker provenance because the evidence reports remain local/ignored. Requires user approval. |
| Leave artifacts as-is until the next Cockpit Home task explicitly owns them | No immediate cleanup mutation | Current untracked task cards can keep blocking other task-card jobs. |
| Delete/archive stale Cockpit Home report artifacts | Cleans the worktree | Requires explicit user approval; do not do this automatically because the report is evidence for the blocked v1 attempt. |
| Revert or edit `scripts/backfill_missing_news_memos.py` | Not recommended | No current dirty script exists. Reverting a tracked milestone would be product mutation and needs a separate task plus approval. |

## 9. What Requires User Approval

- Committing any currently untracked or ignored task/report artifact.
- Force-adding ignored reports under `reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/` or this audit's report directory.
- Deleting, moving, archiving, or reverting any Cockpit Home task/report artifact.
- Any edit/revert to `scripts/backfill_missing_news_memos.py`.
- Any operation touching news stores, Qdrant, embeddings, ingestion, memo extraction runtime, query orchestrator, Cockpit Home implementation, financial truth, or memory.

## 10. DATA_MISSING

- The exact prior uncommitted diff of `scripts/backfill_missing_news_memos.py` before `c4ab78d` cannot be reconstructed from current dirty state because the script is now clean and tracked.
- The exact active session or operator that produced the historical dirty script state is not verifiable from current registry state; `list-active` is empty now.
- Whether queued `llm_gpu` memo tasks from the `docs/claude/STATE.md` operational note remain pending was not checked, because the task forbids touching/running memo extraction/runtime state.
- No production or local news store content was inspected in this audit.

## 11. Recommended Next Safe Step

Preserve the remaining task/report provenance first, then retry the Cockpit Home v1 job from a task card that owns its artifacts.

Minimum safe sequence for a future approved cleanup/preservation step:

1. Commit or otherwise user-approved preserve `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` and its report artifacts.
2. Commit or user-approved preserve this audit's task card/report artifacts.
3. Re-run `git status --short --untracked-files=all`.
4. Re-run registry `list-active` and task-card `check-overlap`.
5. Only then retry Cockpit Home Market Movers / News Snapshot v1 implementation.

Do not clean up or modify `scripts/backfill_missing_news_memos.py`; it is already tracked clean.

## 12. Final Git Status

Validation:

| Command | Result |
| --- | --- |
| `git diff --check` | Passed; no output |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` | Failed as expected for existing dirty/task-card state; `ok: false`, exit code `1` |
| check-diff changed files | `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` (`??`) and `docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md` (`??`) |
| check-diff disallowed files | `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md` |
| check-diff issues | `docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md is outside allowed_files`; `audit_only jobs may not include code changes unless allow_audit_code_changes=true` |
| check-diff report | `reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json` |
| final registry `list-active` | `active_jobs: []` |
| final `git diff --name-status HEAD` | Passed; no output |

Final `git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md
?? docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md
```

Final scoped ignored status:

```text
!! reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/INVESTIGATION.md
!! reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/README.md
!! reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/diff-check.json
!! reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/status.json
!! reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md
!! reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json
```

No product/code file is dirty from this audit. `scripts/backfill_missing_news_memos.py` remained untouched and clean. No registry claim was created, so no release was required.
