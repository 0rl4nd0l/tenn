# Repo Path Ownership And Work Preservation

Status: control-plane source of truth for Tenn repo path ownership and
duplicate-work prevention after PR #397.

Last verified: 2026-06-23 from
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`b58c9f1ce79b5e9583b1b30cf98b3507867f0aeb`.

Scope: Codex development flow and Tenn control-plane only. This file is not
runtime, product, extraction, data, Greyhound, service, or host-global
authority.

## Canonical Branch

Tenn control-plane canonical branch:

```text
origin/migration/clean-runtime-baseline-reconstruct-v1
```

Verify the live remote before starting important work:

```bash
git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1
```

As of this audit, the canonical HEAD is:

```text
b58c9f1ce79b5e9583b1b30cf98b3507867f0aeb
```

Do not use `origin/HEAD` as Tenn canonical. It points at `origin/main` in this
repo, and that is not the requested control-plane base.

## First Command

Future sessions must run the portable guard first:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

From a Tenn control-plane checkout, use the repo-backed fallback only if the
installed host skill path is unavailable:

```bash
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json
```

For path audits, add `--audit-path <path>` for every candidate path that could
be a starting point, sparse evidence directory, stale checkout, or runtime-only
directory.

## Valid Starting Points

Valid starting points are narrow:

- `VALID_CANONICAL_WORKTREE`: a clean worktree on
  `migration/clean-runtime-baseline-reconstruct-v1` with HEAD equal to the live
  canonical remote.
- `VALID_TASK_WORKTREE`: a clean sibling worktree created from current
  canonical for one task, with a task-owned branch and exact task-card
  allowlist.

`/home/l4nd0/tenn` is only valid when current-turn evidence shows it is a
valid git worktree, clean or task-owned, and at the correct canonical base for
the task. In this audit it was not a valid starting point because it was on a
branch based on older canonical evidence.

This task used a fresh sibling worktree:

```text
/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623
```

That path is valid only for this task branch and its task-card allowlist.

## Invalid Or Restricted Known Paths

Current audit classifications:

| Path | Classification | Evidence |
| --- | --- | --- |
| `/home/l4nd0/tenn` | `STALE_PATH` | Branch `local/tenn-entrypoint-current-baseline-v1-20260623`, HEAD `fadd49daca28295228a3b2ac9b0cd8ec5a1af992`, merge-base `1a0f1a03741d692089a0125ecb2f10691b8da597`, not based on canonical `b58c9f1...`. |
| `/home/l4nd0/tenn-runtime` | `RUNTIME_DIR` | Resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`; requested path name indicates runtime surface and is not a git worktree. |
| `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | `SPARSE_EVIDENCE_DIR` | Contains repo-like evidence directories but no usable git worktree. |
| `/home/l4nd0/tenn-control-plane-task-ledger-status-refresh-v1-20260623` | `STALE_PATH` | Branch `control-plane/tenn-git-guard-global-runner-preservation-v1-20260623`, HEAD `db5976b88ea3b5f971c927d8609a6423a3336da4`, ancestor of canonical. |
| `/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623` | `VALID_TASK_WORKTREE` before edits; `DIRTY_RELATED_WORKTREE` during edits | Current task branch from canonical `b58c9f1...`; dirt is this task's allowed diff. |

For `SPARSE_EVIDENCE_DIR`, `RUNTIME_DIR`, `NOT_GIT_REPO`, `STALE_PATH`,
`DIRTY_RELATED_WORKTREE`, and `DATA_MISSING`, guard preflight must set
`path_ownership_blocks_implementation=true` and `stop_reimplementation=true`.

Do not mutate sparse evidence directories, runtime-only directories, stale
paths, or dirty unrelated worktrees. Preserve their evidence in reports, then
work from a clean sibling worktree when implementation is needed.

## If Cwd Is Not A Git Repo

Stop before implementation. Run portable guard against the path and record
`NOT_GIT_REPO`, `SPARSE_EVIDENCE_DIR`, `RUNTIME_DIR`, or `DATA_MISSING`.

Then either move to a verified Tenn control-plane worktree or create a fresh
sibling worktree from canonical:

```bash
git -C /home/l4nd0/tenn fetch origin migration/clean-runtime-baseline-reconstruct-v1
git -C /home/l4nd0/tenn worktree add -b <task-branch> /home/l4nd0/<task-worktree> origin/migration/clean-runtime-baseline-reconstruct-v1
```

Do not repair, clean, delete, reset, stash, rebase, prune, or move the wrong
path unless a separate approved task card authorizes that exact action.

## When To Create A Fresh Sibling Worktree

