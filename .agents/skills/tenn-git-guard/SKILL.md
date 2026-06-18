---
name: tenn-git-guard
description: Native Tenn Git Hygiene backend guard for branch, worktree, dirty-state, PR, and registry preflight. Use inside Tenn issue, review, fix, worker, explain, code-review, and architecture workflows before any mutation or readiness claim.
---

# Tenn Git Guard

`tenn-git-guard` is a quiet backend guard. It is not a user-facing cleanup
command by default.

Use it before `/issue`, `/review-board`, `/fix`, `worker`,
`/explain` for branch or PR topics, `code-reviewer`, and architecture work. Use
the existing `tenn-git-hygiene` skill for deeper cleanup planning, but keep this
wrapper focused on preflight and stop decisions.

## Preflight

Collect current evidence before relying on repo state:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git status --short --untracked-files=all
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
python3 scripts/agent_task_ledger.py resolve-path
python3 scripts/agent_task_ledger.py validate
```

## Task Ledger Preflight

`tenn-git-guard` owns duplicate-work preflight. Before any implementation-capable
workflow starts coding, inspect the branch-independent Agent Task Ledger and the
durable committed summary when present:

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
python3 scripts/agent_task_ledger.py resolve-path
python3 scripts/agent_task_ledger.py validate
python3 scripts/agent_task_ledger.py search --text "<topic-or-path>"
```

When `scripts/agent_task_ledger.py` is unavailable on an older base, fall back
to the manual checks below and record `DATA_MISSING` for runtime support.

Do not resolve the live ledger through literal `.git/tenn-agent-registry/task-ledger.jsonl`.
In linked worktrees, `.git` is a file pointing at a private worktree gitdir,
while shared repo state belongs under the configured registry root. Resolve the
live ledger from the same `<registry_root>` used by `scripts/agent_job_registry.py`:

1. `TENN_AGENT_REGISTRY_ROOT`
2. `git config tenn.agentRegistryRoot`
3. `git rev-parse --path-format=absolute --git-common-dir` plus
   `tenn-agent-registry`
4. If `--path-format=absolute` is unsupported, fall back to
   `git rev-parse --git-common-dir` and normalize any relative output against
   the worktree root before appending `tenn-agent-registry`
5. repo-local `.tenn/agent_jobs` fallback with a warning when git metadata is
   unavailable

Then append `task-ledger.jsonl` to the resolved `registry_root`. When
`TENN_AGENT_REGISTRY_ROOT` or `tenn.agentRegistryRoot` is configured, use that
configured root instead of the git common dir so separate-clone and launcher
setups share the same duplicate-work state.

If either ledger file is unavailable, record `DATA_MISSING` for that source and
run a bounded fallback search before coding:

- task cards under `docs/agent_tasks/`
- reports under `reports/agent_jobs/`
- local and remote branches
- worktrees
- open, closed, and merged PRs
- open and closed issues
- files likely to be touched by the proposed work

Use topic terms, issue numbers, PR numbers, branch names, task ids, and touched
paths from the owner request or task card. Keep searches read-only.

When session or thread identity is available from explicit environment/current
goal metadata, report it. If it is unavailable, report
`session_id=DATA_MISSING` and `thread_id=DATA_MISSING`; do not invent IDs.

Determine the comparison base before calculating merge-base:

1. Prefer an explicit task-card or owner-provided base when present.
2. When reviewing a PR, use that PR's base branch.
3. Otherwise use the upstream tracking branch when available.
4. Otherwise fall back to
   `origin/migration/clean-runtime-baseline-reconstruct-v1`.
5. Record `DATA_MISSING` and stop before mutation if no reliable base can be
   determined.

Then run `git merge-base HEAD <selected-base>` and record both the selected base
and merge-base SHA in the guard output.

If branch or PR context matters, use read-only GitHub inspection before
suggesting mutation:

```bash
gh pr list --state all --search "<branch-or-topic>" --json number,title,state,headRefName,baseRefName,updatedAt
gh issue list --state all --search "<topic>" --json number,title,state,updatedAt,labels
```

Record `DATA_MISSING` for unavailable commands, missing auth, missing upstream,
or unsafe command surfaces.

## Duplicate-Work Classification

Classify similar work before coding:

- `ACTIVE_CONTINUE`: an active ledger/task/worktree lane should be continued or
  adopted.
- `OPEN_PR_WAIT`: an open PR appears to cover the requested work; wait for it or
  review it instead of starting a duplicate.
- `MERGED_USE_CANONICAL`: merged work on the selected base already solves the
  request; use the canonical implementation.
- `STALE_PRESERVE`: stale or branch-local work may still be valuable and should
  be preserved, parked, or intentionally superseded before replacing it.
