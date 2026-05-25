# Tenn GitHub Issue System Protocol

## Summary

GitHub Issues are Tenn's live actionable backlog. Reports, task cards, memory,
and merge parking support the backlog, but they must not become disconnected
places where real bugs and follow-ups disappear.

## Source Roles

- GitHub Issues: live actionable backlog for confirmed bugs, gaps, trust risks,
  follow-ups, blockers, and work that needs a task card.
- Milestones: execution batches that group issues by current operating focus.
- Projects: dashboard and view layer for filtering, prioritizing, and tracking
  issue state across lanes.
- Task cards: execution contracts that define allowed files, surfaces, mode,
  validation, hard stops, and whether GitHub mutation is approved.
- Reports: evidence artifacts, matrices, validation output, and closeout proof.
- Project Memory: durable coordination memory and search hints, not current
  truth and not a substitute for GitHub issue tracking.
- Merge parking: completed-but-unmerged review queue. Parking is not merge
  approval and is not a closed issue unless the parked item is linked.

## Label Policy

Issue skills should recommend these labels and apply them only when the current
task card or user instruction explicitly permits GitHub mutation:

- `lane:*`: primary ownership lane.
- `mode:*`: audit, safe-extension, implementation, result-review, or closeout.
- `priority:*`: P0, P1, P2, or P3 urgency.
- `risk:*`: low, medium, high, or boundary-sensitive risk.
- `state:*`: ready, blocked, parked, needs-review, duplicate, superseded, or done.
- `type:*`: bug, gap, trust-risk, seed-regression, usability, repo-control,
  runtime, follow-up, audit, or docs.

Recommended labels must be included in issue drafts even when live label
application is not approved.

## Milestone Policy

Recommend one milestone when the issue naturally belongs to an execution batch:

- `M0 Control Plane Hardening`
- `M1 Trust / Provenance Foundation`
- `M2 Evaluation Spine`
- `M3 Query + Memory Integrity`
- `M4 Financial Truth Expansion`
- `M5 Cockpit Analyst Workflow`
- `M6 Runtime / Local Automation`

Do not invent milestones during validation. If the milestone does not exist or
GitHub mutation is not approved, record it as a recommendation only.

## Project Policy

When Projects are available, recommend field values rather than relying on
labels alone:

- Lane
- Mode
- Risk
- Priority
- Status
- Task Card
- Report Path
- Blocked By
- Root Cause Fixed
- Follow-up Required
- Production Data Access

If Project access or schema is missing, record `DATA_MISSING` and keep the issue
body complete enough to backfill the Project later.

## PR Link Policy

- Use `fixes #X` only when product remediation actually landed, validation
  passed, and the issue should auto-close on merge.
- Use `refs #X`, `audit for #X`, or normal references for audit-only,
  report-only, partial, parked, exploratory, or follow-up work.
- Never let an audit-only PR auto-close a remediation issue.
- If a PR is only evidence, report generation, or issue triage, keep the issue
  open unless every unresolved actionable item is tracked elsewhere.

## Branch Hygiene / Merge Visibility

Branches and worktrees are evidence-bearing control-plane state. Isolated
branches and worktrees are preferred for safe Tenn work, but completed, blocked,
or abandoned branch work must not silently age out. A branch with possible value
must be linked to an issue, PR, task card, report, or explicit parking entry, or
it must be marked `DATA_MISSING` with the exact evidence needed for review.

Branch review is non-destructive. Classification does not approve merge,
archive, deletion, pruning, reset, rebase, cherry-pick, or cleanup. Destructive
branch cleanup requires a separate explicit approval and a task card whose
allowed operation names that cleanup.

Use these branch classifications:

- `ACTIVE_LINKED`: active branch or worktree with a visible issue, PR, task
  card, report, or owner link and no current cleanup decision needed.
- `PARKED_READY_FOR_REVIEW`: completed or frozen work with visible task/report
  evidence, validation, changed-file summary, and no known rebase/CI/dependency
  blocker. This is ready for human or result-review triage, not merge approval.
