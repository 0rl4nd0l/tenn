# News Pipeline Dirty-File Classification v1

Lane: Provenance
Supporting lanes: Reporting, Query Orchestration
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: AUDIT ONLY
Intended files:
- `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`
- `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/**`
Contested surfaces touched: none
Collision risk: MEDIUM for preserve-worktree hygiene; LOW for this audit's allowed file writes
Decision: proceed with audit only

## Contract Scope

- Agent: Codex.
- Target system layer: agent/task-card reporting only. No ingestion, extraction, storage, retrieval, analysis, client runtime, Qdrant, memory, or financial-truth code was changed.
- Relevant contract rules: `SYSTEM_CONTRACT.md` sections 1.1, 1.2, 2, 3, and 4 require backend authority, no alternate retrieval/storage paths, no pipeline mutation, and no fabricated data lineage.
- What must not change: news ingestion files, news retrieval files, Qdrant projection, `news.sqlite`, embeddings, entity linking, query orchestration, Cockpit Home implementation, financial truth, company/market/thesis memory, parser logic, gold labels, staging, commits, cleanup, restores, deletes, or formatting.
- Why this audit is safe: only the approved task card and report directory were written; all news-related paths were inspected read-only through git metadata.
- GPU process check: not required. This audit did not spawn, restart, or depend on llama-server.

## Branch / HEAD

| Item | Evidence |
| --- | --- |
| Branch | `preserve/dirty-work-20260430T065748Z` |
| HEAD | `a62f743ff5e04883a5e2d1aa7c9e8ce7f08c456f` |
| HEAD subject | `milestone(agent-config): use stable Codex hooks flag` |
| Prompt baseline | `93c1191a8e479cb564f1cd8c8f8989776186a245` |
| Baseline ancestry | `git merge-base --is-ancestor 93c1191a8e479cb564f1cd8c8f8989776186a245 HEAD` exited `0` |
| Commits after baseline | `4ea8bfa milestone(news): constrain memo extraction output quality`; `a62f743 milestone(agent-config): use stable Codex hooks flag` |

## Task Card