- `SUPERSEDED_IGNORE`: older work is safely superseded by current canonical
  state.
- `OWNER_BOUNDARY`: ownership, cleanup, adoption, supersede, or conflict
  decision needs Orlando.
- `UNKNOWN_ASK`: evidence is insufficient and the next meaningful step needs an
  owner decision.

Block implementation when matching active, open-PR, merged, or owner-boundary
work exists unless Orlando explicitly chooses continue, adopt, supersede, or
ignore. When only ledger evidence is missing but fallback search is clean, record
the `DATA_MISSING` source and allow the caller to proceed with a narrow scope.

Guard output must include `duplicate_work_classification`, evidence sources
checked, matching candidates, owner decision needed, and final decision:
`pass`, `warning`, `block`, or `data_missing`.
Include `session_id` and `thread_id` when available.

## Branch Superiority And Stale Work

Before recommending new implementation, search related branches, worktrees, PRs,
task cards, and reports for more advanced existing work. Classify each relevant
candidate:

- `ADOPT`: validated work should be used as-is.
- `CONTINUE`: useful work should become the active lane.
- `PRESERVE`: valuable stale work should be committed, PR'd, or parked when
  approved.
- `SUPERSEDED`: current base already covers it.
- `OWNER_BOUNDARY`: needs an owner decision before use or cleanup.
- `UNKNOWN`: evidence is insufficient.

Do not code over better existing work. Do not leave valuable stale work rotting
when a validated commit or PR path is in scope and approved.

## Hook Cooperation

Do not reimplement existing hooks. Treat them as backend guards:

- Host `goal_optimizer_pre_tool.py` warns on token or output burn.
- Host `stop_check.py` handles terminal dirty-warning suppression.
- Repo `scripts/agent_job_hook.py` handles task-card, registry, and diff
  contract checks.

Workflow commands should preflight branch, dirty-state, registry, and allowlist
problems before hooks fire. Stop hooks are backstops.

## Docs Impact Guard

For implementation-capable workflows, verify that closeout evidence includes a
Docs Impact Check before readiness, PR, or owner-ready claims. The guard should
not rewrite docs itself; it should classify missing or stale docs evidence as a
caller risk.

Required fields:

- `docs_impact`: `DOCS_NOT_REQUIRED | DOCS_UPDATED | DOCS_FOLLOWUP | DATA_MISSING`
- `docs_checked`
- `docs_changed`
- `docs_followup`
- `reason`

If behavior, schema, command usage, workflow, validation, operator steps,
artifact shape, API, data model, skill trigger, or safety boundary changed,
affected docs/templates/skills must be updated or a `DOCS_FOLLOWUP` must be
recorded. If no docs update is required, record `DOCS_NOT_REQUIRED` with a
reason. Do not let a PR close out with undocumented behavior changes.

For durable docs, templates, and skills, callers may add freshness metadata:
`last_verified_commit`, `last_verified_pr`, `source_of_truth_files`,
`stale_if_files`, `owner`, and `evidence_grade`.

## Validation Environment Autonomy

If a requested validation command fails because a standard validation tool is
missing, try safe existing or ephemeral validation environments before blocking.

Resolution order:

1. existing repo venv
2. documented repo test command
3. available dependency runner such as `uv`
4. ephemeral venv under `/tmp` or another throwaway path
5. `unittest` or stdlib fallback when equivalent
6. `WAITING_ON_USER` only after safe paths fail

Agents may install standard validation-only dependencies such as `pytest` into
an ephemeral environment when:

- no repo dependency files or lockfiles are changed
- no production/runtime venv is modified
- the dependency is only used for validation
- the command and result are recorded

Do not mutate project dependencies, CI config, system packages, runtime
services, or host-global config without explicit approval.

## Classify

Classify the worktree and dirty files:

- task-card or report artifact
- hook/config/control-plane file
- product/runtime/data path
- extraction/source/gold-label path
- generated or cache path
- owner-boundary or unknown path
- related PR or issue
- registry active job or `DATA_MISSING`

Block or narrow the workflow when dirty state overlaps the requested mutation
surface and ownership is unclear.

## Allowed Output

Produce short markdown or JSON in the caller's report directory:

- worktree path
- branch
- HEAD
- base and upstream
- dirty file summary
- owner-boundary paths
- related PRs/issues
- registry read-only status
- ledger sources checked
- duplicate-work classification
- docs impact status or `DATA_MISSING`
- decision: `pass`, `warning`, `block`, or `data_missing`

## Prohibited Actions

Do not clean, delete, reset, stash, merge, rebase, cherry-pick, push, force-push,
prune, close issues, comment on GitHub, mutate registry state, or remove
worktrees. Cleanup requires a separate explicit owner approval and a task card.