- `PARKED_NEEDS_REBASE`: useful work is visible, but the branch is stale,
  divergent, conflicts with the current base, or needs a refresh before review.
  Do not rebase during audit unless separately approved.
- `BLOCKED_BY_CI`: the branch or PR is blocked by failing, missing, or
  unavailable CI/check evidence. Link logs when available; otherwise record
  `DATA_MISSING`.
- `BLOCKED_BY_DEPENDENCY`: the branch depends on another issue, PR, branch,
  validation artifact, operator decision, or unavailable environment.
- `SUPERSEDED`: another branch, PR, commit, issue, or report clearly covers the
  same objective and validation path. Link the replacement before any closure.
- `STALE_UNKNOWN_NEEDS_AUDIT`: the branch has unique commits, meaningful changed
  files, unclear merge state, validation evidence, or possible Tenn product or
  control-plane value, but current evidence is insufficient to park, supersede,
  or archive it.
- `SAFE_TO_ARCHIVE_CANDIDATE`: current evidence shows no unique commits, no
  meaningful unmerged file changes, or full coverage by a linked replacement.
  This is only a candidate; actual archive/delete/prune still requires separate
  explicit approval.

Branch review issues should not be created for every stale branch. Create or
draft them only when current evidence shows at least one of:

- unique commits not already reachable from the target base;
- meaningful changed files or report/task artifacts;
- unclear merge state, branch ownership, or validation status;
- validation evidence that may be useful later;
- possible product, evaluation, reporting, repo-hygiene, or control-plane value.

Use current local and remote-tracking refs as evidence. If remote branch or PR
state needs refresh and the current task does not approve GitHub or ref
mutation, record `DATA_MISSING` instead of fetching or changing refs.

Recommended tracking for branch review issues:

- Labels: `lane:repo-hygiene`, `type:control-plane`,
  `state:needs-review` / `state:parked` / `state:blocked` /
  `state:data-missing`, `risk:medium` or `risk:high`, and `mode:audit` or
  `mode:result-review`.
- Milestone: `M0 — Control Plane Hardening`.
- Link the branch name, worktree path when present, base commit, branch HEAD,
  changed-file summary, validation evidence, duplicate/supersession check, and
  the classification.

## Audit Closeout Rule

An audit issue can close only if every unresolved actionable finding is one of:

- linked to an existing GitHub issue or PR;
- converted into a new GitHub issue when approved;
- parked for merge or review with a visible parking link;
- marked `NO_FOLLOWUP` with a reason; or
- marked `DATA_MISSING` with the exact evidence needed.

Otherwise leave the issue open with a blocker or status comment.

## Follow-Up Issue Rule

For `FOLLOWUP_REQUIRED` findings, issue-finder and closeout skills must create
or link a GitHub issue when explicitly approved. Each follow-up issue must
include:

- `## Summary` in plain language.
- Lane and supporting lanes.
- Mode.
- Recommended labels.
- Recommended milestone.
- Optional Project field values.
- Task-card path.
- Report path.
- Allowed and forbidden surfaces.
- Validation plan.
- Hard stops.
- Definition of done.

## Branch Review Issue Body Template

Use this body for authorized branch review issue creation or for drafts:

```markdown
## Task
`<job_id>`

## Lane
Primary lane: Repo Hygiene
Supporting lanes: Reporting, Evaluation
Mode: audit / result-review

## GitHub Tracking
Recommended labels: lane:repo-hygiene, type:control-plane, mode:<audit/result-review>, risk:<medium/high>, state:<needs-review/parked/blocked/data-missing>
Recommended milestone: M0 — Control Plane Hardening
Project fields: Lane=Repo Hygiene; Mode=<audit/result-review>; Risk=<medium/high>; Priority=<P1/P2/P3>; Status=<Needs Review/Parked/Blocked/Data Missing>; Task Card=<task_card_path>; Report Path=<report_path>; Blocked By=<issue/PR/branch/none>; Root Cause Fixed=NO; Follow-up Required=YES; Production Data Access=NO

## Branch
- Branch: `<branch>`
- Worktree: `<path or DATA_MISSING>`
- Base ref / commit: `<base>`
- Branch HEAD: `<head>`
- Classification: ACTIVE_LINKED / PARKED_READY_FOR_REVIEW / PARKED_NEEDS_REBASE / BLOCKED_BY_CI / BLOCKED_BY_DEPENDENCY / SUPERSEDED / STALE_UNKNOWN_NEEDS_AUDIT / SAFE_TO_ARCHIVE_CANDIDATE

## Summary
In plain language:
- What the branch appears to contain:
- What it may impact:
- Why review or parking matters:
- What evidence is missing, if any:

## Evidence
- Unique commits: `<command/result or DATA_MISSING>`
- Changed files: `<summary or DATA_MISSING>`
- Existing issue/PR/task/report links: `<links or DATA_MISSING>`
- Validation evidence: `<commands/reports or DATA_MISSING>`
- Supersession/duplicate check: `<replacement link or DATA_MISSING>`

## Required task card
`docs/agent_tasks/<job_id>.md`

## Required output
`reports/agent_jobs/<job_id>/`

## Allowed files / surfaces
- Branch review report artifacts.
- Issue/PR comments or labels only if explicitly approved.

## Forbidden files / surfaces
- product/backend/frontend/runtime code unless a later implementation task allows it
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- runtime/model/GPU/service config
- branch delete/prune/reset/stash/merge/rebase/cherry-pick without separate explicit approval
- unrelated dirty work

## Acceptance criteria
- Branch classification is evidence-backed or marked `DATA_MISSING`.
- Useful work is linked to an issue, PR, task card, report, or parking entry.
- Superseded or archive-candidate status links the replacement or evidence.
- No destructive branch cleanup occurs in this task.

## Validation
- `git branch --contains` / `git branch --no-merged` or equivalent read-only checks.
- `git log --left-right --cherry-pick --oneline <base>...<branch>` where safe.
- `git diff --name-status <base>...<branch>` where safe.
- Existing report/test/CI evidence, or `DATA_MISSING`.
```

## Issue Template Policy

Use the repo-native GitHub Issue Forms under `.github/ISSUE_TEMPLATE/` for new
Tenn issues whenever the task card approves issue drafting or live issue
creation:

- `tenn_task.yml` for planned task-card-ready work.
- `tenn_bug_regression_seed.yml` for confirmed bugs and seed regressions.
- `tenn_audit_finding.yml` for audit-only findings.
- `tenn_followup_remediation.yml` for unresolved findings from closed or
  completed audits.
- `tenn_branch_merge_review.yml` for branch, worktree, merge, and PR visibility.

Template body classifications are not labels unless they use an activated
`lane:*`, `mode:*`, `priority:*`, `risk:*`, `state:*`, or `type:*` value.

## De-Duplication Rule

Before creating any issue, search:

- open issues;
- closed issues;
- open and closed PRs;
- recent reports and task cards; and
- merge parking entries.

Do not duplicate an issue when an existing tracker covers the same root cause,
lane, validation path, and hard stops. Similar symptoms alone are not enough to
declare a duplicate.

## Automation Alignment

Automated reports should do one of these:

- create issue-ready findings;
- draft issue-ready findings when GitHub mutation is not approved;
- update existing issue references when approved; or
- mark low-value or unsupported items as `DEFER` or `NO_FOLLOWUP`.

Do not maintain disconnected bug, opportunity, or remediation registries that
never reach GitHub Issues, a linked PR, a task card, or a merge-parking entry.

## Closeout Matrix

Closeout and discovery reports should preserve a compact matrix:

| Issue/Finding | Lane | Labels | Milestone | Project Fields | Tracker | Follow-up Required | DATA_MISSING | Next Action |
| ------------- | ---- | ------ | --------- | -------------- | ------- | ------------------ | ------------ | ----------- |

This matrix is the handoff source for fresh Codex/GPT continuations.