- Task card path: `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`
- Validation command: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`
- Validation result: `ok: true`, no issues.

## Registry / Lock Status

| Step | Result |
| --- | --- |
| Initial `list-active` before task-card write | `active_jobs: []` |
| `check-overlap` after task-card validation | `ok: true`, no active jobs, no issues |
| Audit claim | created for `news_pipeline_dirty_file_classification_v1_20260507` |
| Claimed lane/mode | `Provenance`, `audit_only` |
| Claimed allowed files | this task card and `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/**` |
| Active jobs during audit | only this audit claim |
| Other owner of dirty news files | none found |
| Claim release | `ok: true`; active record removed |
| Final `list-active` | one unrelated active Evaluation job: `tenn_agent_mcp_connector_dry_run_plan_20260507` in `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-connector-dry-run-plan-20260507` |
| Final `check-overlap` | `ok: true`; no issues against this audit card |

## Preflight Summary

Required commands were run read-only before classification:

- `git branch --show-current`: `preserve/dirty-work-20260430T065748Z`
- `git rev-parse HEAD`: `a62f743ff5e04883a5e2d1aa7c9e8ce7f08c456f`
- `git status --short --untracked-files=all` before creating this task card: no output.
- `git worktree list`: current preserve worktree plus many sibling audit/safe/integration worktrees; no active registry job owned this audit's file set.
- Recent Cockpit Home log: `93c1191`, `61509ac`, `8925498`, `3d49c9d`, `6781f89`, `53b60a7`, `f7a7454`.
- Recent news log: `4ea8bfa`, `9aae854`, `c3609b5`, `c22a6c0`, `3e7187e`, `165be97`, `fb880c6`, `22356f2`, `0a2d497`, and older news/cockpit news commits.
- `python3 scripts/agent_job_registry.py list-active`: initially empty.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`: `ok: true`.

## Dirty File Table

### Initial Dirty Inventory Before This Audit Wrote Files

`git status --short --untracked-files=all` returned no rows before the task card was created.

| Path | Git status code | Likely lane | Likely owner/workstream | Staged/unstaged/untracked | Intentional/generated/stale/accidental/DATA_MISSING | Subsystem | Cockpit Home overlap | Blocks Home market movers/news endpoint work | Recommended treatment | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| No dirty or untracked file present | none | DATA_MISSING | DATA_MISSING | none | DATA_MISSING for prior reported dirty state | DATA_MISSING | No current file overlap | No current blocker visible in git status | Leave untouched; do not invent a cleanup action | High for current absence; low for prior state |

### Current Dirty Inventory Created By This Audit

At report-writing time, visible `git status --short --untracked-files=all` showed only:

| Path | Git status code | Likely lane | Likely owner/workstream | Staged/unstaged/untracked | Intentional/generated/stale/accidental/DATA_MISSING | Subsystem | Cockpit Home overlap | Blocks Home market movers/news endpoint work | Recommended treatment | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md` | `??` | Provenance | Codex audit | untracked | intentional | reports/task-card | No | No | preserve with this report, or commit separately if the user wants audit artifacts kept | High |
| `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/status.json` | ignored (`!!` in scoped ignored status) | Provenance | registry claim | ignored/untracked | generated | reports/registry artifact | No | No | preserve as audit evidence if committing reports; leave untouched otherwise | High |
| `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/README.md` | ignored by reports rules | Provenance | Codex audit | ignored/untracked | intentional | reports/audit artifact | No | No | preserve as audit evidence | High |
| `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/diff-check.json` | ignored by reports rules | Provenance | task-card validation | ignored/untracked | generated | reports/diff-check artifact | No | No | preserve as validation evidence | High |

## Per-File Classification

No dirty or untracked news-pipeline file is currently present in this preserve worktree.

Read-only targeted checks returned no rows for news/Qdrant/memo/entity/commentary paths under `financial-engine_v2`, `scripts`, or `integrations`:

- `git status --short --untracked-files=all -- financial-engine_v2 scripts integrations | rg -i 'news|qdrant|newspaper|memo|entity|commentary'`
- `git ls-files --others --exclude-standard -- financial-engine_v2 scripts integrations | rg -i 'news|qdrant|newspaper|memo|entity|commentary'`
- `git diff --name-only -- financial-engine_v2 scripts integrations | rg -i 'news|qdrant|newspaper|memo|entity|commentary'`
- A direct status check of the likely post-Home news files also returned no rows:
  - `financial-engine_v2/backend/app/services/news_memo_extractor.py`
  - `financial-engine_v2/backend/app/tasks/news_tasks.py`
  - `financial-engine_v2/backend/tests/test_news_memo_extractor.py`
  - `financial-engine_v2/backend/tests/test_news_tasks.py`
  - `scripts/load_news_to_qdrant.py`
  - `scripts/test_load_news_qdrant_preflight.py`

## Post-Baseline News Commit Evidence

The prompt says the prior Home Portfolio task landed at `93c1191`. Current HEAD is two commits past that baseline:

```text
a62f743 milestone(agent-config): use stable Codex hooks flag
4ea8bfa milestone(news): constrain memo extraction output quality
```

`git diff --name-status 93c1191a8e479cb564f1cd8c8f8989776186a245..HEAD` shows the only post-baseline news-related tracked changes are now committed:

```text
M	.codex/config.toml
M	docs/claude/STATE.md
M	financial-engine_v2/backend/app/services/news_memo_extractor.py
M	financial-engine_v2/backend/app/tasks/news_tasks.py
M	financial-engine_v2/backend/tests/test_news_memo_extractor.py
M	financial-engine_v2/backend/tests/test_news_tasks.py
M	scripts/load_news_to_qdrant.py
M	scripts/test_load_news_qdrant_preflight.py
```

`git show --name-status 4ea8bfa` attributes the news-related files to `milestone(news): constrain memo extraction output quality`. That commit reports focused memo/task/loader/backfill/Celery smoke validation plus `git diff --check`. This audit did not re-run those tests because the task explicitly forbids pipeline jobs and asks for repo hygiene classification only.

## Files Unrelated To Cockpit Home

Confirmed current dirty/untracked files unrelated to Cockpit Home:

- `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`
- `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/README.md`
- `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/diff-check.json`
- `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/status.json`

Confirmed current news-pipeline dirty/untracked files unrelated to Cockpit Home:

- none present.

Tracked post-baseline news commit files are unrelated to Cockpit Home implementation files and do not overlap current Cockpit Home paths:

- `financial-engine_v2/backend/app/services/news_memo_extractor.py`
- `financial-engine_v2/backend/app/tasks/news_tasks.py`
- `financial-engine_v2/backend/tests/test_news_memo_extractor.py`
- `financial-engine_v2/backend/tests/test_news_tasks.py`
- `scripts/load_news_to_qdrant.py`
- `scripts/test_load_news_qdrant_preflight.py`

## Files Blocking Future Home Market Movers / News Work

No current dirty or untracked news-pipeline file blocks future Home market movers/news endpoint work in this worktree.

Residual risk:

- The exact dirty-file list observed by the previous Home task is not available in this turn, so the historical blocker cannot be reconstructed with full status codes.
- `4ea8bfa` appears to have committed the likely news memo/loader/test work after `93c1191`, but that is an inference from current git history, not proof of the prior dirty status.
- Future Home market movers/news endpoint work should still start with a fresh `git status`, `list-active`, and task-card `check-overlap` because this branch is live.

## Recommended Treatment

| Item | Treatment | Action taken |
| --- | --- | --- |
| Current news-pipeline dirty files | none to preserve/review/revert/archive/isolate | none |
| Current audit task card/report artifacts | preserve or commit separately if user wants this audit recorded | task card/report written only |
| Historical dirty news files from prior Home task | DATA_MISSING; do not revert or archive based on absent evidence | none |
| Post-`93c1191` committed news changes in `4ea8bfa` | leave untouched; they are tracked commits, not dirty files | none |

No dirty news-pipeline file was edited, formatted, staged, committed, reverted, deleted, moved, archived, or otherwise touched.

## DATA_MISSING

- The exact prior `git status --short --untracked-files=all` output from the Home Portfolio task is not present in this turn.
- The exact prior status codes for the reported unrelated news-pipeline files cannot be verified.
- The exact owner/session that originally produced the prior dirty news files cannot be verified from current dirty state because there is no current dirty news file to inspect.
- The current worktree is at `a62f743`, not the task-context landing commit `93c1191`; the branch moved after that task.

## Recommended Next Safe Step

Before any Home market movers/news endpoint work:

1. Start from a clean or isolated worktree.
2. Run `git status --short --untracked-files=all`.
3. Validate and claim the new task card.
4. Run registry `list-active` and `check-overlap`.
5. Proceed only if no active job owns the same lane/files and no HIGH collision remains.

No cleanup command is recommended for news-pipeline files because none are dirty now.

## Project Memory Save Recommendation

Save a short project memory note:

```text
2026-05-08 Codex audit news_pipeline_dirty_file_classification_v1_20260507: preserve worktree HEAD a62f743 had no dirty/untracked news-pipeline files; prior post-Home blocker appears no longer present. 93c1191 is an ancestor of HEAD; likely news files are tracked in 4ea8bfa, but the exact prior dirty status snapshot is DATA_MISSING. Future Home market movers/news work should still start with fresh status, registry list-active, and check-overlap.
```

## Validation

| Command | Result |
| --- | --- |
| `git diff --check` | passed, no output |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md` | `ok: false` |
| check-diff changed files | `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md` only |
| check-diff disallowed files | none |
| check-diff issue | `audit_only jobs may not include code changes unless allow_audit_code_changes=true` |
| check-diff report | `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/diff-check.json` |
| registry release | passed; status artifact now says `status: released` |
| final registry overlap | passed; unrelated active MCP dry-run audit job does not overlap |

The `check-diff` failure is expected for this repo's current audit-only contract behavior: even an allowed untracked audit task card is reported as a changed file unless `allow_audit_code_changes=true` is present. It did not identify dirty files outside this audit card.

## Final Git Status

Final `git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md
```

Final scoped ignored status for this report directory:

```text
!! reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/README.md
!! reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/diff-check.json
!! reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/status.json
```

No code files are dirty from this audit, and no news-pipeline files are dirty or untracked in the final status.
