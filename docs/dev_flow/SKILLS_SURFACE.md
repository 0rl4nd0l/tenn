# Tenn Skill Surface

last_verified_commit: e402bf38e5b959f56c1bed6b35e18ba7371cd8f6
last_verified_pr: 386
verification_scope: repo-visible skill routing and source-map freshness only; host picker visibility not probed
source_of_truth_files:
- AGENTS.md
- docs/README.md
- docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/BACKEND_GUARDRAILS.md

## Purpose

Keep Tenn's repo-visible skill surface small. Orlando should usually choose a
core command, while backend guardrails, templates, and host skills stay behind
that command.

Visible skills are intentionally few. Add modes, sections, templates, or backend
scripts to an existing core command before adding another always-visible
`SKILL.md`.

## Operator-Facing Repo Commands

Use these as the normal entrypoints:

| Command skill | Use when |
| --- | --- |
| `tenn-issue` | A vague problem, "what next?", duplicate-work triage, or issue packet is needed. |
| `tenn-fix` | One approved task card, issue packet, or explicit fix is ready to implement. |
| `tenn-review-board` | A risky decision, merge-readiness call, architecture call, or owner-boundary needs multiple perspectives. |
| `tenn-explain` | Orlando asks for a plain-language status, architecture, issue, PR, branch, or subsystem explanation. |
| `tenn-goal-report` | A long `/goal` run needs state, validation, report, or handoff discipline. |
| `tenn-handoff` | Work must be packaged for a fresh session with git, ledger, validation, and next-goal context. |
| `tenn-financial-metric-extraction` | Issue-backed Financial Truth extraction work is explicitly in scope. |

## Specialist And Backend Skills

These are active repo-backed skills, but they are not normal first-stop
operator commands:

| Skill | Classification | Use when |
| --- | --- | --- |
| `tenn-git-guard` | backend guard | Wrappers need shared branch, worktree, dirty-state, registry, ledger, duplicate-work, task-card, and allowed-file preflight. |
| `codex-worker-bridge` | backend bridge | OpenCode/Codex worker bridge contracts or worker-result validation are explicitly in scope. |
| `tenn-improve-codebase-architecture` | specialist | The task explicitly asks for architecture improvement or deep refactoring opportunities and product/data boundaries are clear. |

## Core Modes Instead Of More Skills

These behaviors are modes inside existing commands, not new visible skills:

| Mode | Home | Use when |
| --- | --- | --- |
| Fresh-session orchestrator | `tenn-fix` plus `WORKER_TASK.md` and `WORKER_RESULT.md` | A handoff, problem statement, board decision, or long repair needs lane splitting, bounded workers, review, integration, validation, and closeout. |
| Fresh-session continuation | `tenn-handoff` plus `HANDOFF.md` and `HANDOFF_NEXT_GOAL.md` | Work must survive a context break with linked artifacts, next-first action, do-not-touch boundaries, milestones, and an orchestrator prompt. |
| Zoom-out / contrarian check | `tenn-explain`, `tenn-review-board`, `EXPLAIN.md`, and board templates | The workflow may be solving the wrong problem, overfitting, looping on reports, or missing broader production-readiness value. |

Handoff owns fresh-session continuation. Its report-local `NEXT_GOAL.md` should
be produced from `HANDOFF_NEXT_GOAL.md`: short, handoff-specific, and explicit
that the next session reads `HANDOFF.md` first, runs preflight, then acts as
orchestrator when work remains. The shared `NEXT_GOAL.md` template stays
generic for `tenn-issue`, `tenn-review-board`, and other non-handoff producers.

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
branch, worktree, dirty-state, registry, task-ledger, duplicate-work, task-card,
and allowed-file preflight.

The guard must use the portable skill runner before requiring repo-local Tenn
scripts. Runtime/product repos are valid guard targets even when they do not
contain `scripts/agent_job_registry.py`, `scripts/agent_task_ledger.py`, or
`scripts/agent_job_contract.py`; missing ledger rows should be reported as
`DATA_MISSING`, not as missing runtime repo files.

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
| `tenn-auto-progress` | Internal candidate ranking in `tenn-issue`; optional dry-run backend in `scripts/auto_progress.py`. |
| `tenn-frame-design` | Optional frame mode in `tenn-goal-report`; `docs/dev_flow/templates/FRAME.md` and `OPERATOR_NOTES.md`. |
| `tenn-git-hygiene` | Common preflight in `tenn-git-guard`; explicit cleanup audits follow the two-shot policy below. |
| `tenn-worker` | Worker delegation rules in `tenn-fix`, `WORKER_TASK.md`, and `WORKER_RESULT.md`. |
| `tenn-code-reviewer` | Final PR/diff review gate in `tenn-fix` and `PR_REVIEW.md`, using the host code-reviewer stance under Tenn gates. |
| `tenn-task-card-registry-safety` | Task-card, registry, dirty-state, and allowed-file checks in `tenn-git-guard` and `tenn-fix`. |

## Explicit Git Hygiene Audits

For non-trivial dirty-work or cleanup planning, use `/issue` or `/fix` with an
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

- First ask whether the behavior is a mode of `tenn-issue`, `tenn-fix`,
  `tenn-review-board`, `tenn-explain`, `tenn-goal-report`, or `tenn-handoff`.
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
- Confirm the count did not increase unless a task-card design note explicitly
  justifies the increase.
- Confirm removed entrypoints are absent.
- Confirm core skill H1s still match their directory intent.
- Confirm only task-card-allowed control-plane docs, skills, templates, and
  report artifacts changed.
- Confirm product/runtime/data/extraction/count-24 and host-global paths did not
  change.
