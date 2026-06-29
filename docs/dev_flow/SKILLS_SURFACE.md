# Tenn Skill Surface

last_verified_at: 2026-06-25T06:32:20Z
last_verified_commit: b3b3a154590f36e61d297c1ac79fe623526f0b28
last_verified_pr: 409
freshness_model: ancestor_plus_behavior_stale_files
freshness_checked_at: 2026-06-26T05:30:36Z
freshness_checked_against: c877da6eb114826365339379f10a8a06e82221a5
maintenance: hand_maintained
verification_scope: repo-visible key and narrative-support skill routing, portable guard preflight guidance, and source-map freshness only; host picker visibility not probed
freshness_evidence:
- `git rev-parse origin/migration/clean-runtime-baseline-reconstruct-v1` -> `b3b3a154590f36e61d297c1ac79fe623526f0b28`
- `gh pr view 409 --json number,state,mergedAt,mergeCommit` -> PR #409 `MERGED`, merge commit `b3b3a154590f36e61d297c1ac79fe623526f0b28`
- `git rev-parse origin/migration/clean-runtime-baseline-reconstruct-v1` at freshness check -> `c877da6eb114826365339379f10a8a06e82221a5`
- `git merge-base --is-ancestor b3b3a154590f36e61d297c1ac79fe623526f0b28 origin/migration/clean-runtime-baseline-reconstruct-v1` -> exit `0`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort | wc -l` -> `12`
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort` -> no output; `.codex/skills` is absent in this snapshot
data_missing:
- Host picker/autocomplete visibility was not probed.
stale_if_files:
- `.agents/skills/**/SKILL.md`
- `.codex/skills/**/SKILL.md` if the legacy directory exists again
- `docs/dev_flow/SKILLS_SURFACE.md` behavior/routing sections; metadata-only
  freshness refreshes do not invalidate the audited skill surface
- `docs/dev_flow/templates/*`
source_of_truth_files:
- AGENTS.md
- docs/README.md
- docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md
- docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/BACKEND_GUARDRAILS.md

## Refresh Procedure

`last_verified_commit` is the audited source commit for this skill-surface
snapshot. It is not expected to equal current
`origin/migration/clean-runtime-baseline-reconstruct-v1` after every docs PR
merge. A snapshot remains fresh when `last_verified_commit` is an ancestor of
current canonical and no behavior-affecting `stale_if_files` changed after that
commit without a newer validation entry. Metadata-only updates to this file
should update `freshness_checked_at`, `freshness_checked_against`, and
`freshness_evidence`; they should not churn `last_verified_commit` just to
match the latest merge commit.

To refresh this file, work from current
`origin/migration/clean-runtime-baseline-reconstruct-v1`, run the visible skill
count commands above, inspect `.agents/skills/*/SKILL.md` and legacy
`.codex/skills/*/SKILL.md` additions/removals if that directory exists, and update
`last_verified_at`, `last_verified_commit`, and `last_verified_pr` only when a
behavior-affecting skill-surface source changed or a full skill-surface audit is
rerun. For freshness-only checks, update `freshness_checked_at`,
`freshness_checked_against`, `freshness_evidence`, and `data_missing` instead.
Do not infer host picker visibility from repo files; record it as
`DATA_MISSING` unless it is probed directly.

## Purpose

Keep Tenn's repo-visible skill surface limited to key Tenn commands and
explicit narrative-support utilities. Orlando should usually choose a retained
core command, while backend guardrails, templates, and host skills stay behind
that command.

Visible skills are intentionally few. Add modes, sections, templates, or backend
scripts to an existing key command before adding another always-visible
`SKILL.md`.

## Operator-Facing Repo Commands

Use these as the normal user-facing entrypoints:

| Command skill | Use when |
| --- | --- |
| `tenn-issue` | A vague problem, "what next?", duplicate-work triage, or issue packet is needed. |
| `tenn-fix` | One approved task card, issue packet, or explicit fix is ready to implement. |
| `tenn-review-board` | A risky decision, merge-readiness call, architecture call, or owner-boundary needs multiple perspectives. |
| `tenn-explain` | Orlando asks for a plain-language status, architecture, issue, PR, branch, or subsystem explanation. |
| `tenn-goal-report` | A long `/goal` run needs state, validation, report, or handoff discipline. |
| `tenn-handoff` | Work must be packaged for a fresh session with git, ledger, validation, and next-goal context. |
| `tenn-financial-metric-extraction` | Issue-backed Financial Truth extraction work is explicitly in scope. |
| `zoom-out` | Orlando asks to step up a layer, map the bigger problem, or check whether the current work is solving the right problem. |
| `caveman` | Orlando asks for ultra-terse communication. |

