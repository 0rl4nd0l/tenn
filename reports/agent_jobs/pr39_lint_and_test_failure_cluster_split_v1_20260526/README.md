# PR #39 CI Failure Cluster Split

## Verdict

PR #39 is **NOT_MERGE_READY** and should remain draft. The latest current PR
head on GitHub is still `8635833b7d7359ed55daf0495eb49c5457bab91d`; it failed
CI run `26439822448` / job `77831209696` in `Pytest (backend + cockpit)`.
`Sloppy Scan` passed as run `26439822445`.

This audit did not fix product code, tests, dependencies, workflow files,
runtime state, data stores, or GitHub state.

## Preflight

| Item | Result |
| --- | --- |
| Active cwd | `/home/l4nd0/tenn-runtime` |
| Active realpath | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Active branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| Active HEAD | `730eb0d8fb6d1d1661a87a5076201ab2521ade60` |
| Git status before task card | clean |
| Git status after task card/report writes | allowed task card plus ignored allowed report bundle |
| Final unrelated dirty work | `financial-engine_v2/cockpit/core/actions.py`, `financial-engine_v2/cockpit/core/tools.py`, `financial-engine_v2/worker/worker_app/news_tasks.py`, `scripts/backfill_news.py`, `scripts/fetch_daily_news.py`, `scripts/load_news_to_qdrant.py`, `scripts/news_pipeline/cli_common.py`, `scripts/run_news_pipeline.py`, and `financial-engine_v2/shared/tenn_extraction_active.json` appeared outside this task allowlist and were not touched |
| Worktree count | 253 worktrees reported by `git worktree list --porcelain` |
| PR-head worktree present | `/home/l4nd0/tenn-extraction-orchestrator-parallel-safe-progress-v1-20260526` at `8635833b...` |
| Canonical Tenn checkout | yes: `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`, origin `https://github.com/0rl4nd0l/tenn.git` |

Recent active-branch commits include:

- `730eb0d8` milestone(news): repair nightly sync ollama url resolution
- `e45ae517` chore(repo-hygiene): release restart route audit job
- `e2843d03` chore(repo-hygiene): record restart route closeout
- `49c6e98e` fix(cockpit): guard backend restart route
- `82e62c3f` milestone(evaluation): integrate extraction eval foundation

The local active branch has advanced beyond the GitHub PR #39 head. This audit
uses GitHub PR/check/run evidence for PR readiness, not local HEAD as a
substitute for the PR state.

## Task And Registry