Create a fresh sibling worktree when:

- the current cwd is not a valid git worktree;
- the current worktree is dirty and the dirt overlaps the requested files;
- the current branch is behind canonical and the task is new implementation;
- the current path is sparse, runtime-only, or stale;
- related work exists elsewhere and the owner chooses a fresh continuation
  rather than adopting that branch directly;
- the task-card allowlist would otherwise absorb unrelated owner-boundary dirt.

Do not create a sibling worktree for trivial read-only inspection. Read-only
audits can use `git -C <path>` and portable guard output, but must not mutate
wrong or stale paths.

## Find Prior Work Before Implementing

Before implementation-capable work, search these surfaces:

- portable `tenn-git-guard` preflight with a topic;
- open PRs and all PRs related to the topic or likely touched files;
- local and remote branches related to the topic;
- registered worktrees from `git worktree list --porcelain`;
- Agent Task Ledger live and committed sources;
- Agent Job Registry read-only active jobs;
- merge parking registry;
- report bundles under `reports/agent_jobs/`;
- recent task cards under `docs/agent_tasks/`;
- GitHub issues when issue ownership or backlog state matters.

Use exact topic words, issue numbers, PR numbers, branch names, task ids, and
likely touched paths. Reports and memory are background evidence until
current-turn repo/GitHub/ledger evidence confirms them.

## Preservation Statuses

Use these statuses for existing related work:

| Status | Meaning | Action |
| --- | --- | --- |
| `ADOPT` | Merged or validated work already solves the need. | Use the canonical implementation or existing fix; do not reimplement. |
| `CONTINUE` | Active branch, worktree, or ledger lane should be continued. | Continue there or create an explicit continuation from it. |
| `MERGE_READY` | Open PR appears green and mergeable after live checks. | Review and merge/rebase only with explicit approval. |
| `PARK` | Valuable work exists but should not merge now. | Preserve branch/report/parking evidence; do not duplicate. |
| `SUPERSEDE` | Older work is worse or stale and current plan replaces it. | Record why and keep evidence visible. |
| `BLOCKED` | Owner decision or unsafe ambiguity is required. | Stop with `WAITING_ON_USER` or exact blocker. |
| `DUPLICATE` | Existing open/active work already covers this task. | Stop; review or wait for that work. |
| `DATA_MISSING` | Evidence is insufficient. | Stop for high-risk tasks; otherwise proceed only with narrow fallback evidence. |

Guard duplicate-work classifications map to preservation statuses:

| Guard classification | Preservation status |
| --- | --- |
| `ACTIVE_CONTINUE` | `CONTINUE` |
| `OPEN_PR_WAIT` | `DUPLICATE` |
| `MERGED_USE_CANONICAL` | `ADOPT` |
| `STALE_PRESERVE` | `PARK` |
| `SUPERSEDED_IGNORE` | `SUPERSEDE` |
| `OWNER_BOUNDARY` | `BLOCKED` |
| `UNKNOWN_ASK` | `DATA_MISSING` |
| `DATA_MISSING_FALLBACK_REQUIRED` or `DATA_MISSING_FALLBACK_CHECKED` | `DATA_MISSING` |

## Stop Instead Of Reimplementing

Stop before coding when:

- an open PR already covers the task;
- a branch or worktree contains a likely fix;
- a report, handoff, or task card says the work completed but was not merged;
- current cwd is not a valid Tenn git worktree;
- current branch is stale and the task should continue elsewhere;
- duplicate-work scan is `DATA_MISSING` for high-risk work;
- prior work is owner-boundary, parked, dirty, or ambiguous;
- adopting, superseding, parking, merging, or deleting work requires owner
  approval.

If the only gap is a missing ledger source and bounded fallback search is clean,
a narrow control-plane-only task may proceed with `DATA_MISSING` recorded in
the report. Product/runtime/data/extraction work should stop on the same gap
unless the owner explicitly accepts the risk.

## Preserve, Adopt, Park, Or Supersede

Old fixes are handled by evidence, not by memory:

- Preserve by committing approved local work, opening a PR, or parking with a
  report and registry entry when the owner approves that path.
- Adopt by continuing from the existing branch/PR or by using merged canonical
  behavior as the implementation source.
- Park by recording branch, HEAD, files, validation, blockers, and next owner
  decision in the merge parking registry or report bundle.
- Supersede by naming the old work, proving why current canonical or the new
  task replaces it, and leaving a grep-friendly report trail.

Never silently let old fixes rot in stray branches, and never silently
reimplement work that can be found from PRs, branches, worktrees, ledger,
registry, parking, task cards, or reports.