## Specialist And Backend Skills

These are active repo-backed skills, but they are not normal first-stop
operator commands:

| Skill | Classification | Use when |
| --- | --- | --- |
| `tenn-git-guard` | backend guard | Wrappers need shared branch, worktree, dirty-state, registry, ledger, duplicate-work, task-card, and allowed-file preflight. |
| `codex-worker-bridge` | backend bridge | OpenCode/Codex worker bridge contracts or worker-result validation are explicitly in scope. |
| `tenn-improve-codebase-architecture` | specialist | Architecture improvement or deep refactoring opportunities are explicitly requested and product/data boundaries are clear. |

## Core Modes Instead Of More Skills

These behaviors are modes inside existing commands, not new visible skills:

| Mode | Home | Use when |
| --- | --- | --- |
| Fast progress lane | `tenn-fix`, `tenn-git-guard`, and focused validation | A small docs/control-plane or narrow code fix has exact files, no runtime/data/extraction/GitHub/destructive boundary, and no stale/dirty/duplicate blocker. |
| Fresh-session orchestrator | `tenn-fix` plus `WORKER_TASK.md` and `WORKER_RESULT.md` | A handoff, problem statement, board decision, or long repair needs lane splitting, bounded workers, review, integration, validation, and closeout. |
| Fresh-session continuation | `tenn-handoff` plus `HANDOFF.md` and `HANDOFF_NEXT_GOAL.md` | Work must survive a context break with linked artifacts, next-first action, do-not-touch boundaries, milestones, and an orchestrator prompt. |
| Zoom-out / contrarian check | `zoom-out`, `tenn-explain`, `tenn-review-board`, `EXPLAIN.md`, and board templates | The workflow may be solving the wrong problem, overfitting, looping on reports, or missing broader production-readiness value. |

Fast progress is action-first, not safety-free. It still needs current path
proof, exact task-card scope when editing, focused validation, and honest
closeout. It skips review boards, handoffs, workers, broad reports, and full
branch/worktree fallback detail unless a real blocker appears.

Handoff owns fresh-session continuation. Its report-local `NEXT_GOAL.md` should
be produced from `HANDOFF_NEXT_GOAL.md`: short, handoff-specific, and explicit
that the next session reads `HANDOFF.md` first, runs preflight, then acts as
orchestrator when work remains. The shared `NEXT_GOAL.md` template stays
generic for `tenn-issue`, `tenn-review-board`, `tenn-fix`, and other
non-handoff producers.

Orchestration is a mode, not a broad new skill. `tenn-fix` owns delegation
discipline: split independent lanes, give each worker exact allowed files,
decision limit, result path, and stop condition, then review outputs before
integrating one coherent change at a time. Small workers do not make final
high-risk decisions.

Zoom-out is also a mode, not a separate always-visible command. Use it inside
`tenn-explain` or `tenn-review-board` to ask whether the real root problem is
being solved, whether the work is overfitting to one artifact, whether the run
is stuck in report-only loops, and what next action has the highest
production-readiness value. For financial extraction, favor failure classes,
document classes, breadth, provenance, confidence, and regression coverage over
one-off PDF fixes.

## Backend Guard That Stays Visible

`tenn-git-guard` remains a visible repo skill because wrappers need a shared,
current preflight contract. It is not a user-facing cleanup command. It owns
branch, worktree, path ownership, dirty-state, registry, task-ledger,
duplicate-work, task-card, and allowed-file preflight.

The guard must use the portable skill runner before requiring repo-local Tenn
scripts. Runtime/product repos are valid guard targets even when they do not
contain `scripts/agent_job_registry.py`, `scripts/agent_task_ledger.py`, or
`scripts/agent_job_contract.py`; missing ledger rows should be reported as
`DATA_MISSING`, not as missing runtime repo files.

For candidate path audits, add `--audit-path <path>` and classify results with
`docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md`. Do not start
implementation from `NOT_GIT_REPO`, `SPARSE_EVIDENCE_DIR`, `RUNTIME_DIR`,
`STALE_PATH`, `DIRTY_RELATED_WORKTREE`, or ambiguous `DATA_MISSING` paths.

First-class preflight command:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

