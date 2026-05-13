# Cockpit Upgrade Integration Readiness Audit

## Executive Summary

CONFIRMED: current preserve HEAD is `dabbc456e42f737d12e6a1d979e6189e0936e865` on `preserve/dirty-work-20260430T065748Z`, and `:8081` is serving this same worktree and HEAD from `cockpit-ui`. The shared registry reports no active jobs.

CONFIRMED: the main preserve worktree is not fully clean. Final status contains this audit task card plus out-of-scope dirty files:

- `scripts/run_llama_server.sh`
- `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`
- `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md`

INFERRED: the safest next Cockpit upgrade integration target is `c0549d754cb501254873b34c66d9aec7d12b95d8` from `codex/cockpit-home-news-snapshot-v1-20260508` / `integrate/cockpit-home-news-snapshot-v1-20260508`, but only as a source-only/manual application task after out-of-scope dirty state is handled. Do not merge the whole branch.

## Confirmed Facts

- Task card validation passed for `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md`.
- `python3 scripts/agent_job_registry.py list-active` returned an empty `active_jobs` array.
- `python3 scripts/agent_job_registry.py check-overlap ...` returned `ok: false` because unrelated dirty task cards were outside this audit card’s allowed files.
- Final `python3 scripts/agent_job_contract.py check-diff ...` returned `ok: false` because `scripts/run_llama_server.sh`, `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`, and `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md` are outside allowed files.
- `git worktree list --porcelain` confirms all named candidate branches exist and have worktrees.
- `git merge-base --is-ancestor` confirms these named candidates are ancestors of current preserve HEAD:
  - `integrate/cockpit-home-live-wiring-and-sidebar-fix`
  - `codex/source-label-998d68e-clean-integration-20260506`
- The live runtime `:8081` runs from `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui` at HEAD `dabbc456e42f737d12e6a1d979e6189e0936e865`.
- `:3000` is not listening.
- `graphify-out/GRAPH_REPORT.md` exists and was inspected before broad searches.

## Inferred Facts

- Current runtime is not exposing a stale `/mnt/sdb2/...` Cockpit worktree; it is serving current preserve.
- The old P1 shell/live-wiring branches should not be merged because a later integrated branch and later preserve commits already carry the useful behavior while the old branch tips compare as broad stale reverse drift.
- The marketplace recency UI/contract work appears already represented in current preserve by later commits, even though the original safe branches are not ancestors.
- Source-label/provenance behavior appears already represented in current preserve and should not be the first Reporting integration because remaining source-label branches touch backend/query/provenance contested surfaces.

## DATA_MISSING

- `lsof` did not identify the `:8081` listener; runtime identity is based on `ss`, `ps`, `/proc`, and curl.
- No browser screenshot or rebuilt Next artifact validation was performed; audit boundaries prohibited restart/rebuild.
- The shared worktree has out-of-scope dirty files, so this audit cannot prove the full worktree is clean.
- The exact runtime UI effect of `c0549d7` cannot be confirmed without a follow-up implementation and rebuild/restart.

## Runtime Status

- `:8081`: live, `HTTP/1.1 200 OK`, Next.js, cwd `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui`, branch `preserve/dirty-work-20260430T065748Z`, HEAD `dabbc456e42f737d12e6a1d979e6189e0936e865`.
- `:3000`: not live.
- `:8000`: live, not mutated.
- `:8001`: live llama-server, not mutated.

## Main Worktree Cleanliness

Not clean. Final `git status --short --untracked-files=all` reported:

```text
 M scripts/run_llama_server.sh
?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
?? docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md
```

Only `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` belongs to this audit. The other paths were left untouched.

## Active Registry Status

No active jobs were reported by the shared registry.

## Candidate Branch Matrix Summary

See `candidate_branch_matrix.md` for the full table.

- Already integrated: `integrate/cockpit-home-live-wiring-and-sidebar-fix`, `codex/source-label-998d68e-clean-integration-20260506`.
- Functionally/staleness integrated by later preserve commits: old sidebar/live-wiring branches, marketplace recency UI/contract branches.
- Pending but not first: `safe/marketplace-scanner-instrumentation-v1`, source-label retry, preserve chat-envelope/source-label integration.
- Recommended first: `c0549d754cb501254873b34c66d9aec7d12b95d8` from the home-news snapshot branch pair.

## Recommended First Integration Target

Target `c0549d754cb501254873b34c66d9aec7d12b95d8` because its actual commit is narrowly scoped to:

- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`

It adds Cockpit Home market-update/news snapshot behavior and avoids backend/query/provenance surfaces if applied source-only.

## Why Not The Other Candidates Yet

- P1 shell/live-wiring: already integrated or stale relative to current preserve.
- Sidebar nested button fix: current preserve has later `5e7f762 fix(reporting): remove nested sidebar chat button`.
- Marketplace recency UI/contract: current preserve already has `match-recency.ts`, `last_seen_at`, sort support, and tests.
- Marketplace scanner instrumentation: backend scanner/test scope; not the safest Reporting UI integration.
- Source-label/provenance retry and chat-envelope/source-label: touch backend/query contested surfaces and need a separate Query Orchestration/Provenance audit.

## Exact Next Safe Action

Use the handoff in `recommended_integration_handoff.md` after resolving or isolating out-of-scope dirty state. Create the follow-up task card there, claim it, then manually apply only the relevant source/test hunks from `c0549d7`. Do not merge the whole branch.

## Project Memory Save Recommendation

SAVE_RECOMMENDED. This audit establishes that live `:8081` is current preserve and identifies `c0549d7` as the next bounded Cockpit Home integration target.

## Final Git Status

Final status at closeout:

```text
 M scripts/run_llama_server.sh
?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
?? docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md
```
