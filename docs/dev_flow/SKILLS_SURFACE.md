# Tenn Skill Surface

last_verified_commit: acb7e9a7df6a9b75d14beff16c750693a4aab5e6
last_verified_pr: 375
source_of_truth_files:
- AGENTS.md
- docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md
- reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/BACKEND_GUARDRAILS.md

## Purpose

Keep Tenn's repo-visible skill surface small. Orlando should usually choose a
core command, while backend guardrails, templates, and host skills stay behind
that command.

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

## Backend Skills That Stay Visible

`tenn-git-guard` remains a visible repo skill because wrappers need a shared,
current preflight contract. It is not a user-facing cleanup command. It owns
branch, worktree, dirty-state, registry, task-ledger, duplicate-work, task-card,
and allowed-file preflight.

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

## Validation Checklist

- Count visible repo skill entrypoints with:
  `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- Confirm removed entrypoints are absent.
- Confirm core skill H1s still match their directory intent.
- Confirm only task-card-allowed control-plane docs, skills, templates, and
  report artifacts changed.
- Confirm product/runtime/data/extraction/count-24 and host-global paths did not
  change.