- Task card: `docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
- Task card validation: passed
- Registry `list-active --read-only`: ok, empty before claim
- Registry `check-overlap`: ok
- Registry claim: ok
- Registry release: ok
- GitHub mutation: none
- Production data access: false

## PR #39 State

| Field | Current GitHub value |
| --- | --- |
| PR | #39 `[codex] integrate trust foundation next phase` |
| State | open |
| Draft | true |
| Mergeable | MERGEABLE |
| Merge state | UNSTABLE |
| Head ref | `migration/clean-runtime-baseline-reconstruct-v1` |
| Head SHA | `8635833b7d7359ed55daf0495eb49c5457bab91d` |
| Base ref | `migration/clean-runtime-baseline-reconstruct-base-36130cbd` |
| Base SHA | `36130cbdb98e7084e8396d125a1d6f8d3ab48bc7` |
| Commits | 38 |
| Changed files | 346 |
| Additions / deletions | 39,618 / 190 |

The known PR shape still matches GitHub: open, draft, unmerged, 38 commits, 346
changed files, 39,618 additions, 190 deletions, head `8635833b...`.

## CI Evidence

| Check | Run | Job | Result | Notes |
| --- | --- | --- | --- | --- |
| CI / lint-and-test | `26439822448` | `77831209696` | failed | `Pytest (backend + cockpit)` failed; Ruff passed; autodev pytest skipped |
| Sloppy Scan / scan | `26439822445` | `77831209694` | passed | same PR head SHA |

Latest failed log conclusion for run `26439822448`:

- Setup, checkout, setup-python, dependency install, advisory pip-audit, and Ruff passed.
- `Pytest (backend + cockpit)` failed.
- `Pytest (autodev)` did not run because the prior pytest step failed.
- Current run summary: `63 failed, 2842 passed, 18 skipped, 1 deselected, 57 warnings, 48 subtests passed`.

This supersedes the older issue-body sample that mentioned 65 failures.

## Cluster Map

| ID | Count | Cluster | Classification | Baseline vs PR | Next action |
| --- | ---: | --- | --- | --- | --- |
| C01 | 6 | Backend sqlite3/uuid4/vector invariants | architecture_invariant_policy_mismatch | mixed | child task |
| C02 | 15 | Cockpit chat/session `llm_client` contract drift | dependency_or_api_drift | inherited | child task |
| C03 | 14 | Cockpit subagent event-loop assumption | dependency_or_api_drift | mixed | child task |
| C04 | 5 | Streaming subprocess helper requires `job_id` | dependency_or_api_drift | inherited | child task |
| C05 | 5 | `load_news_to_qdrant` Ollama URL API drift | dependency_or_api_drift | inherited | child task |
| C06 | 5 | Marketplace time-sensitive fixture drift | test_drift | inherited | child task |
| C07 | 4 | Cockpit agent stress grounding/action expectations | test_drift | inherited | child task |
| C08 | 3 | Hybrid router policy/callback contract | product_regression | inherited | child task |
| C09 | 2 | Memo extractor signal routing stores no signals | product_regression | inherited | child task |
| C10 | 1 | Preferences API response shape expanded | dependency_or_api_drift | DATA_MISSING | child task |
| C11 | 1 | Missing real-gold 10X PDF asset | missing_asset | inherited | child task |
| C12 | 1 | Process-document API hits Redis/Celery in CI | ci_environment_dependency | mixed | child task |
| C13 | 1 | Query orchestrator sufficiency guard regression | product_regression | DATA_MISSING | child task |

Full machine-readable cluster details are in `failure_clusters.json`.

## Baseline-vs-PR Notes

No same-shape successful baseline CI run was found for base SHA
`36130cbdb98e7084e8396d125a1d6f8d3ab48bc7`. The strongest evidence available
is a file-diff heuristic:

- PR #39 changed `.github/workflows/ci.yml` to install
  `financial-engine_v2/backend/requirements-dev.txt`.
- PR #39 changed `financial-engine_v2/backend/requirements-dev.txt`.
- Most failing code/test files are unchanged between PR base and PR head.
- Therefore many failures appear inherited or newly exposed by deeper CI
  execution, not directly introduced by product edits in PR #39.
- `scripts/load_news_to_qdrant.py` has a local post-PR-head repair at current
  local HEAD `730eb0d8`, but that repair is not in the current GitHub PR #39
  head and no PR rerun was requested.

## Duplicate Checks

GitHub issue/PR searches found open issue #105 and PR #39 as the live trackers.
Searches for the individual clusters did not find separate open duplicate
trackers for sqlite3/uuid4 invariants, real-gold asset, Ollama URL API drift,
marketplace stale benchmark drift, Redis/Celery process-document CI dependency,
streaming subprocess `job_id`, Cockpit subagents event loop, or Cockpit router
stress behavior. Closed #66 is only the precursor audit. Closed #55 is
remediated and removed from this queue.

## What This Proves

- PR #39 is currently red on GitHub at head `8635833b...`.
- The current failing job and run IDs are known.
- Failures are not one vague bucket; they split into 13 actionable clusters.
- The highest-risk clusters are architecture invariants, Cockpit chat/router
  contract drift, missing gold asset, query sufficiency, memory signal routing,
  and CI dependency isolation.
- No forbidden surfaces were changed by this audit.

## What This Does Not Prove

- It does not prove every cluster is introduced by PR #39.
- It does not prove current local HEAD would pass CI if pushed or rerun.
- It does not repair any root cause.
- It does not authorize broad test rewrites, workflow changes, runtime starts,
  data-store mutation, PR updates, merges, rebases, or GitHub issue mutation.

## Recommended Next Safe Actions

1. Keep #105 open until child remediation tasks land and PR #39 has a fresh
   green CI run or explicit parking decision.
2. Keep PR #39 draft.
3. Split child tasks from `child_task_proposals.md`; start with C01, then C02
   through C05.
4. Treat local commit `730eb0d8` as evidence that C05 may already have a local
   candidate fix, but do not update PR #39 without separate approval.
5. Do not close #66 again; it is already closed and remains only historical
   precursor evidence.
6. Do not reopen #55; it is closed/remediated and out of this queue.

## DATA_MISSING

- Same-shape base CI run for base SHA `36130cb...`.
- Fresh PR #39 CI after local branch advanced to `730eb0d8`.
- Exact root-cause proof for C10 and C13 without running focused local tests or
  editing code, both out of scope for this audit.
- Clean final task-card `check-diff` after report generation. It initially
  passed when only this task card was visible, then final `check-diff` failed
  because unrelated dirty work appeared outside this task allowlist. The current
  `diff-check.json` records that blocker.

## Hard Blockers

- Final check-diff is blocked by unrelated dirty work outside the PR39 audit
  allowlist. The dirty state was moving while an unrelated registry job was
  active. No cleanup, stash, reset, or overwrite was performed.

## Project Memory Save

Project Memory save is **RECOMMENDED** after review because this is a durable PR
#39/#105 cluster map and will guide multiple follow-up tasks. It is not required
before review because no product remediation landed in this job.