The default preflight uses summarized branch/worktree fallback output. Use full
fallback detail only when it is part of the decision:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --fallback-detail full --json
```

Repo-backed fallback from a Tenn control-plane checkout:

```bash
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json
```

## Runtime Proof Gate

Use this mode when daemon, runtime, extraction, ingestion, automation,
collector, scheduler, service, or pipeline functionality is claimed.

| Mode | Home | Use when |
| --- | --- | --- |
| Runtime proof gate | `AGENTS.md`, `tenn-fix`, `tenn-explain`, `tenn-review-board`, `tenn-handoff` | A closeout, explanation, board decision, merge/promotion call, or handoff says runtime-like work is working, functional, complete, or `DONE`. |

This mode must use the `Runtime Functionality Proof` table in `AGENTS.md`. It
does not add a visible skill. Activity evidence such as services, timers, logs,
artifacts, reports, tests, or merged PRs must stay separate from functionality
evidence that proves the intended live output is fresh or changed.

## Rehomed Entry Points

These `SKILL.md` entrypoints were removed to reduce default context and avoid
planning loops. Restore from git only if a future task proves the behavior needs
a first-class visible skill again.

| Removed entrypoint | New home |
| --- | --- |
| `tenn-auto-progress` | Internal candidate ranking in `tenn-review-board` or `tenn-fix`; optional dry-run backend in `scripts/auto_progress.py`. |
| `tenn-frame-design` | Optional frame mode in `tenn-fix` reports; `docs/dev_flow/templates/FRAME.md` and `OPERATOR_NOTES.md`. |
| `tenn-git-hygiene` | Common preflight in `tenn-git-guard`; explicit cleanup audits follow the two-shot policy below. |
| `tenn-worker` | Worker delegation rules in `tenn-fix`, `WORKER_TASK.md`, and `WORKER_RESULT.md`. |
| `tenn-code-reviewer` | Final PR/diff review gate in `tenn-fix` and `PR_REVIEW.md`, using the host code-reviewer stance under Tenn gates. |
| `tenn-task-card-registry-safety` | Task-card, registry, dirty-state, and allowed-file checks in `tenn-git-guard` and `tenn-fix`. |
| `.codex/skills/cockpit-flag-orchestrator` | Legacy cockpit triage should use Tenn task cards, reports, GitHub issues, and the retained key skills. |

## Explicit Git Hygiene Audits

For non-trivial dirty-work or cleanup planning, use `tenn-fix` with an
exact task card and this two-shot policy:

- Shot 1: inspect, classify, preserve safe evidence, write
  `APPROVAL_MANIFEST.md`, write `EXECUTION_PLAN_FOR_SHOT_2.md`, and stop.
- Shot 2: execute only approved manifest groups mechanically, skip drifted
  paths, stop before forbidden boundaries, and write closeout.

Do not clean, delete, reset, stash, rebase, merge, cherry-pick, push, mutate
GitHub, or mutate registry state unless the current task card and owner approval
explicitly permit that exact action.

## Reversal Procedure

This trim is reversible:

1. Restore the needed `.agents/skills/<name>/SKILL.md` from a prior commit.
2. Update this file to explain why the entrypoint is visible again.
3. Update the affected core skill or template to remove duplicate wording.
4. Validate the task card, skill H1/frontmatter, `git diff --check`, and
   `check-diff`.

## Avoiding Skill Bloat Regression

- First ask whether the behavior is a mode of an existing approved skill,
  especially `tenn-issue`, `tenn-fix`, `tenn-review-board`, `tenn-explain`,
  `tenn-goal-report`, `tenn-handoff`, `zoom-out`, or
  `tenn-improve-codebase-architecture`.
- Prefer updating a core skill section and a template over adding a new
  `.agents/skills/<name>/SKILL.md`.
- A new visible skill needs a task-card design note proving that a mode would
  hide necessary operator intent or make safety worse.
- Keep backend-only guardrails in scripts, docs, or templates unless first-class
  invocation is genuinely required.
- Any new visible skill must update this file, preserve the old count in the
  report bundle, explain why the count increased, and pass the visible skill
  count check.

## Validation Checklist

- Count visible repo skill entrypoints with:
  `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- Confirm the legacy custom repo skill surface has no visible entrypoints with:
  `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- Confirm the count did not increase unless a task-card design note explicitly
  justifies the increase.
- Confirm removed entrypoints are absent.
- Confirm core skill H1s still match their directory intent.
- Confirm only task-card-allowed control-plane docs, skills, templates, and
  report artifacts changed.
- Confirm product/runtime/data/extraction/count-24 and host-global paths did not
  change.
